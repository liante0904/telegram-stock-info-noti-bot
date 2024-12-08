import os
import gc
import aiohttp
import json
import re
import asyncio
import sys
from datetime import datetime
from aiohttp import ClientSession

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo


async def fetch_data(session: ClientSession, url: str, headers: dict, data: dict, cookies: dict) -> dict:
    try:
        async with session.post(url, headers=headers, data=data, cookies=cookies, timeout=10) as response:
            response_text = await response.text()
            return json.loads(response_text)
    except Exception as e:
        print(f"Error during request to {url}: {e}")
        return {}


async def process_board_order(session: ClientSession, sec_firm_order: int, article_board_order: int, target_url: str, cms_cd: str, headers: dict, cookies: dict):
    firm_info = FirmInfo(
        sec_firm_order=sec_firm_order,
        article_board_order=article_board_order
    )
    data = {
        "pageNum": "1",
        "src": "all",
        "cmsCd": cms_cd,
        "rowNum": "10",
        "startRow": "0",
        "sdt": "",
        "edt": ""
    }

    response = await fetch_data(session, target_url, headers, data, cookies)
    if not response:
        return []

    soup_list = response[0].get('getNoticeList', [])
    json_data_list = []

    for list_item in soup_list:
        REG_DT = re.sub(r"[-./]", "", list_item['REGDT'])
        LIST_ARTICLE_URL = f"https://www.sangsanginib.com/_upload/attFile/{cms_cd}/{cms_cd}_{list_item['NT_NO']}_1.pdf"
        LIST_ARTICLE_TITLE = list_item['TITLE']
        json_data_list.append({
            "SEC_FIRM_ORDER": sec_firm_order,
            "ARTICLE_BOARD_ORDER": article_board_order,
            "FIRM_NM": firm_info.get_firm_name(),
            "REG_DT": REG_DT,
            "ATTACH_URL": LIST_ARTICLE_URL,
            "DOWNLOAD_URL": LIST_ARTICLE_URL,
            "KEY": LIST_ARTICLE_URL,
            "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
            "SAVE_TIME": datetime.now().isoformat()
        })

    return json_data_list


async def Sangsanginib_checkNewArticle():
    SEC_FIRM_ORDER = 6
    TARGET_URL = "https://www.sangsanginib.com/notice/getNoticeList"
    cmsCd_list = ["CM0078", "CM0338", "CM0079"]

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.sangsanginib.com",
        "Referer": "https://www.sangsanginib.com",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }

    cookies = {
        "SSISTOCK_JSESSIONID": "F63EB7BB0166E9ECA5988FF541287E07",
        "_ga": "GA1.1.467249692.1728208332",
        "_ga_BTXL5GSB67": "GS1.1.1728208331.1.1.1728208338.53.0.0"
    }

    async with aiohttp.ClientSession() as session:
        tasks = [
            process_board_order(session, SEC_FIRM_ORDER, idx, TARGET_URL, cms_cd, headers, cookies)
            for idx, cms_cd in enumerate(cmsCd_list)
        ]

        results = await asyncio.gather(*tasks)
        # Flatten the results
        json_data_list = [item for sublist in results for item in sublist]

        # 메모리 정리
        gc.collect()

    return json_data_list


# 비동기 함수 실행
async def main():
    result = await Sangsanginib_checkNewArticle()
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
