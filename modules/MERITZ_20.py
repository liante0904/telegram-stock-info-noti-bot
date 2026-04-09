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
        logger.debug(f"MERITZ Scraper: Fetching page {page} - {target_url}")

        try:
            html_content = await fetch(session, target_url)
        except Exception as e:
            logger.error(f"Error fetching URL {target_url}: {e}")
            break

        # HTML parse
        soup = BeautifulSoup(html_content, "html.parser")
        soupListHead = soup.select('table > thead > tr > th')
        soupList = soup.select('table > tbody > tr')
        
        if not soupList:
            logger.info(f"MERITZ Scraper: No more articles on page {page}")
            break
            
        logger.info(f"MERITZ Scraper: Found {len(soupList)} articles on page {page}")
            
        # 헤더 매핑 생성: 헤더 이름 -> 열 번호
        header_map = {th.get_text().strip(): idx for idx, th in enumerate(soupListHead)}
        
        for list_item in soupList:
            try:
                link_tag = list_item.select_one(f'td:nth-child({header_map["제목"] + 1}) a')
                if not link_tag: continue

                LIST_ARTICLE_TITLE = link_tag.get_text().strip()
                LIST_ARTICLE_URL = "https://home.imeritz.com" + link_tag['href']
                
                date_column = "작성일" if "작성일" in header_map else "작성일시"
                REG_DT = list_item.select_one(f'td:nth-child({header_map[date_column] + 1})').get_text().strip()
                REG_DT = re.sub(r"[-./]", "", REG_DT)
                
                writer_column = "작성자" if "작성자" in header_map else "작성자명"
                WRITER = list_item.select_one(f'td:nth-child({header_map[writer_column] + 1})').get_text().strip()
                
                CATEGORY = list_item.select_one(f'td:nth-child({header_map["분류"] + 1})').get_text().strip() if "분류" in header_map else ""

                # 상세 페이지에서 PDF URL 추출
                try:
                    article_html = await fetch(session, LIST_ARTICLE_URL)
                    article_soup = BeautifulSoup(article_html, "html.parser")
                    download_tag = article_soup.select_one('a[title]')

                    if download_tag and 'title' in download_tag.attrs:
                        file_name = download_tag['title'].replace(" 파일 다운로드", "").strip()
                        DOWNLOAD_URL = f"https://home.imeritz.com/include/resource/research/WorkFlow/{file_name}"
                        TELEGRAM_URL = DOWNLOAD_URL
                        PDF_URL = DOWNLOAD_URL
                    else:
                        logger.debug(f"No PDF download link for {LIST_ARTICLE_TITLE}")
                        DOWNLOAD_URL = TELEGRAM_URL = PDF_URL = LIST_ARTICLE_URL

                except Exception as e:
                    logger.error(f"Error fetching detail from {LIST_ARTICLE_URL}: {e}")
                    DOWNLOAD_URL = TELEGRAM_URL = PDF_URL = LIST_ARTICLE_URL

                json_data_list.append({
                    "SEC_FIRM_ORDER": sec_firm_order,
                    "ARTICLE_BOARD_ORDER": article_board_order,
                    "FIRM_NM": FirmInfo(sec_firm_order, article_board_order).get_firm_name(),
                    "REG_DT": REG_DT,
                    "ARTICLE_URL": LIST_ARTICLE_URL,
                    "ATTACH_URL": TELEGRAM_URL,
                    "DOWNLOAD_URL": DOWNLOAD_URL,
                    "TELEGRAM_URL": TELEGRAM_URL,
                    "PDF_URL": PDF_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "CATEGORY": CATEGORY,
                    "KEY": TELEGRAM_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error parsing article row: {e}")
                continue

        page += 1

    return json_data_list


async def MERITZ_checkNewArticle(full_fetch=False):
    """메리츠증권 데이터 수집"""
    SEC_FIRM_ORDER = 20

    TARGET_URL_TUPLE = [
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=sih02nw&listCnt=50&pageNum=1&searchDiv=&searchText=',
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=invest03nw&listCnt=50&pageNum=1&searchDiv=&searchText=',
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=invest02nw&listCnt=50&pageNum=1&searchDiv=&searchText=',
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=pricenewsrs&listCnt=50&pageNum=1&searchDiv=&searchText='
    ]

    max_pages = None if full_fetch else 3
    all_results = []
    
    async with aiohttp.ClientSession() as session:
        for article_board_order, base_url in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(SEC_FIRM_ORDER, article_board_order)
            logger.debug(f"MERITZ Scraper Start: {firm_info.get_firm_name()} Board {article_board_order}")
            results = await fetch_all_pages_meritz(session, base_url, SEC_FIRM_ORDER, article_board_order, max_pages)
            all_results.extend(results)

    gc.collect()
    logger.info(f"MERITZ Scraper: Found {len(all_results)} total articles")
    return all_results


async def main():
    result = await MERITZ_checkNewArticle(full_fetch=True)
    logger.info(f"Total MERITZ articles fetched: {len(result)}")

if __name__ == "__main__":
    asyncio.run(main())
