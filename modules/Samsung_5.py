# -*- coding:utf-8 -*- 
import gc
import aiohttp
import asyncio
from datetime import datetime
import json
import re
import os
import sys
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper

async def Samsung_checkNewArticle():
    SEC_FIRM_ORDER      = 5
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    # 삼성증권 기업 분석
    TARGET_URL_0 =  'https://www.samsungpop.com/mbw/search/search.do?cmd=report_search&startCount=2000&TOTALVIEWCOUNT=1&range=A&writer=&NUM=&GBNM=&GBNS=&JDATE=&JTIME=&COMPONENTCD=&moreCheck=N&GUBUN=all&searchField=TITLE&periodType=3&query='
    # 삼성증권 산업 분석
    TARGET_URL_1 =  'https://www.samsungpop.com/mbw/search/search.do?cmd=report_search&startCount=0&TOTALVIEWCOUNT=3000&range=A&writer=&NUM=&GBNM=&GBNS=&JDATE=&JTIME=&COMPONENTCD=&moreCheck=N&GUBUN=industry1&searchField=TITLE&periodType=1&query='
    # 삼성증권 해외 분석
    TARGET_URL_2 =  'https://www.samsungpop.com/mbw/search/search.do?cmd=report_search&startCount=0&TOTALVIEWCOUNT=3000&range=A&writer=&NUM=&GBNM=&GBNS=&JDATE=&JTIME=&COMPONENTCD=&moreCheck=N&GUBUN=company2&searchField=TITLE&periodType=1&query='
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            logger.debug(f"Samsung Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")

            scraper = AsyncWebScraper(TARGET_URL)
            
            # HTML parse
            soup = await scraper.Get(session=session)
            if not soup:
                logger.warning(f"Failed to get soup for {TARGET_URL}")
                continue

            soupList = soup.select('#content > section.bbsLstWrap > ul > li')
            logger.info(f"Samsung Scraper: Found {len(soupList)} articles")

            for item in soupList:
                try:
                    # 제목 추출 및 정제
                    title_element = item.select_one('dt > strong')
                    if not title_element:
                        continue

                    LIST_ARTICLE_TITLE = title_element.text.strip()
                    
                    # PDF 링크 데이터 파싱
                    a_href = item.a.get("href", "").replace("javascript:downloadPdf(", "").replace(")", "").replace("'", "")
                    a_href_parts = a_href.split(",")

                    if len(a_href_parts) < 3:
                        continue

                    a_href_path = a_href_parts[0].strip()  # PDF 파일 경로
                    REG_DT = a_href_parts[2].strip().replace(";", "")       # REG_DT 값 추출 및 세미콜론 제거

                    LIST_ARTICLE_URL = f'https://www.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName={a_href_path}&contentType=application/pdf&inlineYn=Y'

                    # bbsLstCont 내부 정보 추출 (발행일, 분류, 작성자)
                    dd_elements = item.select('dd > span')
                    pub_date = dd_elements[0].text.strip() if len(dd_elements) > 0 else "N/A"
                    category = dd_elements[1].text.strip() if len(dd_elements) > 1 else "N/A"
                    author = dd_elements[2].text.strip() if len(dd_elements) > 2 else "N/A"
                    
                    LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace(f"({author})", "")
                    
                    # 결과 저장
                    json_data_list.append({
                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                        "FIRM_NM": firm_info.get_firm_name(),
                        "REG_DT": REG_DT,
                        "DOWNLOAD_URL": '',
                        "TELEGRAM_URL": LIST_ARTICLE_URL,
                            "PDF_URL": LIST_ARTICLE_URL,
                        "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                        "WRITER": author,
                        "BOARD_NM": category,
                        "SAVE_TIME": datetime.now().isoformat(),
                        "KEY": LIST_ARTICLE_URL,
                    })
                except Exception as e:
                    logger.error(f"Error parsing item: {e}")

            break
            
    # 메모리 정리
    gc.collect()

    return json_data_list
            
    # 메모리 정리
    gc.collect()

    return json_data_list

def extract_and_deduplicate(json_list):
    """
    JSON 리스트에서 앞부분 4자리값과 BOARD_NM 값을 추출하고 BOARD_NM 기준으로 중복을 제거한 후 정렬된 리스트를 반환합니다.

    Args:
        json_list: JSON 형식의 파이썬 리스트

    Returns:
        정렬된 딕셔너리 리스트 (각 딕셔너리는 "year", "board_nm" 키를 가짐)
    """

    extracted_data = []
    seen_board_nms = set()  # 중복된 BOARD_NM 값을 추적하기 위한 set

    for item in json_list:
        key_value = item.get("KEY")
        if key_value:
            file_name = re.search(r"fileName=([^&]+)", key_value).group(1)
            year = file_name[:4]
            board_nm = item.get("BOARD_NM")

            if board_nm not in seen_board_nms:  # 중복된 BOARD_NM 값이 아니면 추가
                extracted_data.append({"year": year, "board_nm": board_nm})
                seen_board_nms.add(board_nm)

    # 정렬
    def get_sort_key(item):
        return (item["year"], item["board_nm"])

    return sorted(extracted_data, key=get_sort_key)

if __name__ == "__main__":
    asyncio.run(Samsung_checkNewArticle())
