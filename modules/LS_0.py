# -*- coding:utf-8 -*- 
import os
import gc
import requests
import urllib.request
import sys
from bs4 import BeautifulSoup
import time
import asyncio
import aiohttp
from aiohttp import ClientSession
import re
import urllib.parse
from loguru import logger

from datetime import datetime, timedelta, date
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.WebScraper import SyncWebScraper
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

skip_boards = set()

PROXIES = {
    'http': 'socks5h://localhost:9091',
    'https': 'socks5h://localhost:9091'
}

def LS_checkNewArticle(page=1, is_imported=False, skip_boards=None):
    SEC_FIRM_ORDER = 0
    json_data_list = []
    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = (
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=146&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=36&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=37&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=38&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=147&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=39&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=183&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=145&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=33&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=253&currPage={page}'
    )

    if skip_boards is None:
        skip_boards = set()

    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        if ARTICLE_BOARD_ORDER in skip_boards:
            continue

        soupList = []
        soup = None

        import random
        time.sleep(random.uniform(1.0, 2.0))

        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        retries = 3
        while retries > 0:
            try:
                scraper = SyncWebScraper(TARGET_URL, firm_info, proxies=PROXIES)
                soup = scraper.Get()
                if soup is None:
                    raise ValueError("Empty response from server.")
                soupList = soup.select('#contents > table > tbody > tr')
                break
            except Exception as e:
                logger.error(f"Error fetching LS board {ARTICLE_BOARD_ORDER}: {e}. Retrying... ({retries-1} left)")
                retries -= 1
                time.sleep(5)
                if retries == 0:
                    skip_boards.add(ARTICLE_BOARD_ORDER)
                    logger.warning(f"Skipping LS board {ARTICLE_BOARD_ORDER} after 3 attempts.")
                    break

        logger.info(f"{firm_info.get_firm_name()}의 {firm_info.get_board_name()} 게시판... (Found {len(soupList)} articles)")

        if not soupList and not is_imported:
            continue

        for list_item in soupList:
            try:
                WRITER = list_item.select('td')[2].get_text().strip()
                str_date = list_item.select('td')[3].get_text().strip()
                a_tag = list_item.select_one('a')
                if not a_tag: continue

                LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + a_tag['href'].replace("amp;", "")
                LIST_ARTICLE_URL = clean_url(LIST_ARTICLE_URL)
                
                title_text = a_tag.get_text().strip()
                LIST_ARTICLE_TITLE = title_text[title_text.find("]")+1:].strip()

                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", str_date),
                    "ARTICLE_URL": '',
                    "ATTACH_URL": '',
                    "DOWNLOAD_URL": '',
                    "TELEGRAM_URL": '',
                    "PDF_URL": '',
                    "WRITER": WRITER,
                    "KEY": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error parsing LS article row: {e}")
                continue

    gc.collect()
    return json_data_list

def clean_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    required_params = {
        'board_no': query_params.get('board_no', [''])[0],
        'board_seq': query_params.get('board_seq', [''])[0],
    }
    new_query = urlencode(required_params)
    cleaned_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        '',
        new_query,
        ''
    ))
    return cleaned_url


async def fetch(session: ClientSession, url: str, headers: dict) -> str:
    try:
        loop = asyncio.get_event_loop()
        def sync_get():
            response = requests.get(url, headers=headers, proxies=PROXIES, verify=False, timeout=20)
            response.raise_for_status()
            return response.text
        
        return await loop.run_in_executor(None, sync_get)
    except Exception as e:
        if "Timeout" in str(e):
            logger.warning(f"Timeout occurred for URL: {url}")
        else:
            logger.error(f"Error requesting URL {url}: {e}")
        return None

async def process_article(session: ClientSession, article: dict, headers: dict):
    TARGET_URL = article["KEY"]

    if ".pdf" in TARGET_URL:
        article["ARTICLE_URL"] = TARGET_URL
        article["TELEGRAM_URL"] = TARGET_URL
        article["PDF_URL"] = TARGET_URL
        article["DOWNLOAD_URL"] = TARGET_URL
        return

    html_content = await fetch(session, TARGET_URL, headers)
    if not html_content:
        return

    soup = BeautifulSoup(html_content, "html.parser")
    trs = soup.select("tr")

    for tr in trs:
        th = tr.select_one("th")
        td = tr.select_one("td")

        if th and td:
            th_text = th.get_text(strip=True)
            td_text = td.get_text(strip=True)

            if th_text == "제목":
                article["ARTICLE_TITLE"] = td_text
            elif th_text == "첨부파일":
                attach_a = tr.select_one("td.attach a")
                if attach_a:
                    article["ATTACH_FILE_NAME"] = attach_a.get_text(strip=True)

                img = soup.select_one("#contents > div.tbViewCon > div > html > body > p > img") or \
                      soup.select_one("#contents > div.tbViewCon > div > p > img")

                if img:
                    img_filename = img.get("alt") or img.get("src")
                    if img_filename:
                        name, extension = os.path.splitext(img_filename)
                        match = re.search(r"_(\d{8})$", name)

                        if match:
                            date_part = match.group(1)
                            new_name = re.sub(r"_(\d{8})$", "", name)
                            new_filename = f"{date_part}_{new_name}.pdf"

                            url = await get_valid_url(new_filename, date_part, article, headers)
                            article["ARTICLE_URL"] = urllib.parse.quote(url, safe=":/")
                            article["TELEGRAM_URL"] = urllib.parse.quote(url, safe=":/")
                            article["PDF_URL"] = urllib.parse.quote(url, safe=":/")
                            article["DOWNLOAD_URL"] = urllib.parse.quote(url, safe=":/")
                        else:
                            url = await create_fallback_url(article)
                            article["ARTICLE_URL"] = urllib.parse.quote(url, safe=":/")
                            article["TELEGRAM_URL"] = urllib.parse.quote(url, safe=":/")
                            article["PDF_URL"] = urllib.parse.quote(url, safe=":/")
                            article["DOWNLOAD_URL"] = urllib.parse.quote(url, safe=":/")
                    else:
                        URL_PARAM = article["REG_DT"]
                        URL_PARAM_0 = 'B' + URL_PARAM[:6]
                        ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
                        ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%')
                        URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)
                        ATTACH_URL = f'https://www.ls-sec.co.kr/upload/EtwBoardData/{URL_PARAM_0}/{URL_PARAM_1}'
                        article["ARTICLE_URL"] = urllib.parse.quote(ATTACH_URL, safe=":/")
                        article["TELEGRAM_URL"] = urllib.parse.quote(ATTACH_URL, safe=":/")
                        article["PDF_URL"] = urllib.parse.quote(ATTACH_URL, safe=":/")
                        article["DOWNLOAD_URL"] = urllib.parse.quote(ATTACH_URL, safe=":/")
                else:
                    URL_PARAM = article["REG_DT"]
                    URL_PARAM_0 = 'B' + URL_PARAM[:6]
                    ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
                    ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%')
                    URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)
                    ATTACH_URL = f'https://www.ls-sec.co.kr/upload/EtwBoardData/{URL_PARAM_0}/{URL_PARAM_1}'
                    article['ARTICLE_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')
                    article['TELEGRAM_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')
                    article['PDF_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')
                    article['DOWNLOAD_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')

