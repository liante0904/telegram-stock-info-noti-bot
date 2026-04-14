import asyncio
import aiohttp
import gc
import re
from datetime import datetime
from bs4 import BeautifulSoup
import os
import sys
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

async def fetch(session, url):
    """비동기로 HTTP 요청을 보내는 함수"""
    async with session.get(url) as response:
        return await response.text()

async def fetch_all_pages_meritz(session, base_url, sec_firm_order, article_board_order, max_pages=None):
    """메리츠증권 모든 페이지 데이터를 순회하며 가져오는 함수"""
    json_data_list = []
    page = 1

    while True:
        if max_pages and page > max_pages:  # 최대 페이지를 초과하면 종료
            break

        target_url = base_url.replace("pageNum=1", f"pageNum={page}")
        logger.debug(f"Fetching: {target_url}")

        try:
            html_content = await fetch(session, target_url)
        except Exception as e:
            logger.error(f"Error fetching URL {target_url}: {e}")
            break

        # HTML parse
        soup = BeautifulSoup(html_content, "html.parser")
        soupListHead = soup.select('table > thead > tr > th')  # 메리츠증권 리스트 헤더
        soupList = soup.select('table > tbody > tr')  # 메리츠증권 리스트 아이템 선택자
        logger.info(f"Page {page}: Found {len(soupList)} articles")  # Progress 출력

        if not soupList:  # 더 이상 데이터가 없으면 종료
            break
            
        # 헤더 매핑 생성: 헤더 이름 -> 열 번호
        header_map = {th.get_text().strip(): idx for idx, th in enumerate(soupListHead)}
        
        for list_item in soupList:
            try:
                link_tag = list_item.select_one(f'td:nth-child({header_map["제목"] + 1}) a')

                LIST_ARTICLE_TITLE = link_tag.get_text().strip() if link_tag else "N/A"
                LIST_ARTICLE_URL = "https://home.imeritz.com" + link_tag['href']
                
                # 작성일시
                date_column = "작성일" if "작성일" in header_map else "작성일시"
                REG_DT = list_item.select_one(f'td:nth-child({header_map[date_column] + 1})').get_text().strip()
                REG_DT = re.sub(r"[-./]", "", REG_DT)  # 날짜 포맷 정리
                
                # 작성자
                date_column = "작성자" if "작성자" in header_map else "작성자명"
                WRITER = list_item.select_one(f'td:nth-child({header_map[date_column] + 1})').get_text().strip()
                
                # 카테고리
                CATEGORY = list_item.select_one(f'td:nth-child({header_map["분류"] + 1})').get_text().strip() if "분류" in header_map else ""

                # DOWNLOAD_URL, TELEGRAM_URL 생성
                try:
                    article_html = await fetch(session, LIST_ARTICLE_URL)
                    article_soup = BeautifulSoup(article_html, "html.parser")

                    download_tag = article_soup.select_one('a[title]')
                    if download_tag and 'title' in download_tag.attrs:
                        file_name = download_tag['title']
                        file_name = file_name.replace(" 파일 다운로드", "").strip()
                        DOWNLOAD_URL = f"https://home.imeritz.com/include/resource/research/WorkFlow/{file_name}"
                        TELEGRAM_URL = DOWNLOAD_URL
                    else:
                        logger.warning(f"No 'title' attribute found in download tag at {LIST_ARTICLE_URL}")
                        DOWNLOAD_URL = TELEGRAM_URL = LIST_ARTICLE_URL

                except Exception as e:
                    logger.error(f"Error fetching DOWNLOAD_URL from {LIST_ARTICLE_URL}: {e}")
                    DOWNLOAD_URL = TELEGRAM_URL = LIST_ARTICLE_URL

                # JSON 데이터 생성
                article_data = {
                    "SEC_FIRM_ORDER": sec_firm_order,
                    "ARTICLE_BOARD_ORDER": article_board_order,
                    "FIRM_NM": FirmInfo(sec_firm_order, article_board_order).get_firm_name(),
                    "REG_DT": REG_DT,
                    "ARTICLE_URL": LIST_ARTICLE_URL,
                    "ATTACH_URL": TELEGRAM_URL,
                    "DOWNLOAD_URL": DOWNLOAD_URL,
                    "TELEGRAM_URL": TELEGRAM_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "CATEGORY": CATEGORY,
                    "KEY": TELEGRAM_URL, # 중복 방지 키
                    "SAVE_TIME": datetime.now().isoformat()
                }
                json_data_list.append(article_data)
            except Exception as e:
                logger.error(f"Error parsing article row: {e}")
                continue

        page += 1

    return json_data_list


async def MERITZ_checkNewArticle(full_fetch=False):
    """메리츠증권 데이터 수집"""
    SEC_FIRM_ORDER = 20

    TARGET_URL_TUPLE = [
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED'
    ]

    # 200건씩 한 번만 호출하도록 max_pages를 1로 제한 (full_fetch 시에도 대량 수집 가능)
    max_pages = 1
    all_results = []
    async with aiohttp.ClientSession() as session:
        for article_board_order, base_url in enumerate(TARGET_URL_TUPLE):
            logger.info(f"Processing MERITZ board {article_board_order + 1}/{len(TARGET_URL_TUPLE)}")
            results = await fetch_all_pages_meritz(session, base_url, SEC_FIRM_ORDER, article_board_order, max_pages)
            all_results.extend(results)

    gc.collect()
    return all_results


async def main():
    meritz_result = await MERITZ_checkNewArticle(full_fetch=True)
    logger.info(f"Fetched {len(meritz_result)} articles from Meritz.")
    if meritz_result:
        db = SQLiteManager()
        db.insert_json_data_list(meritz_result)

if __name__ == "__main__":
    asyncio.run(main())
