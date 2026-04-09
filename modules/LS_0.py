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

from datetime import datetime, timedelta, date
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.WebScraper import SyncWebScraper
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

import urllib3
# SSL 경고 메시지 숨기기 (로그 정돈)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 전역 변수 선언
skip_boards = set()

# Cloudflare WARP SOCKS5 프록시 설정 (9091 포트)
PROXIES = {
    'http': 'socks5h://localhost:9091',
    'https': 'socks5h://localhost:9091'
}

def LS_checkNewArticle(page=1, is_imported=False, skip_boards=None):
    SEC_FIRM_ORDER = 0
    json_data_list = []
    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = (
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=146&currPage={page}',    #"이슈브리프", 
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=36&currPage={page}',     #"기업분석",
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=37&currPage={page}',     #"산업분석",   
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=38&currPage={page}',     #"투자전략",   
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=147&currPage={page}',    #"Quant",      
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=39&currPage={page}',     #"Macro",      
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=183&currPage={page}',    #"FI/ Credit", 
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=145&currPage={page}',    #"Commodity",  
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=33&currPage={page}',     #"정기자료", 
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=253&currPage={page}'     #"해외리서치"], 
    )

    if skip_boards is None:
        skip_boards = set()

    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        if ARTICLE_BOARD_ORDER in skip_boards:
            continue

        # 게시판 이동 시 1~2초 랜덤 휴식 (보수적 접근)
        import random
        time.sleep(random.uniform(1.0, 2.0))

        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        retries = 3
        while retries > 0:
            try:
                # SyncWebScraper에 프록시 전달
                scraper = SyncWebScraper(TARGET_URL, firm_info, proxies=PROXIES)
                soup = scraper.Get()
                if soup is None:
                    raise ValueError("Empty response from server.")
                soupList = soup.select('#contents > table > tbody > tr')
                break
            except Exception as e:
                print(f"Error fetching data: {e}. Retrying... ({retries-1} left)")
                retries -= 1
                time.sleep(5)
                if retries == 0:
                    skip_boards.add(ARTICLE_BOARD_ORDER)
                    continue

        print(f"{firm_info.get_firm_name()}의 {firm_info.get_board_name()} 게시판...")

        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        if not soupList and not is_imported:
            continue

        for list in soupList:
            try:
                WRITER = list.select('td')[2].get_text()
                str_date = list.select('td')[3].get_text()
                list = list.select('a')
                LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", "")
                LIST_ARTICLE_URL = clean_url(LIST_ARTICLE_URL)
                LIST_ARTICLE_TITLE = list[0].get_text()
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]")+1:len(LIST_ARTICLE_TITLE)]
                POST_DATE = str_date.strip()

                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", POST_DATE),
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
            except IndexError:
                print("IndexError: list index out of range - Skipping this board.")
                skip_boards.add(ARTICLE_BOARD_ORDER)  # Add to skip_boards on IndexError
                break  # Skip the rest of this board’s articles

    del soup
    gc.collect()
    return json_data_list

def clean_url(url):
    # URL 파싱
    parsed_url = urlparse(url)
    
    # 필요한 쿼리 파라미터 추출
    query_params = parse_qs(parsed_url.query)
    required_params = {
        'board_no': query_params.get('board_no', [''])[0],
        'board_seq': query_params.get('board_seq', [''])[0],
    }
    
    # 새로운 쿼리 문자열 생성
    new_query = urlencode(required_params)
    
    # 새 URL 구성
    cleaned_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        '',  # params
        new_query,  # 새로운 쿼리
        ''  # fragment
    ))
    
    return cleaned_url


async def fetch(session: ClientSession, url: str, headers: dict) -> str:
    """
    WARP SOCKS5 프록시(9091)를 경유하여 요청을 수행합니다.
    aiohttp 대신 requests를 사용하여 SOCKS5H(DNS 우회) 호환성을 확보합니다.
    """
    try:
        # 동기 함수인 requests.get을 비동기적으로 실행
        loop = asyncio.get_event_loop()
        def sync_get():
            response = requests.get(url, headers=headers, proxies=PROXIES, verify=False, timeout=20)
            response.raise_for_status()
            return response.text
        
        return await loop.run_in_executor(None, sync_get)
    except Exception as e:
        if "Timeout" in str(e):
            print(f"Timeout occurred for URL: {url}")
        else:
            print(f"Error requesting URL {url}: {e}")
        return None

async def process_article(session: ClientSession, article: dict, headers: dict):
    print("process_article")
    TARGET_URL = article["KEY"]

    # '.pdf' 처리
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
                        # url = create_fallback_url(article)
                        # img가 None인 경우 대체 로직 실행
                        URL_PARAM = article["REG_DT"]
                        URL_PARAM_0 = 'B' + URL_PARAM[:6]

                        ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
                        ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%')
                        URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)

                        ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
                        url = ATTACH_URL.format(URL_PARAM_0, URL_PARAM_1)
                        article["ARTICLE_URL"] = urllib.parse.quote(url, safe=":/")
                        article["TELEGRAM_URL"] = urllib.parse.quote(url, safe=":/")
                        article["PDF_URL"] = urllib.parse.quote(url, safe=":/")
                        article["DOWNLOAD_URL"] = urllib.parse.quote(url, safe=":/")
                else:
                    # img가 None인 경우 대체 로직 실행
                    URL_PARAM = article["REG_DT"]
                    URL_PARAM_0 = 'B' + URL_PARAM[:6]

                    ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
                    ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%')
                    URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)

                    ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
                    url = ATTACH_URL.format(URL_PARAM_0, URL_PARAM_1)

                    article['ARTICLE_URL'] = urllib.parse.quote(url, safe=':/')
                    article['TELEGRAM_URL'] = urllib.parse.quote(url, safe=':/')
                    article['PDF_URL'] = urllib.parse.quote(url, safe=':/')
                    article['DOWNLOAD_URL'] = urllib.parse.quote(url, safe=':/')

