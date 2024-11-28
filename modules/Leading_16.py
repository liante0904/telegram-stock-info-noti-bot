# -*- coding:utf-8 -*- 
import re
import gc
import requests
from datetime import datetime

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper

def Leading_checkNewArticle():
    SEC_FIRM_ORDER      = 16
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 리딩투자증권 
    # TARGET_URL_0 =  "http://www.leading.co.kr/board/EquityResearch/list"
    
    TARGET_URL_0 = "http://www.leading.co.kr/board/EquityResearch/list?pageIndex=1&siteCd=&pageSize=10&pageUnit=100&sortColumnName=&sortDirection=&searchColumnName=SUBJECT&searchValue=&contentNo=&boardNo="
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        
        scraper = SyncWebScraper(TARGET_URL, firm_info)
        soup = scraper.Get()

        # soupListHead에서 헤더 추출
        soupListHead = soup.select('#sub-container > div.table-wrap > table > thead > tr')
        headers = [th.text.strip() for th in soupListHead[0].find_all('th')]  # 헤더 텍스트 추출
        print("헤더:", headers)

        # soupList에서 데이터 추출
        soupList = soup.select('#sub-container > div.table-wrap > table > tbody > tr')
        print('='*50)

        parsed_data = []  # 데이터를 저장할 리스트
        for row in soupList:
            columns = []  # 한 행의 데이터 저장
            for idx, td in enumerate(row.find_all('td')):
                header = headers[idx]  # 현재 열의 헤더 확인
                if header == '첨부':  # '첨부' 열일 경우
                    a_tag = td.find('a')  # a 태그 검색
                    columns.append(a_tag.attrs.get('href', '').strip() if a_tag else '')  # href 속성 가져오기
                else:
                    columns.append(td.get_text(strip=True))  # 기본 텍스트 가져오기

            if len(columns) < len(headers):  # 열 개수가 헤더 개수보다 적으면 스킵
                continue

            # zip을 사용하여 헤더와 데이터를 매칭
            row_data = dict(zip(headers, columns))
            parsed_data.append(row_data)
            
        soupList = parsed_data
        # soupList에서 게시물 정보 파싱
        for list in soupList:
            
            # 리서치 파일 첨부 링크 파싱
            attachment_link = "없음"
            if list['첨부']:
                attachment_link =  f"http://www.leading.co.kr{list['첨부']}"  # 상대 경로를 절대 경로로 변환
            
            # 결과 출력
            # print("제목:", title)
            # print("첨부 파일:", attachment_link)
            # print()
            LIST_ARTICLE_TITLE = list['제목']
            LIST_ARTICLE_URL = attachment_link
            DOWNLOAD_URL     = attachment_link
            REG_DT = list['작성일']
            REG_DT = re.sub(r"[-./]", "", REG_DT)  # 날짜 포맷 정리
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":REG_DT,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat(),
                "KEY": attachment_link
            })
            
            
    # 메모리 정리
    del soupList, list
    gc.collect()
    return json_data_list

if __name__ == "__main__":
    r = Leading_checkNewArticle()
    print(r)
