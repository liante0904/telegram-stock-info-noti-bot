import asyncio
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.SQLiteManager import SQLiteManager
from models.FirmInfo import FirmInfo
from modules.dbfi_19 import fetch_detailed_url


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
            print(f"Fetched records for SEC_FIRM_ORDER {sec_firm_order}: {records}")
            all_records.extend(records)

    # 전체 회사들의 레코드가 JSON 리스트로 모임
    json_records = json.dumps(all_records, indent=2)
    print(f"Combined JSON Records:\n{json_records}")

    # API를 통해 TELEGRAM_URL 획득 및 업데이트
    update_records = await fetch_detailed_url(all_records)
    for record in update_records:
        # TELEGRAM_URL 업데이트 수행
        await db.update_telegram_url(record['id'], record['TELEGRAM_URL'])
        print(f"Updated TELEGRAM_URL for id {record['id']} with {record['TELEGRAM_URL']}")


# API를 통해 TELEGRAM_URL을 획득하는 함수 (예시로 가정)
async def fetch_telegram_url(key_url):
    """API를 통해 TELEGRAM_URL을 가져오는 함수 (가정된 API)."""
    # 실제 API 호출 코드 작성
    # 예를 들어, aiohttp 또는 httpx를 이용해 비동기로 호출 가능
    # 임의 URL 반환 예시
    return f"https://example.com/telegram/{key_url.split('/')[-1]}"

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
