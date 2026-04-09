# -*- coding:utf-8 -*- 
import gc
import requests
import re
from datetime import datetime
from loguru import logger

from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo


def DS_checkNewArticle():
    SEC_FIRM_ORDER = 11  # DS투자증권 고유 식별자
    TARGET_URL_1 = "https://www.ds-sec.co.kr/bbs/board.php?bo_table=sub03_02"
    TARGET_URL_2 = "https://www.ds-sec.co.kr/bbs/board.php?bo_table=sub03_03"
    
    requests.packages.urllib3.disable_warnings()
    
    TARGET_URL_TUPLE = (TARGET_URL_1, TARGET_URL_2)

    json_data_list = []

    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        logger.debug(f"DS Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")

        # HTML 요청 및 파싱
        try:
            response = requests.get(TARGET_URL, verify=False, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 게시글 목록 추출
            table = soup.select_one("#fboardlist > div > table")
            if not table:
                logger.warning(f"Table not found in {TARGET_URL}")
                continue

            rows = table.select("tbody tr")
            logger.info(f"DS Scraper: Found {len(rows)} rows in {firm_info.get_board_name()}")

            for row in rows:
                # 제목과 URL 추출
                title_element = row.select_one(".bo_tit a")
                if not title_element:
                    continue  # 제목 요소가 없으면 건너뜁니다

                title = title_element.get_text(strip=True)
                article_url = title_element["href"]

                # wr_id 추출을 위한 정규식
                wr_id_match = re.search(r"wr_id=(\d+)", article_url)
                if wr_id_match:
                    wr_id = wr_id_match.group(1)
                    telegram_url = f"https://www.ds-sec.co.kr/bbs/download.php?bo_table=sub03_02&wr_id={wr_id}&no=0"
                else:
                    telegram_url = "없음"

                # 날짜와 조회수 추출
                date_element = row.select_one(".td_datetime")
                date_str = date_element.get_text(strip=True) if date_element else "날짜 정보 없음"

                # JSON 데이터 구성
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "ARTICLE_TITLE": title,
                    "ARTICLE_URL": article_url,
                    "TELEGRAM_URL": telegram_url,
                    "PDF_URL": telegram_url,
                    "REG_DT": re.sub(r"[-./]", "", date_str),
                    "SAVE_TIME": datetime.now().isoformat(),
                    "KEY": telegram_url if telegram_url != "없음" else article_url
                })
        except Exception as e:
            logger.error(f"Error scraping {TARGET_URL}: {e}")

        # 메모리 정리
        gc.collect()

    return json_data_list
