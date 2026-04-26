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
from models.db_factory import get_db
from models.ConfigManager import config

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

skip_boards = set()
USE_WARP_ONLY = False  # 직접 접속 실패 시 전역적으로 WARP만 사용하도록 설정

# 프록시 설정 (환경 변수가 없으면 로컬 기본값 사용)
SOCKS_PROXY = os.getenv("SOCKS_PROXY_URL", "socks5h://localhost:9091")
LS_DIRECT_RETRIES = int(os.getenv("LS_DIRECT_RETRIES", "2"))
LS_WARP_RETRIES = int(os.getenv("LS_WARP_RETRIES", "5"))
PROXIES = {
    'http': SOCKS_PROXY,
    'https': SOCKS_PROXY
}

def get_soup_with_warp(url, headers):
    global USE_WARP_ONLY
    for attempt in range(1, LS_WARP_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, proxies=PROXIES, verify=False, timeout=20)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            if attempt < LS_WARP_RETRIES:
                time.sleep(attempt)
            else:
                logger.error(f"LS WARP 최종 실패 (시도 {attempt}/{LS_WARP_RETRIES}): {url} ({e})")
                return None

def LS_checkNewArticle(page=1, is_imported=False, skip_boards=None):
    global USE_WARP_ONLY
    SEC_FIRM_ORDER = 0
    json_data_list = []
    requests.packages.urllib3.disable_warnings()

    base_urls = config.get_urls("LS_0")
    
    # page가 1이거나 None이면 파라미터 제외, 그 외에만 currPage 추가
    if not page or str(page) == '1':
        TARGET_URL_TUPLE = tuple(base_urls)
    else:
        TARGET_URL_TUPLE = tuple(f"{url}&currPage={page}" for url in base_urls)

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

        # 1차 시도: 직접 접속. OCI 대역 차단 가능성이 있어 짧게 2회만 확인 후 WARP로 넘긴다.
        # 이미 이전에 직접 접속이 실패한 적이 있다면 즉시 soup = None으로 처리하여 WARP로 넘어가게 함.
        direct_headers = SyncWebScraper(TARGET_URL, firm_info).headers
        if USE_WARP_ONLY:
            soup = None
        else:
            for direct_attempt in range(1, LS_DIRECT_RETRIES + 1):
                try:
                    resp = requests.get(TARGET_URL, headers=direct_headers, verify=False, timeout=10)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.content, "html.parser")
                    soupList = soup.select('#contents > table > tbody > tr')
                    break
                except Exception as e:
                    soup = None
                    if direct_attempt < LS_DIRECT_RETRIES:
                        logger.info(f"LS 직접 접속 실패 {direct_attempt}/{LS_DIRECT_RETRIES}, 재시도: {TARGET_URL} ({e})")
                        time.sleep(direct_attempt)
            
            # 직접 접속 시도가 모두 실패하면 이후부터는 WARP만 사용하도록 설정
            if soup is None:
                logger.warning(f"LS 직접 접속 실패로 이후 모든 요청은 WARP를 사용합니다: {TARGET_URL}")
                USE_WARP_ONLY = True

        if soup is None:
            soup = get_soup_with_warp(TARGET_URL, direct_headers)
            if soup:
                soupList = soup.select('#contents > table > tbody > tr')
            else:
                skip_boards.add(ARTICLE_BOARD_ORDER)

        logger.info(f"{firm_info.get_firm_name()}의 {firm_info.get_board_name()} 게시판... (Found {len(soupList)} articles)")

        if not soupList and not is_imported:
            continue

        for list_item in soupList:
            try:
                WRITER = list_item.select('td')[2].get_text().strip()
                str_date = list_item.select('td')[3].get_text().strip()
                a_tag = list_item.select_one('a')
                if not a_tag: continue

                # KEY값에서 &currPage=1 부분만 정확히 제거 (공백 처리)
                raw_href = a_tag['href'].replace("amp;", "")
                LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + raw_href
                LIST_ARTICLE_URL = clean_url(LIST_ARTICLE_URL).replace("&currPage=1", "")
                
                title_text = a_tag.get_text().strip()
                LIST_ARTICLE_TITLE = title_text[title_text.find("]")+1:].strip()

                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", str_date),
                    "ARTICLE_URL": '',
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
    # 만약 currPage가 1이 아닌 다른 값이면 유지해야 할 수도 있으나, 
    # 요구사항에 따라 일단 중복 방지를 위해 필수 파라미터만 재조합
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
    global USE_WARP_ONLY
    loop = asyncio.get_event_loop()

    # 1차 시도: 직접 접속. 짧게 2회 확인한 뒤 WARP 경로로 전환한다.
    if not USE_WARP_ONLY:
        for direct_attempt in range(1, LS_DIRECT_RETRIES + 1):
            try:
                def sync_get_direct():
                    response = requests.get(url, headers=headers, verify=False, timeout=10)
                    response.raise_for_status()
                    return response.text
                return await loop.run_in_executor(None, sync_get_direct)
            except Exception as e:
                if direct_attempt < LS_DIRECT_RETRIES:
                    logger.info(f"직접 접속 실패 {direct_attempt}/{LS_DIRECT_RETRIES}, 재시도: {url} ({e})")
                    await asyncio.sleep(direct_attempt)
        
        # 직접 접속 실패 시 플래그 전환
        logger.warning(f"상세 페이지 직접 접속 실패로 이후 WARP를 사용합니다: {url}")
        USE_WARP_ONLY = True

    # 2차 시도: WARP 프록시 (최대 5회, 재시도 중간 실패 로그 생략)
    for attempt in range(1, LS_WARP_RETRIES + 1):
        try:
            def sync_get_warp():
                response = requests.get(url, headers=headers, proxies=PROXIES, verify=False, timeout=20)
                response.raise_for_status()
                return response.text
            return await loop.run_in_executor(None, sync_get_warp)
        except Exception as e:
            if attempt < LS_WARP_RETRIES:
                await asyncio.sleep(1 * attempt)
            else:
                logger.error(f"LS WARP 상세 요청 최종 실패 (시도 {attempt}/{LS_WARP_RETRIES}): {url} ({e})")
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
                attach_tag = tr.select_one("td.attach a")
                if attach_tag:
                    article["ATTACH_FILE_NAME"] = attach_tag.get_text(strip=True)

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
                            url = await create_fallback_url(article, soup)
                            article["ARTICLE_URL"] = url
                            article["TELEGRAM_URL"] = url
                            article["PDF_URL"] = url
                            article["DOWNLOAD_URL"] = url
                    else:
                        url = await create_fallback_url(article, soup)
                        article["ARTICLE_URL"] = url
                        article["TELEGRAM_URL"] = url
                        article["PDF_URL"] = url
                        article["DOWNLOAD_URL"] = url
                else:
                    url = await create_fallback_url(article, soup)
                    article["ARTICLE_URL"] = url
                    article["TELEGRAM_URL"] = url
                    article["PDF_URL"] = url
                    article["DOWNLOAD_URL"] = url

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
    db = get_db()
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
        return await create_fallback_url(article, None)

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

    return await create_fallback_url(article, None)


async def create_fallback_url(article, soup=None):
    URL_PARAM = article["REG_DT"]
    URL_PARAM_0 = "B" + URL_PARAM[:6]
    
    attach_file_name = article.get("ATTACH_FILE_NAME", "")
    if not attach_file_name and soup:
        attach_tag = soup.select_one(".attach > a")
        if attach_tag:
            attach_file_name = attach_tag.get_text(strip=True)
            
    if attach_file_name:
        safe_name = urllib.parse.quote(attach_file_name)
        # EtwBoardData 앞에 EtwFrontBoard가 붙는 경우가 많음
        fallback_url = f"https://www.ls-sec.co.kr/upload/EtwBoardData/{URL_PARAM_0}/{safe_name}"
        logger.debug(f"Fallback URL created: {fallback_url}")
        return fallback_url
    
    return ""

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
            db = get_db()
            inserted_count, updated_count = db.insert_json_data_list(all_articles)
            logger.success(f"LS: Inserted {inserted_count}, Updated {updated_count} articles.")
