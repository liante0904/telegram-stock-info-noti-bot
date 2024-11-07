# -*- coding:utf-8 -*-
import os
import gc
import logging
import requests
import json
import re
import urllib.parse as urlparse
import urllib.request
import asyncio
import aiohttp
from datetime import datetime, timedelta, date
import time

from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper
from utils.date_util import GetCurrentDate

def LS_checkNewArticle():
    json_data_list = []
    SEC_FIRM_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = [
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=146',  # 이슈브리프
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=36',   # 기업분석 게시판
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=37',   # 산업분석
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=38',   # 투자전략
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=147',  # Quant
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=39',   # Macro
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=183',  # FI/Credit
        'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=145'   # Commodity
    ]

    for ARTICLE_BOARD_ORDER, base_url in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        # 페이지 번호 설정
        page = 1
        while True:
            # 페이지 URL에 `currPage` 파라미터 추가
            TARGET_URL = f"{base_url}&currPage={page}"
            scraper = SyncWebScraper(TARGET_URL, firm_info)
            soup = scraper.Get()
            
            # '등록된 데이터가 없습니다.' 메시지가 있는지 확인
            if soup.select_one(".no_data") and "등록된 데이터가 없습니다." in soup.select_one(".no_data").text:
                print(f"{TARGET_URL}: 등록된 데이터가 없으므로 종료합니다.")
                break

            soupList = soup.select('#contents > table > tbody > tr')

            # 현재 날짜와 7일 전 날짜 계산
            today = date.today()
            seven_days_ago = today - timedelta(days=7)
            for item in soupList:
                print('=')
                str_txt = item.get_text()
                print(str_txt)
                print('=')
                if "등록된 데이터가 없습니다." in str_txt:
                    break
                
                str_date = item.select('td')[3].get_text().strip()
                post_date_obj = datetime.strptime(str_date, '%Y.%m.%d').date()
                
                # if post_date_obj < seven_days_ago:
                #     print(f"{TARGET_URL}: 게시물 날짜 {str_date}가 7일 이전이므로 스킵합니다.")
                #     continue

                link_element = item.select_one('a')
                LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + link_element['href'].replace("amp;", "")
                LIST_ARTICLE_TITLE = link_element.get_text().split(']')[1].strip() if ']' in link_element.get_text() else link_element.get_text()

                # # 상세 정보 가져오기
                # detail_data = LS_detail(LIST_ARTICLE_URL, str_date, firm_info)
                # if detail_data:
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": post_date_obj.strftime('%Y%m%d'),
                    "ARTICLE_URL": LIST_ARTICLE_URL,
                    "ATTACH_URL": '',
                    "DOWNLOAD_URL": '',
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            # print(json_data_list)
            # 다음 페이지로 이동
            page += 1
            print(f"{page}진행중...")
            time.sleep(0.5)  # 페이지 요청 간에 잠시 대기

        print(json_data_list)
    # 메모리 정리
    gc.collect()
    return json_data_list

def LS_detail(TARGET_URL, str_date, firm_info):
    TARGET_URL = TARGET_URL.replace('&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1', '')
    item = {}  # 빈 딕셔너리로 초기화
    time.sleep(0.1)

    scraper = SyncWebScraper(TARGET_URL, firm_info)
    soup = scraper.Get()

    # 게시글 제목
    trs = soup.select('tr')
    item['LIST_ARTICLE_TITLE'] = trs[0].select_one('td').text

    # 첨부파일 이름
    attach_element = soup.select_one('.attach > a')
    if attach_element:
        ATTACH_FILE_NAME = attach_element.get_text()
        
        URL_PARAM = str_date.split('.')
        URL_PARAM_0 = 'B' + URL_PARAM[0] + URL_PARAM[1]
        URL_PARAM_1 = urllib.parse.unquote(ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%'))
        
        ATTACH_URL = f'https://www.ls-sec.co.kr/upload/EtwBoardData/{URL_PARAM_0}/{URL_PARAM_1}'
        item['LIST_ARTICLE_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')
    else:
        print(f"{TARGET_URL}: 첨부파일이 없습니다.")
        return None

    return item

def main():
    LS_checkNewArticle()
if __name__ == "__main__":
    main()