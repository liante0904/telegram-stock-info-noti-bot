import asyncio
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.SQLiteManager import SQLiteManager
from models.FirmInfo import FirmInfo
from modules.LS_0 import LS_detail
from modules.DBfi_19 import fetch_detailed_url


# TELEGRAM_URL을 얻고 업데이트하는 함수
async def update_firm_telegram_url_by_date(date_str=None):
    """
    firm_names 배열의 모든 인덱스를 순회하며, telegram_update_required가 True인 경우 TELEGRAM_URL 컬럼을 업데이트합니다.
    """
    db = SQLiteManager()
    all_records = []  # 모든 회사의 레코드를 저장할 리스트

    # firm_names 배열의 모든 인덱스를 순회
    for sec_firm_order in range(len(FirmInfo.firm_names)):
        firm_info = FirmInfo(sec_firm_order=sec_firm_order, article_board_order=0)

        # 회사 이름이 공백이 아니고, telegram_update_required가 True인 경우만 처리
        if firm_info.get_firm_name() and firm_info.telegram_update_required:
            records = await db.fetch_daily_articles_by_date(firm_info=firm_info, date_str=date_str)

            # records가 빈 리스트가 아닌 경우에만 처리 진행
            if records:
                print(f"Fetched records for SEC_FIRM_ORDER {sec_firm_order}: {records}")
                all_records.extend(records)

                # 조건에 따라 추가 작업 수행
                if sec_firm_order == 19:
                    # sec_firm_order가 19인 경우 업데이트 수행
                    print("Updating TELEGRAM_URL for records with SEC_FIRM_ORDER 19")
                    update_records = await fetch_detailed_url(records)  # all_records 대신 records 사용
                    for record in update_records:
                        await db.update_telegram_url(record['id'], record['TELEGRAM_URL'])
                        print(f"Updated TELEGRAM_URL for id {record['id']} with {record['TELEGRAM_URL']}")
                
                elif sec_firm_order == 0:
                    # sec_firm_order가 0인 경우 추가 작업 수행
                    print("Additional processing for SEC_FIRM_ORDER 0")
                    update_records = LS_detail(articles=records, firm_info=firm_info)  # all_records 대신 records 사용
                    
                    for record in update_records:
                        await db.update_telegram_url(record['id'], record['TELEGRAM_URL'], record['ARTICLE_TITLE'])
                        print(f"Updated TELEGRAM_URL for id {record['id']} with {record['TELEGRAM_URL']}")

    # 전체 회사들의 레코드가 JSON 리스트로 모임
    if all_records:  # all_records가 비어 있지 않은 경우에만 JSON 변환 및 출력 수행
        json_records = json.dumps(all_records, indent=2)
        print(f"Combined JSON Records size:\n{len(json_records)}")

# 메인 함수
async def main():
    firm_info = FirmInfo(
        sec_firm_order=19,
        article_board_order=0
    )
    # TELEGRAM_URL 업데이트 함수 호출
    await update_firm_telegram_url_by_date()

if __name__ == "__main__":
    asyncio.run(main())
