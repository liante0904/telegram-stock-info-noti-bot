# -*- coding:utf-8 -*- 
import os
import requests
import re
import urllib.parse as urlparse
import urllib.request
import asyncio
from datetime import datetime
import time


# selenium
from selenium import webdriver
from selenium.webdriver.common.by import By

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo


async def Koreainvestment_selenium_checkNewArticle():
    SEC_FIRM_ORDER      = 13
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 한국투자증권 리서치 모바일
    TARGET_URL_0 =  "https://securities.koreainvestment.com/main/research/research/Search.jsp?schType=report"
    
    # 카테고리 리스트 (기본, 미국 현지 리서치)
    # 0: 전체보고서, 10: 미국 현지 리서치
    CATEGORIES = [
        {"name": "전체", "board_order": 0, "script": None, "mkt_tp": "KR"},
        {"name": "미국 현지 리서치", "board_order": 10, "script": "onTab1Selected('stifel', 1);", "mkt_tp": "GLOBAL"}
    ]

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        for idx, cat in enumerate(CATEGORIES):
            ARTICLE_BOARD_ORDER = cat["board_order"]
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )

            # 웹 페이지 열기
            driver.get(TARGET_URL_0)
            driver.implicitly_wait(5)

            # 자바스크립트 실행 (미국 현지 리서치인 경우)
            if cat["script"]:
                driver.execute_script(cat["script"])
                time.sleep(2) # AJAX 로딩 대기

            # 10페이지까지 반복 (페이지당 10건 x 10페이지 = 100건)
            for page in range(1, 11):
                if page > 1:
                    # 다음 페이지로 이동
                    driver.execute_script(f"goPage({page});")
                    time.sleep(2) # 페이지 로딩 대기

                # 현재 페이지 데이터 파싱
                title_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[1]/div[2]/span[1]')
                link_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[2]')
                info_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[1]/span')
                
                if not title_elements: # 데이터가 없으면 중단
                    break
                
                print(f"[{cat['name']}] Page {page} collected: {len(title_elements)} items")

                # List
                for title, link, article_info in zip(title_elements, link_elements, info_elements):
                    LIST_ARTICLE_TITLE = title.text
                    LIST_ARTICLE_URL_RAW = link.get_attribute("onclick")
                    article_info_str = article_info.text.split(' ')
                    
                    if len(article_info_str) < 2: continue

                    LIST_ARTICLE_URL = Koreainvestment_GET_LIST_ARTICLE_URL(LIST_ARTICLE_URL_RAW)
                    
                    json_data_list.append({
                        "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                        "FIRM_NM":firm_info.get_firm_name(),
                        "REG_DT":re.sub(r"[-./]", "", article_info_str[1]),
                        "ATTACH_URL":LIST_ARTICLE_URL,
                        "DOWNLOAD_URL": LIST_ARTICLE_URL,
                        "TELEGRAM_URL": LIST_ARTICLE_URL,
                        "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                        "WRITER": article_info_str[0],
                        "KEY": LIST_ARTICLE_URL,
                        "SAVE_TIME": datetime.now().isoformat(),
                        "MKT_TP": cat["mkt_tp"]
                    })
    finally:
        driver.quit()
        
    print(f"Total articles collected: {len(json_data_list)}")
    return json_data_list

def Koreainvestment_GET_LIST_ARTICLE_URL(string):
    if not string: return ""
    string = string.replace("javascript:prePdfFileView2(", "").replace("javascript:prePdfFileView3(", "").replace("&amp;", "&").replace(")", "").replace("(", "").replace("'", "")
    params = [p.strip() for p in string.split(",")]
    
    if len(params) < 5: return ""

    category = "category1="+params[0] +"&"+ "category2=" + params[1]
    filename = params[2]
    option = params[3]
    datasubmitdate = params[4]
    
    air_yn = params[5] if len(params) > 5 else "N"
    kor_yn = params[6] if len(params) > 6 else "Y"
    special_yn = params[7] if len(params) > 7 else "N"

    r = Koreainvestment_MAKE_LIST_ARTICLE_URL(category, filename, option, datasubmitdate, air_yn, kor_yn, special_yn)

    parsed_url = urlparse.urlparse(r)
    query_params = urlparse.parse_qs(parsed_url.query)
    
    filepath = query_params.get('filepath', [''])[0]
    filename_val = query_params.get('filename', [''])[0]
    
    if filepath and filename_val:
        return f"http://file.truefriend.com/Storage/{filepath}/{filename_val}"
    else:
        return r

