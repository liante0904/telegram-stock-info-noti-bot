# -*- coding:utf-8 -*-
import os
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta, date
import sys
from dateutil.relativedelta import relativedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

# Base URL templates
YUANTA_URL_TEMPLATE_DEFAULT = 'https://www.myasset.com/myasset/research/rs_list/rs_list.cmd?cd007={board_code}&pgCnt=100&page={page}'
YUANTA_URL_TEMPLATE_DATED = 'https://www.myasset.com/myasset/research/rs_list/rs_list.cmd?cd007={board_code}&pgCnt=100&startCalendar={start_date}&endCalendar={end_date}&page={page}'

# Board specific codes
YUANTA_BOARD_CODES = ["RE01", "RE02", "RB30A", "RB30B", "RB30C", "RF09"]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}

async def scrape_yuanta_page_async(session, target_url, sec_firm_order, article_board_order, is_imported, semaphore):
    """
    Asynchronously scrapes a single page of Yuanta Securities research articles.
    """
    async with semaphore:
        firm_info = FirmInfo(sec_firm_order=sec_firm_order, article_board_order=article_board_order)
        try:
            # Add a small delay to be polite to the server
            await asyncio.sleep(0.1)
            async with session.get(target_url, headers=HEADERS) as response:
                response.raise_for_status()
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

                        save_time_dt = datetime.now()
                        final_save_time_str = save_time_dt.isoformat()

                        if is_imported:
                            adjusted_save_time_dt = datetime.combine(POST_DATE, save_time_dt.time())
                            final_save_time_str = adjusted_save_time_dt.isoformat()

                        json_data_list.append({
                            "SEC_FIRM_ORDER": sec_firm_order,
                            "ARTICLE_BOARD_ORDER": article_board_order,
                            "FIRM_NM": firm_info.get_firm_name(),
                            "REG_DT": POST_DATE.strftime("%Y%m%d"),
                            "ARTICLE_URL": LIST_ARTICLE_URL,
                            "ATTACH_URL": DOWNLOAD_URL,
                            "DOWNLOAD_URL": DOWNLOAD_URL,
                            "TELEGRAM_URL": '',
                            "WRITER": WRITER,
                            "KEY": LIST_ARTICLE_URL,
                            "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                            "SAVE_TIME": final_save_time_str
                        })
                    except Exception as e:
                        print(f"Error parsing an article item: {e}")
                        continue
                return json_data_list

        except Exception as e:
            # print(f"Error fetching or processing {target_url}: {e}")
            return None

def yuanta_detail(articles):
    if isinstance(articles, dict):
        articles = [articles]
    for article in articles:
        if not article.get("TELEGRAM_URL"):
             article["TELEGRAM_URL"] = article.get("DOWNLOAD_URL", "")
    return articles

async def main():
    all_articles = []
    is_imported_flag = "--all" in sys.argv
    SEC_FIRM_ORDER = 27
    
    # Semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(10)

    async with aiohttp.ClientSession() as session:
        if is_imported_flag:
            # --- Full historical scrape logic ---
            print("--- Starting full historical scrape for Yuanta Securities (Async) ---")
            
            end_date = date.today()
            consecutive_months_with_no_articles = 0

            while True:
                start_date = end_date.replace(day=1)
                print(f"\n--- Scraping date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ---")

                articles_in_month_count = 0
                for i, board_code in enumerate(YUANTA_BOARD_CODES):
                    page = 1
                    while True:
                        firm_info = FirmInfo(sec_firm_order=SEC_FIRM_ORDER, article_board_order=i)
                        print(f"Checking {firm_info.get_board_name()} - {start_date.strftime('%Y-%m')} - Page {page}")
                        
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
                            # No more pages for this board in this month
                            break
                
                if not articles_in_month_count:
                    consecutive_months_with_no_articles += 1
                    print(f"No articles found for this month. Consecutive empty months: {consecutive_months_with_no_articles}")
                else:
                    consecutive_months_with_no_articles = 0

                if consecutive_months_with_no_articles >= 6:
                    print("Found 6 consecutive months with no articles. Assuming end of historical data.")
                    break

                # Move to the previous month
                end_date = start_date - timedelta(days=1)

        else:
            # --- Recent articles scrape logic ---
            print("--- Starting scrape for recent Yuanta Securities articles (Async) ---")
            tasks = []
            for i, board_code in enumerate(YUANTA_BOARD_CODES):
                for page in range(1, 6): # Scrape first 5 pages
                    target_url = YUANTA_URL_TEMPLATE_DEFAULT.format(board_code=board_code, page=page)
                    tasks.append(scrape_yuanta_page_async(session, target_url, SEC_FIRM_ORDER, i, is_imported_flag, semaphore))
            
            results = await asyncio.gather(*tasks)
            for result in results:
                if result:
                    all_articles.extend(result)

    if not all_articles:
        print("No articles were scraped.")
    else:
        processed_articles = yuanta_detail(all_articles)
        print(f"\n--- Scraped {len(processed_articles)} Total Articles ---")
        
        if is_imported_flag:
            print("Saving all scraped articles to the database...")
            db = SQLiteManager()
            inserted_count = db.insert_json_data_list(processed_articles, 'data_main_daily_send')
            print(f"Inserted {inserted_count} articles into the database.")
        else:
            print("Saving all recent scraped articles to the database...")
            db = SQLiteManager()
            inserted_count = db.insert_json_data_list(processed_articles, 'data_main_daily_send')
            print(f"Inserted {inserted_count} articles into the database.")

if __name__ == "__main__":
    # Ensure you have dateutil installed: pip install python-dateutil
    asyncio.run(main())
