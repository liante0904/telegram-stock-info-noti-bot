import os
import gc
import aiohttp
import asyncio
import re
from datetime import datetime

from bs4 import BeautifulSoup
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo

async def fetch_article(session, url, headers):
    async with session.get(url, headers=headers) as response:
        return await response.text()

async def Hanyang_checkNewArticle():
    SEC_FIRM_ORDER = 22
    ARTICLE_BOARD_ORDER = 0

    TARGET_URL_TUPLE = [
        "https://www.hygood.co.kr/board/researchAnalyzeCompany/list",
        "https://www.hygood.co.kr/board/researchAnalyzeIssue/list",
        "https://www.hygood.co.kr/board/researchBondsCredit/list"
    ]

    json_data_list = []

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_article(session, url, headers) for url in TARGET_URL_TUPLE]
        responses = await asyncio.gather(*tasks)
    
        for ARTICLE_BOARD_ORDER, (response, url) in enumerate(zip(responses, TARGET_URL_TUPLE)):
        # for response, url in zip(responses, BASE_URLS):
            
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            soup = BeautifulSoup(response, "html.parser")
            table = soup.find("table", class_="board_list")

            if not table:
                print(f"Table not found in {url}")
                continue

            rows = table.select("tbody tr")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue  # Skip rows with insufficient data

                # # REG_DT 추출
                # reg_date = cells[0].get_text(strip=True)
                # print(reg_date)
                # REG_DT = reg_date.replace('-', '')  # YYYYMMDD 형식

                # ARTICLE_TITLE 및 ARTICLE_URL 추출
                article_link = cells[1].find("a")
                if not article_link:
                    continue

                ARTICLE_TITLE = article_link.get_text(strip=True)
                ARTICLE_URL = article_link['href']

                # 절대 URL로 변환
                if ARTICLE_URL.startswith("/"):
                    ARTICLE_URL = f"https://www.hygood.co.kr{ARTICLE_URL}"

                REG_DT = cells[2].get_text(strip=True)

                # 첨부 파일 URL 추출
                attachment_cell = cells[3].find("a")
                ATTACH_URL = ""
                if attachment_cell:
                    ATTACH_URL = attachment_cell['href']
                    if ATTACH_URL.startswith("/"):
                        ATTACH_URL = f"https://www.hygood.co.kr{ATTACH_URL}"
                
                json_data_list.append({
                    "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                    "FIRM_NM":firm_info.get_firm_name(),
                    "REG_DT":re.sub(r"[-./]", "", REG_DT),
                    "ARTICLE_TITLE": ARTICLE_TITLE,
                    "ARTICLE_URL": ATTACH_URL,
                    "DOWNLOAD_URL": ATTACH_URL,
                    "TELEGRAM_URL": ATTACH_URL,
                    "SAVE_TIME": datetime.now().isoformat(),
                    "KEY":ATTACH_URL
                })

        # 메모리 정리
        gc.collect()

    return json_data_list

# 비동기 함수 실행
if __name__ == "__main__":
    articles = asyncio.run(Hanyang_checkNewArticle())
    for article in articles:
        print(article)