def Koreainvestment_MAKE_LIST_ARTICLE_URL(filepath, filename, option, datasubmitdate, air_yn, kor_yn, special_yn):
    filename = urllib.parse.quote(filename)
    host_name = "http://research.truefriend.com/streamdocs/openResearch"
    host_name2, host_name3 = "https://kis-air.com/kor/", "https://kis-air.com/us/"

    if filepath.startswith("?") or filepath.startswith("&"):
        filepath = filepath[1:]

    params = filepath.split("&")
    if len(params) == 2:
        p1, p2 = params[0], params[1]
        if (p1 == 'category1=01' and p2 in ['category2=01', 'category2=02', 'category2=03', 'category2=04', 'category2=05']):
            filepath = "research/research01"
        elif (p1 == 'category1=02' and p2 in ['category2=01', 'category2=02', 'category2=03', 'category2=04', 'category2=06', 'category2=08', 'category2=09', 'category2=10', 'category2=11', 'category2=12', 'category2=13', 'category2=14']):
            filepath = "research/research02"
        elif (p1 == 'category1=03' and p2 in ['category2=01', 'category2=02', 'category2=03']):
            filepath = "research/research03"
        elif (p1 == 'category1=04' and p2 in ['category2=00', 'category2=01', 'category2=02', 'category2=03']):
            filepath = "research/research04"
        elif p1 == 'category1=05':
            filepath = "research/research05"
        elif p1 == 'category1=07' and p2 == 'category2=01':
            filepath = "research/research07"
        elif p1 == 'category1=08' and p2 in ['category2=03', 'category2=04', 'category2=05']:
            filepath = "research/research08"
        elif p1 == 'category1=06' and p2 in ['category2=01', 'category2=02']:
            filepath = "research/research06"
        elif p1 == 'category1=09' and p2 == 'category2=00':
            filepath = "research/research11"
        elif p1 == 'category1=10' and p2 in ['category2=01', 'category2=04', 'category2=06']:
            if p2 == 'category2=06': filepath = "research/research_emailcomment"
            elif p2 == 'category2=04': filepath = "research/china"
            else: filepath = "research/research10"
        elif p1 == 'category1=14' and p2 == 'category2=01':
            filepath = "research/research14"
        elif p1 == 'category1=13' and p2 == 'category2=01':
            filepath = "research/research11"
        elif p1 == 'category1=17': # 미국 현지 리서치 (Stifel)
            filepath = "research/research17"
        elif p1 == 'category1=15' and p2 == 'category2=01':
            filepath = "research/research01"
        elif p1 == 'category1=16' and p2 == 'category2=01':
            filepath = "research/research15"

    if not option: option = "01"

    if params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        return f"{host_name2 if kor_yn == 'Y' else host_name3}{datasubmitdate}/{'special' if special_yn == 'Y' else 'daily'}"
    else:
        return f"{host_name}?filepath={urllib.parse.quote(filepath)}&filename={filename}&option={option}"

if __name__ == "__main__":
    results = asyncio.run(Koreainvestment_selenium_checkNewArticle())
    
    # 스티펠(BOARD_ORDER: 10) 데이터만 필터링해서 마지막 2개 출력
    stifel_data = [item for item in results if item["ARTICLE_BOARD_ORDER"] == 10]
    print("\n" + "="*50)
    print("STIFEL DATA PDF URL CHECK (LAST 2 ITEMS)")
    print("="*50)
    for item in stifel_data[-2:]:
        import json
        print(json.dumps(item, indent=4, ensure_ascii=False))
        print("-" * 50)
