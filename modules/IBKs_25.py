import os
import gc
import aiohttp
import json
import asyncio
import re
import sys
from datetime import datetime

# FirmInfo 등을 위해 path 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

SEC_FIRM_ORDER = 25

# IBK 투자증권 리서치 게시판 정보 (인덱스는 FirmInfo.py의 board_names[25] 순서와 일치해야 함)
# path: download.ibks.com/emsdata/tradeinfo/{path}/ 파일경로 매핑용
URL_INFO = [
    {"name": "전략/시황", "url": "https://m.ibks.com/iko/IKO010101/getInvReportList.do", "screen": "IKO010101", "path": "invreport"},
    {"name": "기업분석", "url": "https://m.ibks.com/iko/IKO010201/getBusReportList.do", "screen": "IKO010201", "path": "busreport"},
    {"name": "산업분석", "url": "https://m.ibks.com/iko/IKO010301/getIndReportList.do", "screen": "IKO010301", "path": "indreport"},
    {"name": "경제/채권", "url": "https://m.ibks.com/iko/IKO010401/getCommentList.do", "screen": "IKO010401", "path": "comment"},
    {"name": "해외기업분석", "url": "https://m.ibks.com/iko/IKO010501/getReportList.do", "screen": "IKO010501", "path": "overseasreport", "menu_tp": "0"},
    {"name": "글로벌ETF", "url": "https://m.ibks.com/iko/IKO010501/getReportList.do", "screen": "IKO010501", "path": "overseasreport", "menu_tp": "1"}
]

# 공통 헤더
BASE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json; charset=UTF-8",
    "Origin": "https://m.ibks.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

async def fetch_data(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict) -> dict:
    try:
        async with session.post(url, headers=headers, json=payload, timeout=15) as response:
            if response.status != 200:
                return {}
            response_text = await response.text()
            return json.loads(response_text)
    except Exception as e:
        print(f"Error during request to {url}: {e}")
        return {}

async def process_reports(session: aiohttp.ClientSession, info: dict, page: int, board_idx: int):
    category_name = info["name"]
    target_url = info["url"]
    screen_code = info["screen"]
    path_name = info["path"]

    firm_info = FirmInfo(sec_firm_order=SEC_FIRM_ORDER, article_board_order=board_idx)
    
    headers = BASE_HEADERS.copy()
    headers["Referer"] = f"https://m.ibks.com/iko/{screen_code}.do"

    row_size = 50 # 대량 수집 시 효율을 위해 50개씩 요청
    start_row = (page - 1) * row_size + 1
    end_row = page * row_size

    payload = {
        "screen": screen_code,
        "data": {
            "start_row": start_row,
            "end_row": end_row,
            "row_size": row_size,
            "pageNo": page,
            "search_value": ""
        }
    }

    # 해외리서치 세부 카테고리 처리
    if "menu_tp" in info:
        payload["data"]["menu_tp"] = info["menu_tp"]

    response = await fetch_data(session, target_url, headers, payload)
    if not response:
        return []

    report_list = response.get("data", {}).get("list", [])
    json_data_list = []

    for report in report_list:
        REG_DT = report.get('REG_DATE', '')
        REG_DT = re.sub(r"[-./]", "", REG_DT)
        
        # 파일명 추출 (ATTATCH1 필드 사용)
        file_name = report.get('ATTATCH1', '')
        
        # 리포트 타입(gubun) 설정
        if board_idx == 0:
            # '전략/시황' 게시판은 'invrespect' 사용
            gubun = 'invrespect'
        elif board_idx in [4, 5]:
            # 해외 리포트는 'GLOB' 사용
            gubun = 'GLOB'
        else:
            # 나머지 국내 리포트는 'DAIL' 사용
            gubun = 'DAIL'

        # gubun에 따라 path_name 설정
        if gubun == 'DAIL':
            path_name = 'invrespect'
        else:
            path_name = 'invreport'
        
        # menuCode는 각 게시판의 screen 코드를 사용
        menu_code = screen_code
        
        # attatchCd는 'ATTATCH1'로 고정된 것으로 보임
        # 실제 다운로드 URL 구성 (요청하신 download.ibks.com 기반 직링크)
        LIST_ARTICLE_URL = f"https://download.ibks.com/emsdata/tradeinfo/{path_name}/{file_name}"
        
        ARTICLE_TITLE = report.get('TITLE', 'No Title').strip()
        WRITER = report.get('REG_NAME', '').strip()
        
        market_type = 'GLOBAL' if category_name in ["해외기업분석", "글로벌ETF"] else 'KR'
        
        json_data_list.append({
            "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER": board_idx,
            "FIRM_NM": firm_info.get_firm_name(),
            "REG_DT": REG_DT,
            "ATTACH_URL": LIST_ARTICLE_URL,
            "DOWNLOAD_URL": LIST_ARTICLE_URL,
            "ARTICLE_TITLE": ARTICLE_TITLE,
            "WRITER": WRITER,
            "TELEGRAM_URL": LIST_ARTICLE_URL,
            "KEY": LIST_ARTICLE_URL,
            "MKT_TP": market_type,
            "SAVE_TIME": datetime.now().isoformat()
        })

    return json_data_list

