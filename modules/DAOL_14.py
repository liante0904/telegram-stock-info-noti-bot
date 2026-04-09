import os
import gc
import aiohttp
import asyncio
import urllib.parse as urlparse
from datetime import datetime
from loguru import logger

from bs4 import BeautifulSoup
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo

async def fetch_article(session, TARGET_URL, form_data, headers):
    async with session.post(TARGET_URL, data=form_data, headers=headers) as response:
        return await response.text()

async def DAOL_checkNewArticle():
    SEC_FIRM_ORDER = 14
    json_data_list = []

    # URL 정의
    TARGET_URL_TUPLE = (
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED'
    )

    async with aiohttp.ClientSession() as session:
        tasks = []
        for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
            logger.debug(f"DAOL Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")
            
            parsed_url = urlparse.urlparse(TARGET_URL)
            query_params = urlparse.parse_qs(parsed_url.query)
            BASE_URL = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            POST_URL = f"{BASE_URL}?cmd=list&templet-bypass=true"

            headers = {
                'Accept': '*/*',
                'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': BASE_URL,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            now = datetime.now()
            start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

            form_data = {
                'curPage': '1',
                'rGubun': query_params.get('rGubun'),
                'sctrGubun': query_params.get('sctrGubun'),
                'web': query_params.get('web'),
                'startDate': start_of_year.strftime("%Y/%m/%d"),
                'endDate': now.strftime("%Y%m%d"),
                'searchSelect': '0',
                'searchNm2': query_params.get('rGubun')
            }

            tasks.append(fetch_article(session, POST_URL, form_data, headers))

        responses = await asyncio.gather(*tasks)

        for ARTICLE_BOARD_ORDER, response in enumerate(responses):
            firm_info = FirmInfo(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
            soup = BeautifulSoup(response, "html.parser")
            soupList = soup.select('tr')
            logger.info(f"DAOL Scraper: Found {len(soupList)} rows for board {ARTICLE_BOARD_ORDER}")

            for list_item in soupList:
                cells = list_item.select('td')
                if len(cells) < 5: continue

                REG_DT = cells[0].get_text(strip=True).replace('/', '')
                WRITER = cells[4].get_text(strip=True)

                article_link = cells[1].select_one('a.del_w')
                if not article_link: continue

                LIST_ARTICLE_TITLE = article_link.get('title', '')
                if "Coverage 제외" in LIST_ARTICLE_TITLE:
                    continue

                raw_href = article_link.get('href', '')
                parts = raw_href.split(',')
                if len(parts) != 3: continue

                try:
                    path = parts[0].split("'")[1]
                    filename = parts[1].split("'")[1]
                    final_url = f"https://www.ktb.co.kr/common/download.jspx?cmd=viewPDF&path={path}/{filename}"
                    
                    json_data_list.append({
                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                        "FIRM_NM": firm_info.get_firm_name(),
                        "REG_DT": REG_DT,
                        "ATTACH_URL": final_url,
                        "DOWNLOAD_URL": final_url,
                        "TELEGRAM_URL": final_url,
                        "PDF_URL": final_url,
                        "KEY": final_url,
                        "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                        "WRITER": WRITER,
                        "SAVE_TIME": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error parsing DAOL article link: {e}")

    gc.collect()
    return json_data_list


if __name__ == "__main__":
    result = asyncio.run(DAOL_checkNewArticle())
    logger.info(f"Total DAOL articles fetched: {len(result)}")
