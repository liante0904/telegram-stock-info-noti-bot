import sqlite3
import oracledb
import os
import time
import hashlib
from datetime import datetime
from dotenv import load_dotenv

def fast_migrate():
    load_dotenv(override=True)
    db_path = os.path.expanduser('~/sqlite3/telegram.db')
    
    print("🚀 [M4 + 5G 최적화] 초고속 이관 시작 (ID 1:1 보존 모드)...")
    start_time = time.time()

    # 1. SQLite 데이터 광속 추출 (ID 포함)
    try:
        sl_conn = sqlite3.connect(db_path)
        sl_conn.row_factory = sqlite3.Row
        cursor = sl_conn.cursor()
        cursor.execute("SELECT * FROM data_main_daily_send")
        rows = cursor.fetchall()
        print(f"📦 SQLite 추출 완료: {len(rows)}건 ({time.time()-start_time:.2f}초)")
    except Exception as e:
        print(f"❌ SQLite 오류: {e}")
        return

    # 2. Oracle 연결 (Wallet 기반)
    try:
        wl = os.path.expanduser(os.getenv('WALLET_LOCATION'))
        # M4 맥미니 환경에서는 Thin 모드로도 충분히 빠릅니다.
        ora_conn = oracledb.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            dsn=os.getenv('DB_DSN'),
            config_dir=wl,
            wallet_location=wl,
            wallet_password=os.getenv('WALLET_PASSWORD')
        )
        ora_cursor = ora_conn.cursor()
        print(f"🔗 Oracle 연결 성공 ({time.time()-start_time:.2f}초)")
        
        # 메인 테이블 비우기
        ora_cursor.execute("TRUNCATE TABLE TB_SEC_REPORTS")
        print("🧨 기존 데이터 삭제(TRUNCATE) 완료.")
    except Exception as e:
        print(f"❌ Oracle 연결/초기화 오류: {e}")
        return

    # 3. 데이터 정제 및 벌크 준비
    # REPORT_ID를 명시적으로 포함!
    query = """
    INSERT INTO TB_SEC_REPORTS (
        REPORT_ID, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT, 
        ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, SEND_USER, MAIN_CH_SEND_YN, 
        DOWNLOAD_STATUS_YN, DOWNLOAD_URL, SAVE_TIME, WRITER, REPORT_KEY, 
        TELEGRAM_URL, MKT_TP, GEMINI_SUMMARY, SUMMARY_TIME, SUMMARY_MODEL
    ) VALUES (
        :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, TO_TIMESTAMP(:13, 'YYYY-MM-DD HH24:MI:SS.FF'), :14, :15, :16, :17, :18, :19, :20
    )
    """

    data_to_insert = []
    for r in rows:
        # 1) SAVE_TIME 정제 (Oracle TIMESTAMP 규격)
        st = str(r['SAVE_TIME']).replace("T", " ")
        if st.startswith("--"):
            rd = str(r['REG_DT'])
            st = f"{rd[:4]}-{rd[4:6]}-{rd[6:8]} {st[3:]}" if len(rd) == 8 else f"2024-01-01 {st[3:]}"
        
        # 밀리초/마이크로초 길이 보정
        if len(st) == 19: st += ".000000"
        elif len(st) > 26: st = st[:26] # Oracle TIMESTAMP(6) 대응
        
        # 2) REPORT_KEY 생성/정제
        report_key = r['KEY'] or r['ATTACH_URL']
        if not report_key:
            raw_key = f"{r['FIRM_NM']}_{r['ARTICLE_TITLE']}_{r['REG_DT']}"
            report_key = hashlib.md5(raw_key.encode('utf-8')).hexdigest()

        # 3) NUL 문자 및 길이 제한 처리
        title = str(r['ARTICLE_TITLE'] or "").replace('\x00', '')[:1000]
        
        # 튜플 구성
        data_to_insert.append((
            r['report_id'],            # 1: REPORT_ID (SQLite의 report_id를 그대로!)
            r['SEC_FIRM_ORDER'],       # 2
            r['ARTICLE_BOARD_ORDER'],  # 3
            r['FIRM_NM'],              # 4
            r['REG_DT'],               # 5
            r['ATTACH_URL'],           # 6
            title,                     # 7
            r['ARTICLE_URL'],          # 8
            r['SEND_USER'],            # 9
            r['MAIN_CH_SEND_YN'] or 'N',# 10
            r['DOWNLOAD_STATUS_YN'] or 'N', # 11
            r['DOWNLOAD_URL'],         # 12
            st,                        # 13: SAVE_TIME (String for TO_TIMESTAMP)
            r['WRITER'],               # 14
            report_key,                # 15: REPORT_KEY
            r['TELEGRAM_URL'],         # 16
            r['MKT_TP'] or 'KR',       # 17
            r['GEMINI_SUMMARY'],       # 18
            r['SUMMARY_TIME'],         # 19
            r['SUMMARY_MODEL']         # 20
        ))

    # 4. Oracle 벌크 인서트 (1.5만 건 단위로 최적화)
    batch_size = 15000
    total_count = len(data_to_insert)
    
    try:
        for i in range(0, total_count, batch_size):
            batch = data_to_insert[i:i+batch_size]
            ora_cursor.executemany(query, batch)
            print(f"📤 전송 중... {min(i+batch_size, total_count)}/{total_count} ({time.time()-start_time:.1f}초)")
        
        ora_conn.commit()
        print(f"🎉 [성공] 모든 데이터 이관 완료!")
    except Exception as e:
        print(f"❌ 인서트 도중 오류 발생: {e}")
        ora_conn.rollback()
    finally:
        ora_conn.close()
        sl_conn.close()
    
    print(f"✨ 최종 소요 시간: {time.time()-start_time:.2f}초 (25.8만 건 완료)")

if __name__ == "__main__":
    fast_migrate()
