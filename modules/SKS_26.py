# -*- coding:utf-8 -*-
import os
import gc
import requests
from datetime import datetime
import sys
from dotenv import load_dotenv

# 내부 공용 모듈 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper



def Sks_checkNewArticle():
    SEC_FIRM_ORDER = 26   # SK증권 (원하시는 번호로)
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()
    
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

    load_dotenv(dotenv_path=dotenv_path)
    
    TARGET_URL = os.getenv('SKS_URL')

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )

    scraper = SyncWebScraper(TARGET_URL, firm_info)

    # ⚙️ POST 요청 파라미터 (검색어 없음, 1페이지)
    payload = {
        "searchVal": "",
        "searchType": "",
        "page": 1,
        "rowPerPage": 2000,
        "_r_": "0.999"
    }

    # 🔹 JSON 응답 받기
    jres = scraper.PostJson(params=payload)
    soupList = jres.get('list', [])

    for item in soupList:
        # print(item)
        # return 
        # PDF 파일명 예: "20251020073057027_0_ko.pdf"
        pdfpath = item.get("PDFPATH", "").strip()
        subject = item.get("RSUBJECT", "").strip()
        writer = item.get("RESECHNM", "").strip()
        ARTICLE_BOARD_ORDER = int(item.get("CATEGYID", "").strip())
        CATEGYID_NAME = item.get("CATEGYID_NAME", "").strip()
        reg_date = item.get("CURNDATE", "").strip().replace('.', '')
        print(f"ARTICLE_BOARD_ORDER: {ARTICLE_BOARD_ORDER}, CATEGYID_NAME: {CATEGYID_NAME}")
        # 🔗 PDF 다운로드 URL
        # https://www.sks.co.kr/data1/research/qna_file/{pdfpath}
        download_url = f"https://www.sks.co.kr/data1/research/qna_file/{pdfpath}"

        # 📰 뷰어 URL (pdf 바로보기용, 동일하게 사용)
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
            "KEY": download_url,
            "WRITER": writer,
            "SAVE_TIME": datetime.now().isoformat()
        })

    del soupList
    gc.collect()

    return json_data_list


def main():
    result = Sks_checkNewArticle()
    # print(result)


if __name__ == '__main__':
    main()