async def LS_detail(articles, firm_info=None):
    if isinstance(articles, dict):
        articles = [articles]
    elif isinstance(articles, str):
        logger.error("Error: Invalid article format. Expected a dictionary or a list.")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.ls-sec.co.kr/",
        "Connection": "keep-alive"
    }

    semaphore = asyncio.Semaphore(1)

    async def sem_process_article(session, article):
        async with semaphore:
            await process_article(session, article, headers)
            import random
            await asyncio.sleep(random.uniform(2.5, 4.5))

    async with aiohttp.ClientSession() as session:
        tasks = [sem_process_article(session, article) for article in articles]
        await asyncio.gather(*tasks)

    return articles

async def LS_detailAll(articles=None, firm_info=None):
    db = SQLiteManager()
    if articles is None:
        articles = await db.fetch_ls_detail_targets()
    
    if not articles:
        logger.info("Detail 처리가 필요한 LS 레포트가 없습니다.")
        return []

    target_articles = [a for a in articles if not str(a.get('TELEGRAM_URL', '')).lower().endswith('.pdf')]
    if not target_articles:
        return articles

    logger.info(f"총 {len(target_articles)}개의 LS 레포트에 대해 상세 정보를 추출합니다.")
    updated_articles = await LS_detail(target_articles, firm_info)
    
    for article in updated_articles:
        if article.get('TELEGRAM_URL') and str(article.get('TELEGRAM_URL')).lower().endswith('.pdf'):
            await db.update_telegram_url(
                record_id=article['report_id'], 
                telegram_url=article['TELEGRAM_URL'],
                article_title=article.get('ARTICLE_TITLE'),
                pdf_url=article.get('PDF_URL') or article.get('TELEGRAM_URL')
            )
            logger.debug(f"DB 업데이트 완료: {article.get('ARTICLE_TITLE')}")
            
    return updated_articles

async def get_valid_url(new_filename, date_part, article, headers):
    base_url = "https://msg.ls-sec.co.kr/eum/K_{filename}"
    try:
        date_obj = datetime.strptime(date_part, "%Y%m%d")
    except ValueError:
        return await create_fallback_url(article)

    date_range = [date_obj + timedelta(days=i) for i in range(-2, 3)]
    for test_date in date_range:
        test_date_str = test_date.strftime("%Y%m%d")
        test_filename = new_filename.replace(date_part, test_date_str)
        test_url = base_url.format(filename=test_filename)

        try:
            response = requests.get(test_url, headers=headers, verify=False, proxies=PROXIES, timeout=15)
            if response.status_code == 200:
                logger.debug(f"Valid URL found: {test_url}")
                return test_url
        except Exception:
            pass

    return await create_fallback_url(article)


async def create_fallback_url(article):
    URL_PARAM = article["REG_DT"]
    URL_PARAM_0 = "B" + URL_PARAM[:6]
    ATTACH_FILE_NAME = article.get("ATTACH_FILE_NAME", "")
    ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(" ", "%20").replace("[", "%5B").replace("]", "%5D").replace("%25", "%")
    URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)
    ATTACH_URL = f"https://www.ls-sec.co.kr/upload/EtwBoardData/{URL_PARAM_0}/{URL_PARAM_1}"
    logger.debug(f"Fallback URL created: {ATTACH_URL}")
    return ATTACH_URL

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'fix':
        logger.info("상세 정보 누락 건 복구 모드(fix) 실행...")
        asyncio.run(LS_detailAll())
    else:
        page = 1
        all_articles = []
        while True:
            logger.debug(f"LS Scraper: Processing Page {page}")
            articles = LS_checkNewArticle(page, is_imported=False, skip_boards=skip_boards)
            if not any(articles):
                break
            all_articles.extend(articles)
            page += 1

        if not all_articles:
            logger.info("No LS articles found.")
        else:
            db = SQLiteManager()
            inserted_count, updated_count = db.insert_json_data_list(all_articles)
            logger.success(f"LS: Inserted {inserted_count}, Updated {updated_count} articles.")
