# -*- coding:utf-8 -*- 
import os
import gc
import requests
import time
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo

def HANA_checkNewArticle():
    SEC_FIRM_ORDER      = 3
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = [
        # 하나금융 Daily
        'https://www.hanaw.com/main/research/research/list.cmd?pid=4&cid=1',
        # 하나금융 산업 분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=1',
        # 하나금융 기업 분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=2',
        # 하나금융 주식 전략
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=1',
        # 하나금융 Small Cap
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=3',
        # 하나금융 기업 메모
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=4',
        # 하나금융 Quant
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=2',
        # 하나금융 포트폴리오
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=3',
        # 하나금융 투자정보
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=4',
        # 글로벌 투자전략
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=1',
        # 글로벌 산업분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=2',
        # 글로벌 기업분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=3'
    ]

    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        try:
            response = requests.get(TARGET_URL, verify=False)
            time.sleep(0.5)
        except:
            return 0

        # HTML parse
        soup = BeautifulSoup(response.content, "html.parser")
        soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

        #container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li > div.con > ul > li.mb7.m-info.info > span:nth-child(3)
        for list in soupList:
            LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').get_text()
            LIST_ARTICLE_URL =  'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
            REG_DT = list.select_one('div.con > ul > li.mb7.m-info.info > span:nth-child(3)').get_text()
            REG_DT = re.sub(r"[-./]", "", REG_DT)
            WRITER = list.select_one('div.con > ul > li.mb7.m-info.info > span.none.m-name').get_text()
            time_str = list.select_one('div.con > ul > li.mb7.m-info.info > span.hide-on-mobile.txtbasic.r-side-bar').get_text()
            
            # 날짜 조정
            # adjusted_date = adjust_date(REG_DT, time_str)
            
            # print(f"Original: {REG_DT}, Adjusted: {adjusted_date}, Time: {time_str}")
            
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":adjust_date(REG_DT, time_str),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": LIST_ARTICLE_URL,
                "TELEGRAM_URL": LIST_ARTICLE_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "WRITER":WRITER,
                "KEY:": LIST_ARTICLE_URL,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
                
    # 메모리 정리
    del soup
    del response
    gc.collect()
    return json_data_list


def adjust_date(REG_DT, time_str):
    # REG_DT를 datetime 객체로 변환
    reg_date = datetime.strptime(REG_DT, "%Y%m%d")
    
    # time_str에서 시간 추출 (예: "오후 3:31:33" 또는 "오후 3:31")
    time_str = time_str.strip()  # 앞뒤 공백 제거
    match = re.match(r"(오전|오후)\s*(\d{1,2}):(\d{2})(?::(\d{2}))?", time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    period, hour, minute, second = match.groups()
    hour = int(hour)
    minute = int(minute)
    second = int(second) if second else 0  # 초가 없으면 0으로 처리
    
    # 오후 처리
    if period == "오후" and hour != 12:
        hour += 12
    elif period == "오전" and hour == 12:  # 오전 12시는 자정
        hour = 0

    # 해당 시간을 datetime 객체로 설정
    current_time = reg_date + timedelta(hours=hour, minutes=minute, seconds=second)

    # 로직 적용
    if current_time.hour >= 10:  # 오전 10시 이후
        reg_date += timedelta(days=1)

    # 주말 처리 (토요일: 5, 일요일: 6)
    while reg_date.weekday() >= 5:  # 주말이면
        reg_date += timedelta(days=1)

    return reg_date.strftime("%Y%m%d")  # 다시 문자열로 변환
