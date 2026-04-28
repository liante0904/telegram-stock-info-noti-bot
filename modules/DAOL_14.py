from loguru import logger
import os
import gc
import aiohttp
import asyncio
import urllib.parse as urlparse
from datetime import datetime

from bs4 import BeautifulSoup
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config

async def fetch_article(session, TARGET_URL, form_data, headers):
    async with session.post(TARGET_URL, data=form_data, headers=headers) as response:
        return await response.text()

async def DAOL_checkNewArticle():
    sec_firm_order = 14
    article_board_order = 0
    json_data_list = []

    TARGET_URL_TUPLE = config.get_urls("DAOL_14")

    # 세션 생성
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        for article_board_order, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(
                sec_firm_order=sec_firm_order,
                article_board_order=article_board_order
            )
            # URL 파싱 및 수정
            parsed_url = urlparse.urlparse(TARGET_URL)
            query_params = urlparse.parse_qs(parsed_url.query)
            BASE_URL = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            TARGET_URL = BASE_URL + '?cmd=list&templet-bypass=true'

            # 헤더 설정
            headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Host': 'www.daolsecurities.com',
                'Origin': 'https://www.daolsecurities.com',
                'Referer': BASE_URL,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # 현재 날짜
            now = datetime.now()

            # 연초 값 설정
            start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

            # form data 설정
            form_data = {
                'curPage': '1',
                'bbSeq': '',
                'rGubun': query_params.get('rGubun'),
                'sctrGubun': query_params.get('sctrGubun'),
                'web': query_params.get('web'),
                'hts': '',
                'filepath': '',
                'attaFileNm': '',
                'startDate': start_of_year.strftime("%Y/%m/%d"),
                'endDate': datetime.now().strftime("%Y%m%d"),
                'searchSelect': '0',
                'searchNm1': '',
                'searchNm2': query_params.get('rGubun')
            }

            # 비동기 요청 추가
            task = fetch_article(session, TARGET_URL, form_data, headers)
            tasks.append(task)

        # 모든 요청 처리
        responses = await asyncio.gather(*tasks)

        for response in responses:
            soup = BeautifulSoup(response, "html.parser")
            soupList = soup.select('tr')

            nNewArticleCnt = 0

            for list in soupList:
                cells = list.select('td')
                if len(cells) < 3:
                    continue  # 필요한 데이터가 없는 경우 무시

                # reg_dt 추출 및 변환
                reg_date = cells[0].get_text(strip=True)
                reg_dt = reg_date.replace('/', '')  # YYYYMMDD 형식으로 변환

                # 작성자 정보
                writer = cells[4].get_text(strip=True)

                # article_title 및 article_url 추출
                article_link = cells[1].select_one('a.del_w')
                if not article_link:
                    continue  # 링크가 없는 경우 무시

                LIST_ARTICLE_TITLE = article_link['title']
                if "Coverage 제외" in LIST_ARTICLE_TITLE:
                    logger.warning("Coverage 제외는 발송 제외")
                    continue

                LIST_ARTICLE_URL = article_link['href']

                # URL 분할
                parts = LIST_ARTICLE_URL.split(',')
                if len(parts) != 3:
                    logger.debug("잘못된 입력 형식입니다.")
                    continue

                path = parts[0].split("'")[1]
                filename = parts[1].split("'")[1]
                research_id = parts[2].split(")")[0]

                LIST_ARTICLE_URL = f"https://www.ktb.co.kr/common/download.jspx?cmd=viewPDF&path={path}/{filename}"
                download_url = LIST_ARTICLE_URL

                json_data_list.append({
                    "sec_firm_order": sec_firm_order,
                    "article_board_order": article_board_order,
                    "firm_nm": firm_info.get_firm_name(),
                    "reg_dt": reg_dt,
                    "download_url": LIST_ARTICLE_URL,
                    "telegram_url": LIST_ARTICLE_URL,
                    "key": LIST_ARTICLE_URL,
                    "article_title": LIST_ARTICLE_TITLE,
                    "writer": writer,
                    "save_time": datetime.now().isoformat()
                })

        # 메모리 정리
        gc.collect()

    return json_data_list


# 비동기 함수 실행
if __name__ == "__main__":
    asyncio.run(DAOL_checkNewArticle())  # 비동기 함수 실행