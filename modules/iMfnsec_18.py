import asyncio
import aiohttp
import json
import re
from datetime import datetime
import base64
import time
import os
import sys
import random
import hashlib
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config

# 기본 URL과 공통 헤더 설정
BASE_URL = config.get_urls("iMfnsec_18")[0]
HEADERS_TEMPLATE = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}

# 전역 변수로 시큐어 키를 한 번만 생성하고 저장
SECURE_KEY = None

# 시큐어 키 생성 함수 (비동기, 한 번만 생성하여 재사용)
async def generate_secure_key(session, bid):
    global SECURE_KEY
    if SECURE_KEY:
        return SECURE_KEY

    SECURE_KEY = base64.b64encode(f"sJS{int(time.time() * 1000)}".encode()).decode()
    try:
        async with session.post(
            f"{BASE_URL}/inc/common/PrivateSecuerKey.jsp",
            headers={
                **HEADERS_TEMPLATE,
                "Referer": f"{BASE_URL}/mobile/invest/invest02.jsp?bid={bid}&isSmartHi=N"
            },
            data={"_secureKey": SECURE_KEY}
        ) as response:
            if response.status == 200:
                logger.debug("Secure Key generated successfully.")
            else:
                logger.error(f"Failed to set Secure Key. Status: {response.status}")
    except Exception as e:
        logger.error(f"Error generating secure key: {e}")
        
    return SECURE_KEY

# 쿠키 생성 함수 (비동기)
async def generate_cookie():
    session_id = hashlib.md5(f"session{random.randint(1000, 9999)}{time.time()}".encode()).hexdigest()
    acefcid = f"UID-{hashlib.md5(str(random.randint(0, 1000000)).encode()).hexdigest()}"
    return f"JSESSIONID={session_id}; ACEFCID={acefcid}; ACEUACS=undefined;"

# 첨부 파일 URL 가져오는 함수 (비동기)
async def fetch_attach_url(session, bid, aid):
    secure_key = await generate_secure_key(session, bid)
    params = {
        "bid": bid,
        "aid": aid,
        "tr_cd": "db/research/twbbacl_attach",
        "secureKey": secure_key
    }
    try:
        async with session.post(
            f"{BASE_URL}/_json/source.jsp",
            headers={**HEADERS_TEMPLATE, "Origin": BASE_URL},
            data=params
        ) as response:
            if response.status == 200:
                try:
                    res_text = await response.text()
                    jres = json.loads(res_text)[0][0]
                    url = f"https://www.imfnsec.com/upload/{jres['file_dir']}/{jres['file_name']}"
                    return url
                except (json.JSONDecodeError, IndexError):
                    logger.error("Error decoding JSON or accessing response data for attach URL.")
                    return None
            else:
                logger.warning(f"Failed to retrieve attach URL. Status Code: {response.status}")
    except Exception as e:
        logger.error(f"Error fetching attach URL: {e}")
    return None

# IM증권 기사 체크 함수
async def iMfnsec_checkNewArticle(cur_page="1", single_page_only=True):
    SEC_FIRM_ORDER = 18
    bids = ["R_E08", "R_E09", "R_E14", "R_E03", "R_E04", "R_E05"]
    json_data_list = []

    async with aiohttp.ClientSession() as session:
        cookie = await generate_cookie()
        for ARTICLE_BOARD_ORDER, bid in enumerate(bids):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            logger.debug(f"IMfnsec Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER} (bid: {bid})")
            
            secure_key = await generate_secure_key(session, bid)
            if not secure_key:
                continue

            headers = {
                **HEADERS_TEMPLATE,
                "Referer": f"{BASE_URL}/mobile/invest/invest02.jsp?bid={bid}&isSmartHi=N",
                "Cookie": cookie,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest"
            }

            page = int(cur_page)
            while True:
                data = {
                    "tr_cd": "db/board/TWBBACL/board_list",
                    "bid": bid,
                    "cur_page": str(page),
                    "num_page": "100",
                    "secureKey": secure_key
                }

                try:
                    async with session.post(f"{BASE_URL}/_json/source.jsp", headers=headers, data=data) as response:
                        if response.status == 200:
                            res_text = await response.text(encoding='utf-8', errors='ignore')
                            jres = json.loads(res_text)[0]
                            if not jres:
                                break
                            
                            logger.info(f"IMfnsec Scraper: Found {len(jres)} articles for bid {bid} page {page}")

                            for item in jres:
                                try:
                                    attach_url = await fetch_attach_url(session, item['bid'], item['aid'])
                                    json_data_list.append({
                                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                                        "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                                        "FIRM_NM": firm_info.get_firm_name(),
                                        "REG_DT": re.sub(r"[-./]", "", item['reg_dt']),
                                        "ARTICLE_URL": BASE_URL,
                                        "ATTACH_URL": attach_url,
                                        "DOWNLOAD_URL": attach_url,
                                        "TELEGRAM_URL": attach_url,
                                        "PDF_URL": attach_url,
                                        "ARTICLE_TITLE": item['title'],
                                        "WRITER": item['username'],
                                        "KEY": attach_url,
                                        "SAVE_TIME": datetime.now().isoformat()
                                    })
                                except KeyError as e:
                                    logger.error(f"KeyError encountered: {e} for item in bid {bid}, page {page}.")

                            if single_page_only:
                                break
                            page += 1
                        else:
                            logger.warning(f"Failed to fetch page data for bid {bid}. Status code: {response.status}")
                            break
                except Exception as e:
                    logger.error(f"Error during IMfnsec scraping: {e}")
                    break

    return json_data_list

# main 함수
async def main():
    results = await iMfnsec_checkNewArticle(single_page_only=True)
    logger.info(f"Total IMfnsec articles fetched: {len(results)}")

if __name__ == "__main__":
    asyncio.run(main())
