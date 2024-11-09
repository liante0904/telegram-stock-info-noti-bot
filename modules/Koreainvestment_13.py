# -*- coding:utf-8 -*- 
import os
import gc
import logging
import requests
import time
import re
import urllib.parse as urlparse
import urllib.request
import asyncio
import aiohttp
from datetime import datetime, timedelta, date

from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager
from utils.date_util import GetCurrentDate

# selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



def Koreainvestment_selenium_checkNewArticle():
    SEC_FIRM_ORDER      = 13
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 한국투자증권 리서치 모바일
    TARGET_URL_0 =  "https://securities.koreainvestment.com/main/research/research/Search.jsp?schType=report"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")

        # Chrome 드라이버 초기화
        driver = webdriver.Chrome(options=chrome_options)

        # 웹 페이지 열기
        driver.get(TARGET_URL)

        # 페이지 로딩될때까지 대기
        driver.implicitly_wait(0)

        # 제목 엘리먼트 찾기
        title_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[1]/div[2]/span[1]')
        # 링크 엘리먼트 찾기
        link_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[2]')
        info_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[1]/span')
        
        nNewArticleCnt = 0
        # List
        for title, link, article_info in zip(title_elements, link_elements, info_elements):
            LIST_ARTICLE_TITLE = title.text
            LIST_ARTICLE_URL = link.get_attribute("onclick")
            article_info_str = article_info.text.split(' ')
            
            LIST_ARTICLE_URL = Koreainvestment_GET_LIST_ARTICLE_URL(LIST_ARTICLE_URL)
            DOWNLOAD_URL = LIST_ARTICLE_URL

            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", article_info_str[1]),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "WRITER": article_info_str[0],
                "SAVE_TIME": datetime.now().isoformat()
            })
            
            # https://file.truefriend.com/Storage/research/research05/20240726184612130_ko.pdf

        # # 링크와 제목 출력
        # for link_element in link_elements:
        #     title = link_element.text
        #     link = link_element.get_attribute("href")
        #     print("제목:", title)
        #     print("링크:", link)
        #     print()

        # 브라우저 닫기
        driver.quit()
        
    # 메모리 정리
    gc.collect()

    return json_data_list

def Koreainvestment_GET_LIST_ARTICLE_URL(string):
    string = string.replace("javascript:prePdfFileView2(", "").replace("&amp;", "&").replace(")", "").replace("(", "").replace("'", "")
    params = string.split(",")
    
    # 문자열에서 필요한 정보 추출
    category = "category1="+params[0].strip() +"&"+ "category2=" + params[1].strip()
    filename = params[2].strip()
    option = params[3].strip()
    datasubmitdate = params[4].strip()
    air_yn = params[5].strip()
    kor_yn = params[6].strip()
    special_yn = params[7].strip()

    # 함수 호출
    r = Koreainvestment_MAKE_LIST_ARTICLE_URL(category, filename, option, datasubmitdate, air_yn, kor_yn, special_yn)

    # 입력 URL을 파싱합니다.
    parsed_url = urlparse.urlparse(r)
    
    # 쿼리 파라미터를 파싱합니다.
    query_params = urlparse.parse_qs(parsed_url.query)
    
    # filepath와 filename 값을 가져옵니다.
    filepath = query_params.get('filepath', [''])[0]
    filename = query_params.get('filename', [''])[0]
    
    # 새로운 URL을 생성합니다.
    new_url = f"http://file.truefriend.com/Storage/{filepath}/{filename}"
    
    return new_url

def Koreainvestment_MAKE_LIST_ARTICLE_URL(filepath, filename, option, datasubmitdate, air_yn, kor_yn, special_yn):
    filename = urllib.parse.quote(filename)
    filepath = filepath
    
    # print('filepath =',filepath)
    host_name = "http://research.truefriend.com/streamdocs/openResearch"
    url = ""
    host_name2 = "https://kis-air.com/kor/"
    host_name3 = "https://kis-air.com/us/"

    if filepath.startswith("?") or filepath.startswith("&"):
        filepath = filepath[1:]

    params = filepath.split("&")
    # print('params',params)
    if len(params) == 2:
        if params == ['category1=01', 'category2=01'] or params == ['category1=01', 'category2=02'] or params == ['category1=01', 'category2=03'] or params == ['category1=01', 'category2=04'] or params == ['category1=01', 'category2=05']:
            filepath = "research/research01"
        elif params == ['category1=02', 'category2=01'] or params == ['category1=02', 'category2=02'] or params == ['category1=02', 'category2=03']:
            filepath = "research/research02"
        elif params == ['category1=03', 'category2=01'] or params == ['category1=03', 'category2=02'] or params == ['category1=03', 'category2=03']:
            filepath = "research/research03"
        elif params == ['category1=04', 'category2=00'] or params == ['category1=04', 'category2=01'] or params == ['category1=04', 'category2=02'] or params == ['category1=04', 'category2=03']:
            filepath = "research/research04"
        elif params[0] == 'category1=05' or params == ['category1=05']:
            filepath = "research/research05"
        elif params == ['category1=07', 'category2=01']:
            filepath = "research/research07"
        elif params == ['category1=08', 'category2=03'] or params == ['category1=08', 'category2=04'] or params == ['category1=08', 'category2=05']:
            filepath = "research/research08"
        elif params == ['category1=06', 'category2=02'] or params == ['category1=06', 'category2=01']:
            filepath = "research/research06"
        elif params == ['category1=09', 'category2=00']:
            filepath = "research/research11"
        elif params == ['category1=10', 'category2=01'] or params == ['category1=10', 'category2=04']:
            filepath = "research/research10"
        elif params == ['category1=10', 'category2=04']:
            filepath = "research/china"
        elif params == ['category1=01', 'category2=06']:
            filepath = "research/research12"
        elif params == ['category1=10', 'category2=06']:
            filepath = "research/research_emailcomment"
        elif params == ['category1=14', 'category2=01']:
            filepath = "research/research14"
        elif params == ['category1=13', 'category2=01']:
            filepath = "research/research11"
        elif params == ['category1=02', 'category2=04'] or params == ['category1=02', 'category2=12'] or params == ['category1=02', 'category2=06'] or params == ['category1=02', 'category2=13'] or params == ['category1=02', 'category2=08'] or params == ['category1=02', 'category2=09'] or params == ['category1=02', 'category2=10'] or params == ['category1=02', 'category2=11'] or params == ['category1=02', 'category2=14']:
            filepath = "research/research02"
        elif params == ['category1=15', 'category2=01']:
            filepath = "research/research01"
        elif params == ['category1=16', 'category2=01']:
            filepath = "research/research15"

    # print('filepath', filepath)
    if not option or option == None or option == "":
        option = "01"

    if kor_yn == 'Y' and air_yn == 'N' and special_yn == 'N' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name2}{datasubmitdate}/daily"
    elif kor_yn == 'Y' and air_yn == 'N' and special_yn == 'Y' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name2}{datasubmitdate}/special"
    elif kor_yn == 'N' and air_yn == 'N' and special_yn == 'N' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name3}{datasubmitdate}/daily"
    elif kor_yn == 'N' and air_yn == 'N' and special_yn == 'Y' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name3}{datasubmitdate}/special"
    else:
        url = f"{host_name}?filepath={urllib.parse.quote(filepath)}&filename={filename}&option={option}"

    # print(url)
    return url
