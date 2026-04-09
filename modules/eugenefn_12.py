import asyncio
from datetime import datetime
import re  # 정규식 사용을 위한 import
import os
import sys
import json
from bs4 import BeautifulSoup
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper

SEC_FIRM_ORDER = 12

BASE_URLS = [
    "https://m.eugenefn.com/ii33rAdd.do",  # 글로벌전략
    "https://m.eugenefn.com/ii30rAdd.do",  # 국내기업분석
    "https://m.eugenefn.com/ii31rAdd.do",  # 국내산업분석
    "https://m.eugenefn.com/ii34rAdd.do"   # 해외기업분석
]
HEADERS_TEMPLATE = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148",
    "Content-Type": "application/x-www-form-urlencoded"
}

async def parse_article_list(html_text, ARTICLE_BOARD_ORDER):
    articles = []
    if html_text:
        soup = BeautifulSoup(html_text, 'html.parser')
        list_items = soup.find_all('li')
        for item in list_items:
            a_tag = item.find('a')
            if a_tag:
                url = a_tag['href']
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

async def eugene_checkNewArticle():
    all_articles = []
    for ARTICLE_BOARD_ORDER, base_url in enumerate(BASE_URLS):
        referer_url = base_url.replace('Add.do', '.do')
        firm_info = FirmInfo(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
        logger.debug(f"Eugene Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")
        
        scraper = AsyncWebScraper(target_url=base_url, headers={**HEADERS_TEMPLATE, "Referer": referer_url})
        for page_no in range(1, 6):
            payload = f"pageNo={page_no}&add=Y"
            try:
                response_soup = await scraper.Post(data=payload)
                if response_soup:
                    html_text = str(response_soup)
                    articles = await parse_article_list(html_text, ARTICLE_BOARD_ORDER)
                    all_articles.extend(articles)
                    logger.info(f"Eugene Scraper: Found {len(articles)} articles on page {page_no}")
                else:
                    logger.warning(f"Status: Failed for {base_url} (Page {page_no})")
            except Exception as e:
                logger.error(f"Error scraping {base_url} page {page_no}: {e}")

    logger.info(f"Total articles scraped: {len(all_articles)}")
    return all_articles

async def main():
    articles = await eugene_checkNewArticle()
    logger.debug(json.dumps(articles, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
