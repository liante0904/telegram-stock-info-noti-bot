import asyncio
import aiohttp
import json
import ssl
import certifi
from datetime import datetime
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

BASE_URL = "https://m.db-fi.com"
HEADERS_TEMPLATE = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}

# SSL 검증 완전히 비활성화
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers("DEFAULT")


# DB금융투자 기사 체크 함수
async def DBfi_checkNewArticle():
    SEC_FIRM_ORDER = 19
    urls = [
        "/appData/rsh_entr_lst.json",
        "/appData/rsh_bond_lst.json",
        "/appData/rsh_stock_lst.json"
    ]
    json_data_list = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        for ARTICLE_BOARD_ORDER, url_path in enumerate(urls):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            headers = {
                **HEADERS_TEMPLATE,
                "Referer": f"{BASE_URL}/mre/mre_CompanyAll_lst.do",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }

            print(f"Fetching articles from {url_path} with ARTICLE_BOARD_ORDER: {ARTICLE_BOARD_ORDER}")
            async with session.post(f"{BASE_URL}{url_path}", headers=headers) as response:
                print(f"Response status for URL {url_path}: {response.status}")
                if response.status == 200:
                    try:
                        jres = await response.json()
                        data_items = jres.get("data", [])
                    except (json.JSONDecodeError, KeyError):
                        print(f"No items found on the page for URL {url_path}.")
                        continue

                    for item in data_items:
                        detail_url = f"{BASE_URL}/appData/descRsh/{item['rid']}.json"
                        json_data_list.append({
                            "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                            "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                            "FIRM_NM": firm_info.get_firm_name(),
                            "REG_DT": item['rdt'][:8],
                            "ARTICLE_URL": "",
                            "TELEGRAM_URL": "",
                            "ARTICLE_TITLE": item['tit'],
                            "WRITER": item['wnm'],
                            "CATEGORY": item['div'],
                            "KEY": detail_url,
                            "SAVE_TIME": datetime.now().isoformat()
                        })
                else:
                    print(f"Failed to fetch page data for URL {url_path}. Status code: {response.status}")

    return json_data_list


# 상세 URL로 후처리 데이터 획득 함수
async def fetch_detailed_url(articles):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        for article in articles:
            key_url = article["KEY"]

            async with session.post(key_url, headers=HEADERS_TEMPLATE) as response:
                if response.status == 200:
                    try:
                        detail_data = await response.json()
                        # 'url' 값을 가져와 TELEGRAM_URL 생성
                        encoded_url = detail_data['data'].get("url", "")
                        telegram_url = f"https://m.db-fi.com/mod/streamDocs.do?docId={encoded_url}"
                        article["TELEGRAM_URL"] = telegram_url
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON for {key_url}")
                else:
                    print(f"Failed to fetch details from {key_url}. Status code: {response.status}")

    print(articles)
    return articles


async def main():
    articles = await DBfi_checkNewArticle()
    detailed_articles = await fetch_detailed_url(articles)
    db = SQLiteManager()
    inserted_count = db.insert_json_data_list(detailed_articles, 'data_main_daily_send')  # 모든 데이터를 한 번에 삽입
    print(inserted_count)


if __name__ == "__main__":
    asyncio.run(main())