async def IBK_checkNewArticle(page=1, board_idx=None, full_fetch=False):
    """
    IBK투자증권 새 게시글 확인
    :param page: 조회할 페이지 번호 (full_fetch=False일 때 사용)
    :param board_idx: 특정 게시판만 조회할 경우 인덱스 (0~5)
    :param full_fetch: True인 경우 모든 페이지의 데이터를 순회하며 수집
    """
    async with aiohttp.ClientSession() as session:
        all_results = []
        
        for idx, info in enumerate(URL_INFO):
            # 특정 게시판만 요청받은 경우 필터링
            if board_idx is not None and idx != board_idx:
                continue

            if full_fetch:
                current_page = 1
                while True:
                    print(f"Fetching IBK reports for [{info['name']}] - Board Index {idx}, Page {current_page} (Full Fetch Mode)")
                    results = await process_reports(session, info, current_page, idx)
                    if not results:
                        break
                    all_results.extend(results)
                    current_page += 1
                    gc.collect()
            else:
                print(f"Fetching IBK reports for [{info['name']}] - Board Index {idx}, Page {page}")
                results = await process_reports(session, info, page, idx)
                all_results.extend(results)
                gc.collect()

    return all_results

async def main():
    board_idx = None
    full_fetch = False
    
    # 명령행 인자 처리 (예: python3 modules/IBKs_25.py 0)
    if len(sys.argv) > 1:
        try:
            board_idx = int(sys.argv[1])
            full_fetch = True
            print(f"--- Full Fetch Mode for Board Index {board_idx} ({URL_INFO[board_idx]['name']}) ---")
        except (ValueError, IndexError):
            print("Usage: python3 modules/IBKs_25.py [board_index(0-5)]")
            print("Example: python3 modules/IBKs_25.py 0 (Full fetch for '전략/시황')")
            return

    # 데이터 수집
    # 인자가 없으면 전체 게시판 1페이지씩만 수집 (기존 동작)
    result = await IBK_checkNewArticle(board_idx=board_idx, full_fetch=full_fetch)
    
    print(f"\nTotal articles fetched: {len(result)}")
    
    if result:
        # 인자가 있어서 full_fetch를 수행한 경우 DB에 즉시 저장
        if full_fetch:
            print(f"Inserting {len(result)} articles into database...")
            db = SQLiteManager()
            inserted, updated = db.insert_json_data_list(result, 'data_main_daily_send')
            print(f"Done: {inserted} inserted, {updated} updated.")
        else:
            # 테스트 모드일 때는 샘플만 출력
            print("\n--- Sample of fetched data (First record) ---")
            print(json.dumps(result[0], indent=4, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(main())
