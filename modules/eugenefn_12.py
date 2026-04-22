import asyncio
from datetime import datetime
from datetime import date as date_cls
import re  # 정규식 사용을 위한 import
import os
import sys
import json
import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config
from modules.eugene_auth import (
    COOKIE_PATH,
    cookie_dict_to_header,
    authenticated_session,
    get_eugene_credentials,
    is_login_page,
    load_cookie_dict,
    login_and_save_cookies,
)

SEC_FIRM_ORDER = 12

BASE_URLS = config.get_urls("eugenefn_12")

def get_eugene_headers(include_cookie=True):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Content-Type": "application/x-www-form-urlencoded",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"'
    }
    
    if include_cookie:
        # 쿠키 로드 시도
        cookies = load_cookie_dict(COOKIE_PATH)
        if cookies:
            try:
                headers["Cookie"] = cookie_dict_to_header(cookies)
                logger.info("Eugene Scraper: Loaded cookies from eugene_cookies.json")
            except Exception as e:
                logger.error(f"Eugene Scraper: Failed to load cookies: {e}")
            
    return headers


def _parse_report_date(reg_dt):
    if not reg_dt:
        return None
    try:
        return datetime.strptime(reg_dt, "%Y%m%d").date()
    except Exception:
        return None

async def parse_article_list(html_text, ARTICLE_BOARD_ORDER):
    articles = []
    if html_text:
        soup = BeautifulSoup(html_text, 'html.parser')
        list_items = soup.select('ul#list > li')
        if not list_items:
            list_items = soup.find_all('li')
        for item in list_items:
            a_tag = item.find('a')
            if a_tag:
                url = a_tag['href']
                # 상세 페이지 URL이 상대 경로인 경우 처리
                if url.startswith('/'):
                    url = 'https://m.eugenefn.com' + url
                
                # 더블 슬래시(//) 정규화 (보안 솔루션이나 라이브러리 오작동 방지)
                if "//" in url:
                    # 프로토콜 부분(https://)을 제외한 나머지 부분의 더블 슬래시 제거
                    protocol, rest = url.split("://", 1)
                    url = f"{protocol}://{rest.replace('//', '/')}"
                
                title_tag = item.find('strong', class_='title line2')
                title = title_tag.text.strip() if title_tag else ''
                
                date_tag = item.find('span', class_='date')
                date = date_tag.text.strip() if date_tag else ''
                
                # REG_DT 포맷 변경: yyyyMMdd
                reg_dt = re.sub(r"[-./]", "", date)
                
                writer_tag = item.find('span', class_='writer')
                writer = writer_tag.text.strip() if writer_tag else ''
                
                firm_info = FirmInfo(
                    sec_firm_order=SEC_FIRM_ORDER,
                    article_board_order=ARTICLE_BOARD_ORDER
                )

                articles.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": reg_dt,
                    "WRITER": writer,
                    "ARTICLE_URL": '',
                    "ATTACH_URL": '',  # 필요시 변경
                    "DOWNLOAD_URL": url,  # 필요시 변경
                    "TELEGRAM_URL": url,
                    "PDF_URL": url,
                    "ARTICLE_TITLE": title,
                    "KEY": url,
                    "SAVE_TIME": datetime.now().isoformat()
                })

    return articles


async def refresh_eugene_cookies():
    userid, password, cert_password = get_eugene_credentials()
    if not userid or not password:
        raise RuntimeError("Set EUGENE_USERID and EUGENE_PASSWORD in your environment or secrets.json.")
    await login_and_save_cookies(userid, password, cert_password, cookie_path=COOKIE_PATH)
    logger.info("Eugene Scraper: Refreshed eugene_cookies.json")

async def eugene_checkNewArticle(full_fetch=False, since_date=None):
    all_articles = []
    if since_date is None and full_fetch:
        since_date = date_cls(datetime.now().year, 1, 1)
    
    for ARTICLE_BOARD_ORDER, base_url in enumerate(BASE_URLS):
        referer_url = base_url.replace('Add.do', '.do')
        main_url = referer_url
        firm_info = FirmInfo(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
        logger.debug(f"Eugene Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")

        board_articles = []
        needs_retry = True

        for attempt in range(2):
            if attempt == 1:
                try:
                    await refresh_eugene_cookies()
                except Exception as e:
                    logger.error(f"Eugene Scraper: failed to refresh cookies for {base_url}: {e}")
                    break

            headers = get_eugene_headers(include_cookie=False)
            current_headers = headers.copy()
            current_headers["Referer"] = referer_url
            session_failed = False

            userid, password, cert_password = get_eugene_credentials()
            async with authenticated_session(userid, password, cert_password, headers=current_headers) as session:
                first_page_html = ""
                first_page_url = ""
                try:
                    async with session.get(main_url, allow_redirects=True) as response:
                        response.raise_for_status()
                        first_page_html = await response.text()
                        first_page_url = str(response.url)
                except Exception as e:
                    logger.debug(f"Eugene Scraper: initial GET failed for {main_url}: {e}")

                if is_login_page(first_page_html, first_page_url):
                    session_failed = True
                elif first_page_html:
                    try:
                        first_articles = await parse_article_list(first_page_html, ARTICLE_BOARD_ORDER)
                        board_articles.extend(first_articles)
                        logger.info(f"Eugene Scraper: Found {len(first_articles)} articles on page 1")
                    except Exception as e:
                        logger.error(f"Error parsing first page for {main_url}: {e}")

                if not session_failed:
                    page_no = 2
                    while True:
                        payload = {
                            "pageNo": str(page_no),
                            "add": "Y",
                        }
                        try:
                            async with session.post(base_url, data=payload, allow_redirects=True) as response:
                                response.raise_for_status()
                                html_text = await response.text()
                                final_url = str(response.url)

                            if is_login_page(html_text, final_url):
                                session_failed = True
                                logger.warning(f"Eugene Scraper: session expired while fetching {base_url} page {page_no}")
                                break

                            articles = await parse_article_list(html_text, ARTICLE_BOARD_ORDER)
                            if not articles:
                                logger.info(f"Eugene Scraper: No more articles on page {page_no} for {base_url}")
                                break

                            board_articles.extend(articles)
                            logger.info(f"Eugene Scraper: Found {len(articles)} articles on page {page_no}")

                            if since_date is not None:
                                oldest_date = None
                                for article in articles:
                                    parsed = _parse_report_date(article.get("REG_DT"))
                                    if parsed is not None:
                                        oldest_date = parsed if oldest_date is None else min(oldest_date, parsed)

                                if oldest_date is not None and oldest_date < since_date:
                                    logger.info(
                                        f"Eugene Scraper: Reached cutoff on page {page_no} "
                                        f"for {base_url} (oldest={oldest_date}, cutoff={since_date})"
                                    )
                                    break
                            page_no += 1
                        except Exception as e:
                            logger.error(f"Error scraping {base_url} page {page_no}: {e}")
                            session_failed = True
                            break

            if session_failed and attempt == 0:
                board_articles = []
                continue

            needs_retry = False
            break

        if needs_retry:
            logger.warning(f"Eugene Scraper: board scrape ended with retry exhaustion for {base_url}")

        all_articles.extend(board_articles)

    logger.info(f"Total articles scraped: {len(all_articles)}")
    return all_articles

async def main():
    articles = await eugene_checkNewArticle()
    logger.debug(json.dumps(articles, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
