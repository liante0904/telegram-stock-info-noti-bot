# -*- coding:utf-8 -*-
import os
import gc
import requests
import re
from datetime import datetime, timedelta
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper
from models.SQLiteManager import SQLiteManager

# 게시판 설정
BOARD_CONFIG = [
    {"name": "한국 투자전략", "cd007": "RB30", "cd008": "RB30A"},
    {"name": "글로벌 투자전략", "cd007": "RB30", "cd008": "RB30B"},
    {"name": "경제분석",     "cd007": "RB30", "cd008": "RB30C"},
    {"name": "국내기업분석", "cd007": "RE01", "cd008": ""},
    {"name": "국내산업분석", "cd007": "RE02", "cd008": ""}
]

def Yuanta_research_common_checkNewArticle(cd007, cd008, board_name):
    SEC_FIRM_ORDER      = 26
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 최근 14일
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # URL
    TARGET_URL = (f"https://www.myasset.com/myasset/research/rs_list/rs_list.cmd"
                  f"?cd007={cd007}&cd008={cd008}"
                  f"&searchKeyGubun=1&startCalendar={start_date_str}"
                  f"&endCalendar={end_date_str}&pgCnt=100")

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    scraper = SyncWebScraper(TARGET_URL, firm_info)
    soup = scraper.Get()

    articles = soup.select("tr.js-moveRS")

    for article in articles:
        reg_dt = re.sub(r"[-./]", "", article.select_one("td:nth-child(1)").get_text(strip=True))

        title_elem = article.select_one("td:nth-child(2) a")
        article_title = title_elem.get_text(strip=True) if title_elem else "제목없음"

        attach_elem = article.select_one("td:nth-child(3) a[cmd-type=download]")
        download_url = (
            'https://file.myasset.com/sitemanager/upload/' + attach_elem['data-seq']
            if attach_elem and attach_elem.has_attr('data-seq')
            else "없음"
        )

        writer_elem = article.select_one("td:nth-child(5) a.js-link")
        writer = writer_elem.get_text(strip=True) if writer_elem else "정보없음"

        view_count = article.select_one("td:nth-child(6)").get_text(strip=True)

        json_data_list.append({
            "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
            "FIRM_NM": firm_info.get_firm_name(),
            "BOARD_NM": board_name,
            "REG_DT": reg_dt,
            "WRITER": writer,
            "DOWNLOAD_URL": download_url,
            "TELEGRAM_URL": download_url,
            "ARTICLE_TITLE": article_title,
            "VIEW_COUNT": view_count,
            "SAVE_TIME": datetime.now().isoformat(),
            "KEY": download_url
        })
        print(f"[{board_name}] {article_title} ({reg_dt})")

    del soup
    gc.collect()

    return json_data_list


if __name__ == "__main__":
    all_results = []
    for board in BOARD_CONFIG:
        print(f"=== {board['name']} 수집 중... ===")
        data = Yuanta_research_common_checkNewArticle(board["cd007"], board["cd008"], board["name"])
        all_results.extend(data)

    print(f"총 {len(all_results)}개 기사 수집 완료.")
    print(all_results)
    # DB 저장
    if all_results:
        db = SQLiteManager()
        # inserted_count = db.insert_json_data_list(all_results, 'data_main_daily_send')
        # print(f"총 {inserted_count}개 레코드 저장 완료.")
