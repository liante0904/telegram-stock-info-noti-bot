import asyncio
import aiohttp
import gc
import re
from datetime import datetime
from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

async def fetch(session, url):
    """비동기로 HTTP 요청을 보내는 함수"""
    async with session.get(url) as response:
        return await response.text()

async def fetch_all_pages_meritz(session, base_url, sec_firm_order, article_board_order, max_pages=None):
    """메리츠증권 모든 페이지 데이터를 순회하며 가져오는 함수"""
    json_data_list = []
    page = 1

    while True:
        if max_pages and page > max_pages:  # 최대 페이지를 초과하면 종료
            break

        target_url = base_url.replace("pageNum=1", f"pageNum={page}")
        print(f"Fetching: {target_url}")

        try:
            html_content = await fetch(session, target_url)
        except Exception as e:
            print(f"Error fetching URL {target_url}: {e}")
            break

        # HTML parse
        soup = BeautifulSoup(html_content, "html.parser")
        soupListHead = soup.select('table > thead > tr > th')  # 메리츠증권 리스트 헤더
        soupList = soup.select('table > tbody > tr')  # 메리츠증권 리스트 아이템 선택자
        print(f"Page {page}: Found {len(soupList)} articles")  # Progress 출력

        if not soupList:  # 더 이상 데이터가 없으면 종료
            break
            
        # 헤더 매핑 생성: 헤더 이름 -> 열 번호
        header_map = {th.get_text().strip(): idx for idx, th in enumerate(soupListHead)}
        
        for list_item in soupList:
            try:

                link_tag = list_item.select_one(f'td:nth-child({header_map["제목"] + 1}) a')


                LIST_ARTICLE_TITLE = link_tag.get_text().strip() if link_tag else "N/A"
                LIST_ARTICLE_URL = "https://home.imeritz.com" + link_tag['href']
                
                # 작성일시
                # '작성일' 또는 '작성일시'를 처리
                date_column = "작성일" if "작성일" in header_map else "작성일시"
                REG_DT = list_item.select_one(f'td:nth-child({header_map[date_column] + 1})').get_text().strip()
                REG_DT = re.sub(r"[-./]", "", REG_DT)  # 날짜 포맷 정리
                
                # 작성자
                date_column = "작성자" if "작성자" in header_map else "작성자명"
                WRITER = list_item.select_one(f'td:nth-child({header_map[date_column] + 1})').get_text().strip()
                
                # 카테고리 (선택적으로 사용 가능)
                CATEGORY = list_item.select_one(f'td:nth-child({header_map["분류"] + 1})').get_text().strip() if "분류" in header_map else ""

                # LIST_ARTICLE_URL로 접속하여 DOWNLOAD_URL, TELEGRAM_URL 생성
                try:
                    article_html = await fetch(session, LIST_ARTICLE_URL)
                    article_soup = BeautifulSoup(article_html, "html.parser")

                    # 첨부 파일 태그 찾기: title 속성만 사용
                    download_tag = article_soup.select_one('a[title]')  # title 속성을 가진 <a> 태그 찾기

                    if download_tag and 'title' in download_tag.attrs:
                        # title 속성에서 파일 이름 추출
                        file_name = download_tag['title']
                        file_name = file_name.replace(" 파일 다운로드", "").strip()  # 필요 없는 텍스트 제거
                        DOWNLOAD_URL = f"https://home.imeritz.com/include/resource/research/WorkFlow/{file_name}"
                        TELEGRAM_URL = DOWNLOAD_URL
                        # print(f"Constructed DOWNLOAD_URL: {DOWNLOAD_URL}")
                    else:
                        print("No 'title' attribute found in download tag.")
                        DOWNLOAD_URL = TELEGRAM_URL = LIST_ARTICLE_URL  # 기본 URL로 설정

                except Exception as e:
                    print(f"Error fetching DOWNLOAD_URL from {LIST_ARTICLE_URL}: {e}")
                    DOWNLOAD_URL = TELEGRAM_URL = LIST_ARTICLE_URL

                # JSON 데이터 생성
                article_data = {
                    "SEC_FIRM_ORDER": sec_firm_order,
                    "ARTICLE_BOARD_ORDER": article_board_order,
                    "FIRM_NM": FirmInfo(sec_firm_order, article_board_order).get_firm_name(),
                    "REG_DT": REG_DT,
                    "ARTICLE_URL": LIST_ARTICLE_URL,
                    "ATTACH_URL": LIST_ARTICLE_URL,
                    "DOWNLOAD_URL": DOWNLOAD_URL,
                    "TELEGRAM_URL": TELEGRAM_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "CATEGORY": CATEGORY,
                    "KEY:": TELEGRAM_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                }
                json_data_list.append(article_data)
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        page += 1  # 다음 페이지로 이동

    return json_data_list


async def MERITZ_checkNewArticle(full_fetch=False):
    """메리츠증권 데이터 수집"""
    SEC_FIRM_ORDER = 20

    TARGET_URL_TUPLE = [
        # 메리츠증권 투자전략
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=sih02nw&listCnt=50&pageNum=1&searchDiv=&searchText=',
        # 메리츠증권 산업분석
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=invest03nw&listCnt=50&pageNum=1&searchDiv=&searchText=',
        # 메리츠증권 기업분석
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=invest02nw&listCnt=50&pageNum=1&searchDiv=&searchText=',
        # 메리츠증권 주요 지표 및 뉴스
        'https://home.imeritz.com/bbs/BbsList.go?bbsGrpId=bascGrp&bbsId=pricenewsrs&listCnt=50&pageNum=1&searchDiv=&searchText='
    ]

    # full_fetch가 False이면 최대 3페이지까지만 조회
    max_pages = None if full_fetch else 3

    all_results = []
    async with aiohttp.ClientSession() as session:
        for article_board_order, base_url in enumerate(TARGET_URL_TUPLE):
            print(f"Processing board {article_board_order + 1}/{len(TARGET_URL_TUPLE)}: {base_url}")
            results = await fetch_all_pages_meritz(session, base_url, SEC_FIRM_ORDER, article_board_order, max_pages)
            all_results.extend(results)

    # 메모리 정리
    gc.collect()
    return all_results


async def main():
    # 메리츠증권 데이터 수집
    meritz_result = await MERITZ_checkNewArticle(full_fetch=True)
    print(f"Fetched {len(meritz_result)} articles from Meritz.")
    print(meritz_result)

    db = SQLiteManager()
    inserted_count_meritz = db.insert_json_data_list(meritz_result, 'data_main_daily_send')

    print(f"Meritz Articles Inserted: {inserted_count_meritz}")


if __name__ == "__main__":
    asyncio.run(main())
