# -*- coding:utf-8 -*-
import os
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta, date
import sys
from dateutil.relativedelta import relativedelta
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

# Base URL templates
YUANTA_URL_TEMPLATE_DEFAULT = 'https://www.myasset.com/myasset/research/rs_list/rs_list.cmd?cd007={board_code}&pgCnt=100&page={page}'
YUANTA_URL_TEMPLATE_DATED = 'https://www.myasset.com/myasset/research/rs_list/rs_list.cmd?cd007={board_code}&pgCnt=100&startCalendar={start_date}&endCalendar={end_date}&page={page}'

# Board specific codes
YUANTA_BOARD_CODES = ["RE01", "RE02", "RB30A", "RB30B", "RB30C", "RF09"]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}

def get_yuanta_pdf_url_from_detail(detail_url):
    """
    상세 페이지를 방문하여 PDF 다운로드 URL을 추출합니다.
    """
    try:
        detail_headers = HEADERS.copy()
        detail_headers['Referer'] = 'https://www.myasset.com/'
        
        response = requests.get(detail_url, headers=detail_headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 상세 페이지 내 다운로드 버튼 탐색
        # <a href='#' cmd-type='download' data-seq='...'> 패턴
        download_btn = soup.select_one("a[cmd-type='download']")
        if download_btn and download_btn.has_attr('data-seq'):
            data_seq = download_btn['data-seq']
            return f"https://www.myasset.com/myasset/common/commonFile/downloadFromFileServer.cmd?ATTACH_FILE={data_seq}"
            
        # 대체 패턴: 링크 텍스트에 PDF나 다운로드 문구가 포함된 경우
        for a in soup.find_all('a', href=True):
            if 'downloadFromFileServer.cmd' in a['href']:
                return a['href'] if a['href'].startswith('http') else f"https://www.myasset.com{a['href']}"
                
    except Exception as e:
        logger.error(f"Error fetching Yuanta detail page ({detail_url}): {e}")
    return ""

def scrape_yuanta_page(target_url, sec_firm_order, article_board_order, is_imported):
    """
    Scrapes a single page of Yuanta Securities research articles.
    """
    json_data_list = []
    firm_info = FirmInfo(sec_firm_order=sec_firm_order, article_board_order=article_board_order)

    try:
        response = requests.get(target_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        soupList = soup.select('div.tblRow tbody tr.js-moveRS')

        if not soupList:
            return []

    except Exception as e:
        logger.error(f"Error fetching data for {target_url}: {e}")
        return None

    for item in soupList:
        try:
            post_date_str = item.select_one('td:nth-of-type(1)').get_text(strip=True)
            POST_DATE = datetime.strptime(post_date_str, '%Y/%m/%d').date()

            title_tag = item.select_one('td.txtL a')
            if not title_tag: continue
            
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

            # Step 1: 목록에서 PDF 링크 추출 시도 (새로운 API 형식 우선 적용)
            pdf_tag = item.select_one('a.ico.acrobat')
            DOWNLOAD_URL = ''
            if pdf_tag and pdf_tag.has_attr('data-seq'):
                data_seq = pdf_tag['data-seq']
                # 구형 file.myasset.com 대신 안정적인 다운로드 API 주소 사용
                DOWNLOAD_URL = f"https://www.myasset.com/myasset/common/commonFile/downloadFromFileServer.cmd?ATTACH_FILE={data_seq}"

            # Step 2: 목록에 링크가 없거나 불완전하면 상세 페이지 파싱 (최근 7일 이내 게시물 위주로 상세 조회 권장)
            if not DOWNLOAD_URL:
                logger.debug(f"Yuanta: No PDF link in list, checking detail page for '{LIST_ARTICLE_TITLE[:20]}...'")
                DOWNLOAD_URL = get_yuanta_pdf_url_from_detail(LIST_ARTICLE_URL)
                if DOWNLOAD_URL:
                    logger.debug(f"Yuanta: Found PDF link in detail: {DOWNLOAD_URL}")

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
                "PDF_URL": '',
                "WRITER": WRITER,
                "KEY": LIST_ARTICLE_URL,
                "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                "SAVE_TIME": final_save_time_str
            })
        except Exception as e:
            logger.error(f"Error parsing Yuanta article row: {e}")
            continue
            
    return json_data_list

def yuanta_detail(articles):
    if isinstance(articles, dict):
        articles = [articles]
    for article in articles:
        if not article.get("TELEGRAM_URL"):
             article["TELEGRAM_URL"] = article.get("DOWNLOAD_URL", "")
        article["PDF_URL"] = article.get("DOWNLOAD_URL", "")
    return articles

def Yuanta_checkNewArticle(is_imported_flag=False):
    all_articles = []
    SEC_FIRM_ORDER = 27

    if is_imported_flag:
        logger.info("--- Starting full historical scrape for Yuanta Securities ---")
        end_date = date.today()
        consecutive_months_with_no_articles = 0

        while True:
            start_date = end_date.replace(day=1)
            articles_found_this_month = 0
            logger.debug(f"Scraping range: {start_date} to {end_date}")

            for i, board_code in enumerate(YUANTA_BOARD_CODES):
                page = 1
                while True:
                    target_url = YUANTA_URL_TEMPLATE_DATED.format(
                        board_code=board_code,
                        start_date=start_date.strftime('%Y%m%d'),
                        end_date=end_date.strftime('%Y%m%d'),
                        page=page
                    )
                    new_articles = scrape_yuanta_page(target_url, SEC_FIRM_ORDER, i, is_imported_flag)
                    if new_articles:
                        all_articles.extend(new_articles)
                        articles_found_this_month += len(new_articles)
                        page += 1
                        time.sleep(0.5)
                    else:
                        break
            
            if articles_found_this_month == 0:
                consecutive_months_with_no_articles += 1
            else:
                consecutive_months_with_no_articles = 0

            if consecutive_months_with_no_articles >= 3:
                break
            end_date = start_date - timedelta(days=1)

    else:
        logger.info("--- Starting scrape for recent Yuanta Securities articles ---")
        for i, board_code in enumerate(YUANTA_BOARD_CODES):
            page = 1
            while page <= 5:
                target_url = YUANTA_URL_TEMPLATE_DEFAULT.format(board_code=board_code, page=page)
                new_articles = scrape_yuanta_page(target_url, SEC_FIRM_ORDER, i, is_imported_flag)
                if new_articles:
                    all_articles.extend(new_articles)
                else:
                    break
                page += 1
                time.sleep(0.5)

    if not all_articles:
        logger.info("No Yuanta articles found.")
        return []
    else:
        processed_articles = yuanta_detail(all_articles)
        logger.info(f"Yuanta Scraper: Total {len(processed_articles)} articles scraped")
        return processed_articles

if __name__ == "__main__":
    is_imported_flag = "--all" in sys.argv
    articles = Yuanta_checkNewArticle(is_imported_flag)
    if articles:
        db = SQLiteManager()
        inserted_count, updated_count = db.insert_json_data_list(articles)
        logger.success(f"Yuanta: Inserted {inserted_count}, Updated {updated_count} articles.")
