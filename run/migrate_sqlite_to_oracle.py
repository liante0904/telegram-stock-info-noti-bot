import asyncio
import os
import sys
from models.SQLiteManager import SQLiteManager
from models.OracleManager import OracleManager

async def migrate_all_to_oracle():
    """SQLite의 모든 레포트 데이터를 Oracle(tbl_sec_reports)로 이관합니다."""
    sqlite = SQLiteManager()
    oracle = OracleManager()

    # 이관 대상 SQLite 테이블 목록
    tables_to_migrate = [
        'data_main_daily_send',
        'hankyungconsen',
        'naver_research'
    ]

    print(f"🚀 [Migration] SQLite -> Oracle 데이터 이관 시작...")

    # Oracle 테이블 비우기 (TRUNCATE)
    try:
        print(f"🧨 [Oracle] tbl_sec_reports 테이블 비우는 중 (TRUNCATE)...")
        await oracle.execute_query("TRUNCATE TABLE tbl_sec_reports")
        print(f"✨ [Oracle] 테이블이 성공적으로 비워졌습니다.")
    except Exception as e:
        print(f"⚠️ [Oracle] 테이블 비우기 실패 (무시하고 진행): {e}")

    total_migrated = 0
    for table_name in tables_to_migrate:
        try:
            print(f"📦 [{table_name}] 데이터 조회 중...")
            # SQLiteManager의 fetch_all을 사용 (sqlite3.Row 객체 반환)
            rows = sqlite.fetch_all(table_name)
            
            if not rows:
                print(f"⚠️ [{table_name}] 데이터가 없습니다. 건너뜁니다.")
                continue

            # sqlite3.Row 객체를 dict 리스트로 변환 (OracleManager가 처리할 수 있게 함)
            # SQLiteManager의 로직에 따라 key 컬럼이 이미 존재할 것이므로 그대로 전달
            json_data_list = [dict(row) for row in rows]
            
            print(f"📤 [{table_name}] Oracle로 {len(json_data_list)}건 전송 중...")
            # OracleManager의 insert_json_data_list는 MERGE(UPSERT)를 수행하므로 중복 데이터가 있어도 안전함
            result_count = await oracle.insert_json_data_list(json_data_list)
            
            print(f"✅ [{table_name}] 이관 완료: {result_count}건 처리되었습니다.")
            total_migrated += result_count
            
        except Exception as e:
            print(f"❌ [{table_name}] 이관 중 오류 발생: {e}")

    print(f"🎉 [Migration Finished] 총 {total_migrated}건의 데이터가 Oracle로 동기화되었습니다.")

if __name__ == "__main__":
    asyncio.run(migrate_all_to_oracle())
