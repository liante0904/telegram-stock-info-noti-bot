import os
import gc
import aiohttp
import json
import asyncio
from datetime import datetime

# IBK 투자증권 리서치 URL 및 공통 헤더
URLS = {
    "전략/시황": "https://m.ibks.com/iko/IKO010101/getInvReportList.do",
    "기업분석": "https://m.ibks.com/iko/IKO010201/getBusReportList.do",
    "산업분석": "https://m.ibks.com/iko/IKO010301/getIndReportList.do",
    "경제/채권": "https://m.ibks.com/iko/IKO010401/getCommentList.do",
    "해외리서치": "https://m.ibks.com/iko/IKO010501/getReportList.do"
}

# 공통 헤더
headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json; charset=UTF-8",
    "Origin": "https://m.ibks.com",
    "Referer": "https://m.ibks.com/iko/IKO010101.do",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

async def fetch_data(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict) -> dict:
    try:
        async with session.post(url, headers=headers, json=payload, timeout=10) as response:
            response_text = await response.text()
            return json.loads(response_text)
    except Exception as e:
        print(f"Error during request to {url}: {e}")
        return {}

async def process_reports(session: aiohttp.ClientSession, target_url: str, headers: dict):
    payload = {
        "screen": "IKO010101",  # 화면 코드, 필요에 따라 동적으로 수정 가능
        "data": {
            "start_row": 1,
            "end_row": 10,
            "row_size": 10,
            "pageNo": 1,
            "search_value": ""
        }
    }

    response = await fetch_data(session, target_url, headers, payload)
    if not response:
        return []

    report_list = response.get("data", {}).get("list", [])
    json_data_list = []

    for report in report_list:
        print(report)
        REG_DT = report.get('REG_ID', '')
        ATTACH_URL = f"https://m.ibks.com/iko/IKO010101/getFile.do?file_nm={report.get('ATTATCH1', '')}"
        ARTICLE_TITLE = report.get('REG_NAME', 'No Title')
        json_data_list.append({
            "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
            "FIRM_NM": firm_info.get_firm_name(),
            "REG_DT": re.sub(r"[-./]", "", list_item['makeDt']),
            "ATTACH_URL": LIST_ARTICLE_URL,
            "DOWNLOAD_URL": LIST_ARTICLE_URL,
            "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
            "WRITER": WRITER,
            "TELEGRAM_URL": LIST_ARTICLE_URL,
            "KEY": LIST_ARTICLE_URL,
            "SAVE_TIME": datetime.now().isoformat()
        })

    return json_data_list

async def IBK_checkNewReports():
    async with aiohttp.ClientSession() as session:
        # 모든 카테고리별로 데이터를 가져오는 작업
        all_results = {}
        for category, url in URLS.items():
            print(f"Fetching data for category: {category}")
            results = await process_reports(session, url, headers)
            all_results[category] = results
            gc.collect()  # 메모리 정리

    return all_results

# 비동기 함수 실행
async def main():
    result = await IBK_checkNewReports()
    print(result)
    # print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(main())
