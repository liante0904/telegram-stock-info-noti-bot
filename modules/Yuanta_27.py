# -*- coding:utf-8 -*-
import os
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta, date
import sys
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.db_factory import get_db
from models.ConfigManager import config

_yuanta_base = config.get_urls("Yuanta_27")[0]
YUANTA_URL_TEMPLATE_DEFAULT = f'{_yuanta_base}?cd007={{board_code}}&pgCnt=100&page={{page}}'
YUANTA_URL_TEMPLATE_DATED = f'{_yuanta_base}?cd007={{board_code}}&pgCnt=100&startCalendar={{start_date}}&endCalendar={{end_date}}&page={{page}}'

# Board specific codes
YUANTA_BOARD_CODES = ["RE01", "RE02", "RB30A", "RB30B", "RB30C", "RF09"]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}

async def scrape_yuanta_page_async(session, target_url, sec_firm_order, article_board_order, is_imported, semaphore):
    """
    Asynchronously scrapes a single page of Yuanta Securities research articles with 3 retries.
    """
    async with semaphore:
        firm_info = FirmInfo(sec_firm_order=sec_firm_order, article_board_order=article_board_order)
        
        retries = 5
        for attempt in range(1, retries + 1):
            try:
                if attempt > 1:
                    await asyncio.sleep(0.5 * attempt) # 재시도 시 대기 시간 증가
                async with session.get(target_url, headers=HEADERS, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        soupList = soup.select('div.tblRow tbody tr.js-moveRS')
                        if not soupList:
                            return []

                        json_data_list = []
                        for item in soupList:
                            try:
                                post_date_str = item.select_one('td:nth-of-type(1)').get_text(strip=True)
                                POST_DATE = datetime.strptime(post_date_str, '%Y/%m/%d').date()
                                title_tag = item.select_one('td.txtL a')
                                LIST_ARTICLE_TITLE = title_tag.get_text(strip=True)

                                if article_board_order == 0: # 기업분석
                                    stock_name_tag = item.select_one('td:nth-of-type(2) a.js-jongname')
                                    if stock_name_tag:
                                        stock_name = stock_name_tag.get_text(strip=True)
                                        LIST_ARTICLE_TITLE = f"{stock_name}: {LIST_ARTICLE_TITLE}"
                                
                                seq = title_tag['data-seq']
                                LIST_ARTICLE_URL = f"https://www.myasset.com/myasset/research/rs_list/rs_view.cmd?cd007={firm_info.get_board_code()}&SEQ={seq}"
                                writers = [a.get_text(strip=True) for a in item.select('td:nth-of-type(7) a.js-link')]
                                WRITER = ', '.join(writers)

                                pdf_tag = item.select_one('a.ico.acrobat')
                                DOWNLOAD_URL = ''
                                if pdf_tag and pdf_tag.has_attr('data-seq'):
                                    pdf_path = pdf_tag['data-seq']
                                    DOWNLOAD_URL = f"http://file.myasset.com/sitemanager/upload/{pdf_path}"

                                json_data_list.append({
                                    "SEC_FIRM_ORDER": sec_firm_order,
                                    "ARTICLE_BOARD_ORDER": article_board_order,
                                    "FIRM_NM": firm_info.get_firm_name(),
                                    "REG_DT": POST_DATE.strftime("%Y%m%d"),
                                    "ARTICLE_URL": LIST_ARTICLE_URL,
                                    "DOWNLOAD_URL": DOWNLOAD_URL,
                                    "TELEGRAM_URL": DOWNLOAD_URL,
                                    "WRITER": WRITER,
                                    "KEY": LIST_ARTICLE_URL,
                                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                                    "SAVE_TIME": datetime.now().isoformat()
                                })
                            except Exception as e:
                                logger.error(f"Error parsing article item: {e}")
                                continue
                        return json_data_list
                    elif response.status >= 500:
                        if attempt == retries:
                            logger.warning(f"Yuanta Server Error ({response.status}) at {target_url}. Final failure after {retries} attempts.")
                    else:
                        if attempt == retries:
                            logger.warning(f"Unexpected status {response.status} at {target_url}. Final failure after {retries} attempts.")
                            return None
            except Exception as e:
                if attempt == retries:
                    logger.warning(f"Yuanta request final failure for {target_url}: {e}")
                    return None
        return None

async def Yuanta_checkNewArticle(is_imported_flag=False):
    """유안타증권 비동기 데이터 수집 진입점 (표준화된 명칭)"""
    all_articles = []
    SEC_FIRM_ORDER = 27
    semaphore = asyncio.Semaphore(5)

    async with aiohttp.ClientSession() as session:
        if is_imported_flag:
            logger.info("--- Starting full historical scrape for Yuanta (Async) ---")
            end_date = date.today()
            consecutive_months_with_no_articles = 0

            while True:
                start_date = end_date.replace(day=1)
                logger.info(f"Scraping range: {start_date.strftime('%Y-%m')}")
                articles_in_month_count = 0
                for i, board_code in enumerate(YUANTA_BOARD_CODES):
                    page = 1
                    while True:
                        target_url = YUANTA_URL_TEMPLATE_DATED.format(
                            board_code=board_code,
                            start_date=start_date.strftime('%Y%m%d'),
                            end_date=end_date.strftime('%Y%m%d'),
                            page=page
                        )
                        articles_on_page = await scrape_yuanta_page_async(session, target_url, SEC_FIRM_ORDER, i, is_imported_flag, semaphore)
                        if articles_on_page:
                            all_articles.extend(articles_on_page)
                            articles_in_month_count += len(articles_on_page)
                            page += 1
                        else:
                            break
                
                if not articles_in_month_count:
                    consecutive_months_with_no_articles += 1
                else:
                    consecutive_months_with_no_articles = 0

                if consecutive_months_with_no_articles >= 6:
                    break
                end_date = start_date - timedelta(days=1)
        else:
            logger.info("--- Starting recent scrape for Yuanta (Async) ---")
            tasks = []
            for i, board_code in enumerate(YUANTA_BOARD_CODES):
                for page in range(1, 6):
                    target_url = YUANTA_URL_TEMPLATE_DEFAULT.format(board_code=board_code, page=page)
                    tasks.append(scrape_yuanta_page_async(session, target_url, SEC_FIRM_ORDER, i, is_imported_flag, semaphore))
            
            results = await asyncio.gather(*tasks)
            for result in results:
                if result:
                    all_articles.extend(result)

    return all_articles

if __name__ == "__main__":
    is_imported_flag = "--all" in sys.argv
    articles = asyncio.run(Yuanta_checkNewArticle(is_imported_flag))
    if articles:
        db = get_db()
        db.insert_json_data_list(articles)