async def LS_detail(articles, firm_info=None):
    if isinstance(articles, dict):
        articles = [articles]
    elif isinstance(articles, str):
        print("Error: Invalid article format. Expected a dictionary or a list of dictionaries.")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.ls-sec.co.kr/",
        "Connection": "keep-alive"
    }

    semaphore = asyncio.Semaphore(1)  # 동시에 1개만 처리

    async def sem_process_article(session, article):
        async with semaphore:
            await process_article(session, article, headers)
            # 상세 페이지 요청 후 2.5 ~ 4.5초 랜덤 휴식 (매우 보수적)
            import random
            await asyncio.sleep(random.uniform(2.5, 4.5))

    async with aiohttp.ClientSession() as session:
        tasks = [sem_process_article(session, article) for article in articles]
        await asyncio.gather(*tasks)

    # print(articles)
    return articles

async def LS_detailAll(articles=None, firm_info=None):
    db = SQLiteManager()
    
    # 전달받은 articles가 없으면 DB에서 직접 조회
    if articles is None:
        articles = await db.fetch_ls_detail_targets()
    
    if not articles:
        print("Detail 처리가 필요한 LS 레포트가 없습니다.")
        return []

    # TELEGRAM_URL이 .pdf로 끝나지 않는 레포트들만 필터링
    target_articles = [a for a in articles if not str(a.get('TELEGRAM_URL', '')).lower().endswith('.pdf')]
    
    if not target_articles:
        return articles

    print(f"총 {len(target_articles)}개의 LS 레포트에 대해 상세 정보를 추출합니다.")
    updated_articles = await LS_detail(target_articles, firm_info)
    
    # 추출된 정보를 DB에 업데이트
    for article in updated_articles:
        # TELEGRAM_URL이 제대로 추출되었고 .pdf로 끝나는 경우만 업데이트
        if article.get('TELEGRAM_URL') and str(article.get('TELEGRAM_URL')).lower().endswith('.pdf'):
            await db.update_telegram_url(
                record_id=article['report_id'], 
                telegram_url=article['TELEGRAM_URL'],
                article_title=article.get('ARTICLE_TITLE'),
                pdf_url=article.get('PDF_URL') or article.get('TELEGRAM_URL')
            )
            print(f"DB 업데이트 완료: {article.get('ARTICLE_TITLE')}")
            
    return updated_articles

async def get_valid_url(new_filename, date_part, article, headers):
    """
    새로운 URL을 시도하며 상태코드 200인 URL을 찾습니다.
    """
    base_url = "https://msg.ls-sec.co.kr/eum/K_{filename}"
    try:
        date_obj = datetime.strptime(date_part, "%Y%m%d")
    except ValueError:
        print("Invalid date format in date_part:", date_part)
        return await create_fallback_url(article)

    # 날짜 기반으로 앞뒤 2일 추가 탐색
    date_range = [date_obj + timedelta(days=i) for i in range(-2, 3)]
    for test_date in date_range:
        test_date_str = test_date.strftime("%Y%m%d")
        test_filename = new_filename.replace(date_part, test_date_str)
        test_url = base_url.format(filename=test_filename)

        try:
            # get_valid_url에도 프록시 적용
            response = requests.get(test_url, headers=headers, verify=False, proxies=PROXIES, timeout=15)
            if response.status_code == 200:
                print(f"Valid URL found: {test_url}")
                return test_url
            else:
                print(f"URL {test_url} returned status code {response.status_code}")
        except requests.RequestException as e:
            print(f"Error accessing {test_url}: {e}")

    # 5일 동안 유효한 URL을 찾지 못한 경우
    return await create_fallback_url(article)


async def create_fallback_url(article):
    """
    5일 동안 유효한 URL을 찾지 못한 경우, fallback 로직으로 URL 생성.
    """
    URL_PARAM = article["REG_DT"]
    URL_PARAM_0 = "B" + URL_PARAM[:6]
    ATTACH_FILE_NAME = article["ATTACH_FILE_NAME"]
    ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(" ", "%20").replace("[", "%5B").replace("]", "%5D").replace("%25", "%")
    URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)
    ATTACH_URL = f"https://www.ls-sec.co.kr/upload/EtwBoardData/{URL_PARAM_0}/{URL_PARAM_1}"
    print("Fallback URL created:", ATTACH_URL)
    
    return ATTACH_URL

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'fix':
        print("상세 정보 누락 건 복구 모드(fix) 실행...")
        asyncio.run(LS_detailAll())
    else:
        page = 1
        all_articles = []

        while True:
            print(f"Page:{page}.. Process..")
            articles = LS_checkNewArticle(page, is_imported=False, skip_boards=skip_boards)
            if not any(articles):
                break  # Exit loop if no articles found
            all_articles.extend(articles)
            page += 1

        if not all_articles:
            print("No articles found.")
        else:
            db = SQLiteManager()
            inserted_count = db.insert_json_data_list(all_articles)
            print(f"Inserted {inserted_count} articles.")
