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


async def Sangsanginib_checkNewArticle():
    SEC_FIRM_ORDER = 6
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []
    
    TARGET_URL_0 = "https://www.sangsanginib.com/notice/getNoticeList"
    TARGET_URL_1 = TARGET_URL_0
    TARGET_URL_2 = TARGET_URL_0
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.sangsanginib.com",
        "Referer": "https://www.sangsanginib.com",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }

    cmsCd = ["CM0078", "CM0338", "CM0079"]
    cookies = {
        "SSISTOCK_JSESSIONID": "F63EB7BB0166E9ECA5988FF541287E07",
        "_ga": "GA1.1.467249692.1728208332",
        "_ga_BTXL5GSB67": "GS1.1.1728208331.1.1.1728208338.53.0.0"
    }

    async with aiohttp.ClientSession() as session:
        tasks = []
        for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )

            data = {
                "pageNum": "1",
                "src": "all",
                "cmsCd": cmsCd[ARTICLE_BOARD_ORDER],
                "rowNum": "10",
                "startRow": "0",
                "sdt": "",
                "edt": ""
            }

            # 비동기적으로 데이터를 가져오기 위한 작업 추가
            tasks.append(fetch_data(session, TARGET_URL, headers, data, cookies))

        # 비동기적으로 모든 요청을 완료
        responses = await asyncio.gather(*tasks)

        for response in responses:
            if response:
                soupList = response[0].get('getNoticeList', [])
                
                for list_item in soupList:
                    REG_DT = re.sub(r"[-./]", "", list_item['REGDT'])
                    LIST_ARTICLE_URL = f"https://www.sangsanginib.com/_upload/attFile/{cmsCd[ARTICLE_BOARD_ORDER]}/{cmsCd[ARTICLE_BOARD_ORDER]}_{list_item['NT_NO']}_1.pdf"
                    LIST_ARTICLE_TITLE = list_item['TITLE']
                    
                    json_data_list.append({
                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                        "FIRM_NM": firm_info.get_firm_name(),
                        "REG_DT": REG_DT,
                        "ATTACH_URL": LIST_ARTICLE_URL,
                        "DOWNLOAD_URL": LIST_ARTICLE_URL,
                        "KEY": LIST_ARTICLE_URL,
                        "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                        "SAVE_TIME": datetime.now().isoformat()
                    })

        # 메모리 정리
        gc.collect()

    return json_data_list


# 비동기 함수 실행
async def main():
    result = await Sangsanginib_checkNewArticle()
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
