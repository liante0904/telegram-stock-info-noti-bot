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

async def BNK_checkNewArticle():
    SEC_FIRM_ORDER = 23
    ARTICLE_BOARD_ORDER = 0
    
    TARGET_URL_TUPLE = [
        "https://www.bnkfn.co.kr/research/analysingCompany.jspx",
        "https://www.bnkfn.co.kr/research/analysingIssue.jspx",
        "https://www.bnkfn.co.kr/research/economyAnalyse.jspx",
        "https://www.bnkfn.co.kr/research/marketOverview2.jspx"
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
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            soup = BeautifulSoup(response, "html.parser")
            table = soup.find("table", class_="table01")

            if not table:
                print(f"Table not found in {url}")
                continue

            rows = table.select("tbody tr")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue  # Skip rows with insufficient data

                # ARTICLE_TITLE 및 ARTICLE_URL 추출
                article_link = cells[1].find("a")
                if not article_link:
                    continue

                ARTICLE_TITLE = article_link.get_text(strip=True)

                # onclick에서 첨부파일 URL 추출
                onclick_attr = article_link.get("onclick", "")
                match = re.search(r"viewAction\(this, '\d+', '(/uploads/[^']+)', '([^']+)'\);", onclick_attr)
                ARTICLE_URL = ""
                if match:
                    base_path = match.group(1)
                    file_name = match.group(2)
                    ARTICLE_URL = f"https://www.bnkfn.co.kr{base_path}/{file_name}"

                REG_DT = cells[4].get_text(strip=True)

                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", REG_DT),
                    "ARTICLE_TITLE": ARTICLE_TITLE,
                    "ARTICLE_URL": ARTICLE_URL,
                    "DOWNLOAD_URL": ARTICLE_URL,
                    "TELEGRAM_URL": ARTICLE_URL,
                    "SAVE_TIME": datetime.now().isoformat(),
                    "KEY": ARTICLE_URL
                })

        # 메모리 정리
        gc.collect()

    return json_data_list

# 비동기 함수 실행
if __name__ == "__main__":
    articles = asyncio.run(BNK_checkNewArticle())
    for article in articles:
        print(article)
