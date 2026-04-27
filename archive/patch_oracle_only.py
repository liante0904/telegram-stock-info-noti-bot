import asyncio
import os
import sys
from models.SQLiteManager import SQLiteManager
from models.OracleManager import OracleManager
from models.FirmInfo import FirmInfo

async def patch_oracle_recent_data(days=7):
    """최근 7일간의 SQLite 데이터를 Oracle로 전송하여 누락된 정보를 채웁니다. (TRUNCATE 없음)"""
    sqlite = SQLiteManager()
    oracle = OracleManager()
    
    print(f"🚀 [Patch] 최근 {days}일간의 SQLite 데이터를 Oracle로 패치 시작...")

    # 최근 7일간의 데이터를 SQLite에서 가져오기
    # sec_firm_order 0(LS)와 19(DB) 위주로 처리
    target_firms = [0, 19]
    total_patched = 0

    for sfo in target_firms:
        firm_info = FirmInfo(sec_firm_order=sfo)
        # SQLite에서 최근 데이터를 조회 (이미 enrich_data로 복구된 상태)
        # fetch_all_empty_telegram_url_articles 대신 fetch_all을 쓰되 날짜 필터를 걸거나,
        # 전체를 읽어서 MERGE 로직에 맡김 (MERGE는 중복 시 UPDATE하므로 안전함)
        
        print(f"📦 [sec_firm_order {sfo}] SQLite 데이터 조회 중...")
        sqlite.open_connection()
        query = f"SELECT * FROM data_main_daily_send WHERE sec_firm_order = {sfo} AND SAVE_TIME >= datetime('now', '-{days} days', 'localtime')"
        sqlite.cursor.execute(query)
        rows = sqlite.cursor.fetchall()
        sqlite.close_connection()
        
        if not rows:
            print(f"⚠️ [sec_firm_order {sfo}] 최근 {days}일 내 데이터가 없습니다.")
            continue

        json_data_list = [dict(row) for row in rows]
        print(f"📤 [sec_firm_order {sfo}] Oracle로 {len(json_data_list)}건 패치(MERGE) 중...")
        
        # OracleManager.insert_json_data_list는 내부적으로 MERGE INTO를 사용하므로
        # 기존 데이터가 있으면 TELEGRAM_URL 등 변경된 컬럼만 업데이트함
        result_count = await oracle.insert_json_data_list(json_data_list)
        
        print(f"✅ [sec_firm_order {sfo}] 패치 완료: {result_count}건 처리되었습니다.")
        total_patched += result_count

    print(f"🎉 [Patch Finished] 총 {total_patched}건의 데이터가 Oracle에 업데이트되었습니다.")

if __name__ == "__main__":
    asyncio.run(patch_oracle_recent_data(days=7))
