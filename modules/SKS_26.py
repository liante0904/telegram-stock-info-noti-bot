# -*- coding:utf-8 -*-
import os
import gc
import requests
from datetime import datetime
import sys
from dotenv import load_dotenv
from loguru import logger

# 내부 공용 모듈 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper
from models.SQLiteManager import SQLiteManager


def Sks_checkNewArticle():
    SEC_FIRM_ORDER = 26   # SK증권
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()
    
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
    TARGET_URL = os.getenv('SKS_URL')
    if not TARGET_URL:
        logger.error("SKS_URL not found in environment variables.")
        return []

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    logger.debug(f"SKS Scraper Start: {firm_info.get_firm_name()}")

    scraper = SyncWebScraper(TARGET_URL, firm_info)

    # ⚙️ POST 요청 파라미터
    payload = {
        "searchVal": "",
        "searchType": "",
        "page": 1,
        "rowPerPage": 2000,
        "_r_": "0.999"
    }

    # 🔹 JSON 응답 받기
    try:
        jres = scraper.GetJson(params=payload)
        if not jres:
            logger.warning(f"No response from {TARGET_URL}")
            return []
            
        soupList = jres.get('list', [])
        logger.info(f"SKS Scraper: Found {len(soupList)} articles")

        for item in soupList:
            pdfpath = item.get("PDFPATH", "").strip()
            subject = item.get("RSUBJECT", "").strip()
            writer = item.get("RESECHNM", "").strip()
            ARTICLE_BOARD_ORDER = int(item.get("CATEGYID", "0").strip() or 0)
            reg_date = item.get("CURNDATE", "").strip().replace('.', '')
            
            # 🔗 PDF 다운로드 URL
            download_url = f"https://www.sks.co.kr/data1/research/qna_file/{pdfpath}"
            article_url = download_url

            json_data_list.append({
                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                "FIRM_NM": firm_info.get_firm_name(),
                "ARTICLE_TITLE": subject,
                "REG_DT": reg_date,
                "ATTACH_URL": article_url,
                "ARTICLE_URL": article_url,
                "DOWNLOAD_URL": download_url,
                "TELEGRAM_URL": article_url,
                "PDF_URL": article_url,
                "KEY": download_url,
                "WRITER": writer,
                "SAVE_TIME": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Error scraping SKS: {e}")

    gc.collect()
    return json_data_list


def main():
    result = Sks_checkNewArticle()
    if not result:
        logger.warning("No articles found.")
    else:
        db = SQLiteManager()
        inserted_count, updated_count = db.insert_json_data_list(result)
        logger.success(f"SKS: Inserted {inserted_count}, Updated {updated_count} articles.")

if __name__ == '__main__':
    main()
