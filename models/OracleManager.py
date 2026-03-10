import asyncio
import oracledb
import os
import sys
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class OracleManager:
    def __init__(self):
        """Oracle 데이터베이스 연결 초기화 (안정적인 동기 방식 기반)"""
        load_dotenv(override=True)
        self._init_thick_mode()

    def _init_thick_mode(self):
        """Thick 모드 초기화 시도 (Wallet 연동을 위해 필요한 경우)"""
        try:
            # 환경에 따라 instantclient 경로가 다를 수 있음
            lib_dir = "/opt/oracle/instantclient_19_10"
            if os.path.exists(lib_dir):
                oracledb.init_oracle_client(lib_dir=lib_dir)
            else:
                # 기본 경로 시도
                oracledb.init_oracle_client()
        except Exception:
            pass

    def _get_connection_sync(self):
        """동기 방식으로 연결 객체 생성 (검증된 방식)"""
        wl = os.path.expanduser(os.getenv('WALLET_LOCATION'))
        return oracledb.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            dsn=os.getenv('DB_DSN'),
            config_dir=wl,
            wallet_location=wl,
            wallet_password=os.getenv('WALLET_PASSWORD')
        )

    def _insert_sync_process(self, json_data_list):
        """데이터 삽입을 수행하는 동기 메서드"""
        if not json_data_list:
            return 0
            
        conn = self._get_connection_sync()
        query = """
        MERGE INTO TB_SEC_REPORTS t
        USING (SELECT :SEC_FIRM_ORDER as SEC_FIRM_ORDER, :ARTICLE_BOARD_ORDER as ARTICLE_BOARD_ORDER, 
                      :FIRM_NM as FIRM_NM, :REG_DT as REG_DT, :ATTACH_URL as ATTACH_URL, 
                      :ARTICLE_TITLE as ARTICLE_TITLE, :ARTICLE_URL as ARTICLE_URL, 
                      :MAIN_CH_SEND_YN as MAIN_CH_SEND_YN, :DOWNLOAD_URL as DOWNLOAD_URL, 
                      :TELEGRAM_URL as TELEGRAM_URL, :WRITER as WRITER, :MKT_TP as MKT_TP, 
                      :REPORT_KEY as REPORT_KEY, TO_TIMESTAMP(:SAVE_TIME, 'YYYY-MM-DD"T"HH24:MI:SS.FF') as SAVE_TIME
               FROM DUAL) s
        ON (t.REPORT_KEY = s.REPORT_KEY)
        WHEN MATCHED THEN
            UPDATE SET 
                t.REG_DT = s.REG_DT,
                t.WRITER = s.WRITER,
                t.MKT_TP = s.MKT_TP,
                t.DOWNLOAD_URL = CASE WHEN s.DOWNLOAD_URL IS NOT NULL THEN s.DOWNLOAD_URL ELSE t.DOWNLOAD_URL END,
                t.TELEGRAM_URL = CASE WHEN s.TELEGRAM_URL IS NOT NULL AND s.TELEGRAM_URL != '' THEN s.TELEGRAM_URL ELSE t.TELEGRAM_URL END
        WHEN NOT MATCHED THEN
            INSERT (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT, ATTACH_URL, 
                    ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, DOWNLOAD_URL, 
                    TELEGRAM_URL, WRITER, MKT_TP, REPORT_KEY, SAVE_TIME)
            VALUES (s.SEC_FIRM_ORDER, s.ARTICLE_BOARD_ORDER, s.FIRM_NM, s.REG_DT, s.ATTACH_URL, 
                    s.ARTICLE_TITLE, s.ARTICLE_URL, s.MAIN_CH_SEND_YN, s.DOWNLOAD_URL, 
                    s.TELEGRAM_URL, s.WRITER, s.MKT_TP, s.REPORT_KEY, s.SAVE_TIME)
        """
        
        params_list = []
        for entry in json_data_list:
            title = entry.get("ARTICLE_TITLE", "")
            mkt_tp = entry.get("MKT_TP", "KR")
            if not mkt_tp or mkt_tp == "KR":
                if ".JP" in title: mkt_tp = "JP"
                elif ".US" in title: mkt_tp = "US"
            
            # SAVE_TIME 처리 (Oracle TO_TIMESTAMP 형식 지원)
            st = entry.get("SAVE_TIME", "")
            reg_dt = entry.get("REG_DT", "")
            
            # 비정상적인 SAVE_TIME 보정 (예: --T00:46:06.795834)
            if st.startswith("--T"):
                if len(reg_dt) == 8:
                    st = f"{reg_dt[:4]}-{reg_dt[4:6]}-{reg_dt[6:8]}T{st[3:]}"
                else:
                    st = f"2024-01-01T{st[3:]}"  # 기본값
            
            # 일반적인 공백 처리
            st = st.replace(" ", "T")
            
            # Oracle TIMESTAMP에 적합하도록 형식 보정 (YYYY-MM-DD"T"HH24:MI:SS.FF)
            # 마이크로초 부분의 길이를 맞추기 위해 정제 (필요시)
            if "T" in st and len(st) > 19:
                pass # 이미 소수점 포함인 경우 그대로 사용
            elif "T" in st and len(st) == 19:
                st = st + ".000000"
            elif len(st) == 8 and "-" not in st: # yyyymmdd 형태
                st = f"{st[:4]}-{st[4:6]}-{st[6:8]}T00:00:00.000000"

            # REPORT_KEY 생성 (Hash 적용으로 길이 제한 및 중복 해결)
            report_key = entry.get("KEY") or entry.get("ATTACH_URL")
            if not report_key:
                raw_key = f"{entry['FIRM_NM']}_{title}_{entry.get('REG_DT', '')}"
                report_key = hashlib.md5(raw_key.encode('utf-8')).hexdigest()

            params_list.append({
                "SEC_FIRM_ORDER": entry["SEC_FIRM_ORDER"],
                "ARTICLE_BOARD_ORDER": entry["ARTICLE_BOARD_ORDER"],
                "FIRM_NM": entry["FIRM_NM"],
                "REG_DT": entry.get("REG_DT", ""),
                "ATTACH_URL": entry.get("ATTACH_URL", ""),
                "ARTICLE_TITLE": title[:1000],  # 컬럼 사이즈 고려
                "ARTICLE_URL": entry.get("ARTICLE_URL"),
                "MAIN_CH_SEND_YN": entry.get("MAIN_CH_SEND_YN", "N"),
                "DOWNLOAD_URL": entry.get("DOWNLOAD_URL"),
                "TELEGRAM_URL": entry.get("TELEGRAM_URL", ""),
                "WRITER": entry.get("WRITER", ""),
                "MKT_TP": mkt_tp,
                "REPORT_KEY": report_key,
                "SAVE_TIME": st
            })
            
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
            print(f"✅ Oracle Sync Success: {len(params_list)} rows processed.")
            return len(params_list)
        except Exception as e:
            print(f"❌ Oracle Merge Error: {e}")
            return 0
        finally:
            conn.close()

    async def insert_json_data_list(self, json_data_list):
        """비동기 인터페이스 유지 (내부는 안정적인 동기 로직 실행)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._insert_sync_process, json_data_list)

    async def bulk_insert(self, json_data_list):
        """[이관 전용] 대용량 고속 삽입을 위한 별도 함수"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._bulk_insert_sync, json_data_list)

    def _bulk_insert_sync(self, json_data_list):
        """[이관 전용] MERGE 없이 INSERT /*+ APPEND */를 사용하는 고속 동기 로직"""
        if not json_data_list:
            return 0
            
        conn = self._get_connection_sync()
        # Oracle의 Direct Path Insert와 APPEND 힌트 사용
        query = """
        INSERT /*+ APPEND */ INTO TB_SEC_REPORTS (
            SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT, ATTACH_URL, 
            ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, DOWNLOAD_URL, 
            TELEGRAM_URL, WRITER, MKT_TP, REPORT_KEY, SAVE_TIME
        ) VALUES (
            :SEC_FIRM_ORDER, :ARTICLE_BOARD_ORDER, :FIRM_NM, :REG_DT, :ATTACH_URL, 
            :ARTICLE_TITLE, :ARTICLE_URL, :MAIN_CH_SEND_YN, :DOWNLOAD_URL, 
            :TELEGRAM_URL, :WRITER, :MKT_TP, :REPORT_KEY, TO_TIMESTAMP(:SAVE_TIME, 'YYYY-MM-DD HH24:MI:SS.FF')
        )
        """
        
        params_list = []
        for entry in json_data_list:
            title = entry.get("ARTICLE_TITLE", "")
            mkt_tp = entry.get("MKT_TP", "KR")
            if not mkt_tp or mkt_tp == "KR":
                if ".JP" in title: mkt_tp = "JP"
                elif ".US" in title: mkt_tp = "US"
            
            # 이미 정제된 데이터라고 가정 (NUL 제거 및 날짜 형식 보정)
            st = str(entry.get("SAVE_TIME", "")).replace("T", " ")
            if len(st) == 19: st += ".000000"
            elif len(st) == 8 and "-" not in st: st = f"{st[:4]}-{st[4:6]}-{st[6:8]} 00:00:00.000000"

            report_key = entry.get("KEY") or entry.get("ATTACH_URL")
            if not report_key:
                raw_key = f"{entry['FIRM_NM']}_{title}_{entry.get('REG_DT', '')}"
                report_key = hashlib.md5(raw_key.encode('utf-8')).hexdigest()

            params_list.append({
                "SEC_FIRM_ORDER": entry["SEC_FIRM_ORDER"],
                "ARTICLE_BOARD_ORDER": entry["ARTICLE_BOARD_ORDER"],
                "FIRM_NM": entry["FIRM_NM"],
                "REG_DT": entry.get("REG_DT", ""),
                "ATTACH_URL": entry.get("ATTACH_URL", ""),
                "ARTICLE_TITLE": title[:1000],
                "ARTICLE_URL": entry.get("ARTICLE_URL"),
                "MAIN_CH_SEND_YN": entry.get("MAIN_CH_SEND_YN", "N"),
                "DOWNLOAD_URL": entry.get("DOWNLOAD_URL"),
                "TELEGRAM_URL": entry.get("TELEGRAM_URL", ""),
                "WRITER": entry.get("WRITER", ""),
                "MKT_TP": mkt_tp,
                "REPORT_KEY": report_key,
                "SAVE_TIME": st
            })
            
        try:
            with conn.cursor() as cursor:
                # 25만 건을 한 번에 전송 (Oracle이 알아서 최적화함)
                cursor.executemany(query, params_list)
                conn.commit()
            print(f"✅ Oracle Bulk Insert Success: {len(params_list)} rows.")
            return len(params_list)
        except Exception as e:
            print(f"❌ Oracle Bulk Insert Error: {e}")
            return 0
        finally:
            conn.close()

    def _execute_query_sync(self, query, params=None):
        """동기 쿼리 실행 로직"""
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if query.strip().upper().startswith("SELECT"):
                    columns = [col[0] for col in cursor.description]
                    res = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in res]
                else:
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            print(f"❌ Oracle Query Error: {e}")
            return []
        finally:
            conn.close()

    async def execute_query(self, query, params=None):
        """비동기 인터페이스 유지"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_query_sync, query, params)

    async def update_report_summary(self, record_id, summary, model_name):
        """Gemini 요약 결과 업데이트"""
        query = """
        UPDATE TB_SEC_REPORTS
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :st, 
            SUMMARY_MODEL = :model
        WHERE REPORT_ID = :id
        """
        params = {
            "summary": summary,
            "st": datetime.now().isoformat(),
            "model": model_name,
            "id": record_id
        }
        return await self.execute_query(query, params)

if __name__ == "__main__":
    async def test():
        om = OracleManager()
        res = await om.execute_query("SELECT count(*) FROM TB_SEC_REPORTS")
        print(f"Test Result: {res}")
    asyncio.run(test())
