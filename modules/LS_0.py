# -*- coding:utf-8 -*- 
import os
import gc
import requests
import time
import re
import urllib.request
import sys
import os
from datetime import datetime, timedelta, date


from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper

# selenium


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.WebScraper import SyncWebScraper
from models.FirmInfo import FirmInfo

def LS_checkNewArticle():
    SEC_FIRM_ORDER      = 0
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 이슈브리프
    TARGET_URL_0 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=146'
    # 기업분석 게시판
    TARGET_URL_1 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=36'
    # 산업분석
    TARGET_URL_2 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=37'
    # 투자전략
    TARGET_URL_3 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=38'
    # Quant
    TARGET_URL_4 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=147'
    # Macro
    TARGET_URL_5 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=39'
    # FI/ Credit
    TARGET_URL_6 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=183'
    # Commodity
    TARGET_URL_7 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=145'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        soup = scraper.Get()

        soupList = soup.select('#contents > table > tbody > tr')
        
        # 현재 날짜
        today = date.today()
        # 7일 전 날짜 계산
        seven_days_ago = today - timedelta(days=7)

        nNewArticleCnt = 0        
        for list in soupList:
            str_date = list.select('td')[3].get_text()
            list = list.select('a')
            # print(list[0].text)
            # print('https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", ""))
            LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", "")
            LIST_ARTICLE_TITLE = list[0].get_text()
            LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]")+1:len(LIST_ARTICLE_TITLE)]
            POST_DATE = str_date.strip()
            # print('POST_DATE',POST_DATE)

            # POST_DATE를 datetime 형식으로 변환 (형식: yyyy.mm.dd)
            # try:
            #     post_date_obj = datetime.strptime(POST_DATE, '%Y.%m.%d').date()
            # except ValueError as e:
            #     print(f"날짜 형식 오류: {POST_DATE}, 오류: {e}")
            #     continue
            
            # REG_DT = post_date_obj.strftime('%Y%m%d')
            # print('post_date_obj',post_date_obj)
            # print('REG_DT:', REG_DT)
            # 7일 이내의 게시물만 처리
            # if post_date_obj < seven_days_ago:
            #     print(f"게시물 날짜 {POST_DATE}가 7일 이전이므로 중단합니다.")
            #     break

            # item = LS_detail(LIST_ARTICLE_URL, str_date, firm_info)
            # print(item)
            # if item:
            #     # LIST_ARTICLE_URL = item['LIST_ARTICLE_URL']
            #     DOWNLOAD_URL     = item['LIST_ARTICLE_URL']
            #     LIST_ARTICLE_TITLE = item['LIST_ARTICLE_TITLE']
            
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT": re.sub(r"[-./]", "", POST_DATE),
                "ARTICLE_URL": '',
                "ATTACH_URL": '',
                "DOWNLOAD_URL": '',
                "TELEGRAM_URL": '',
                "KEY": LIST_ARTICLE_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
            
    # 메모리 정리
    del soup
    gc.collect()
    return json_data_list


def LS_detail(articles, firm_info):
    for article in articles:
        TARGET_URL = article["KEY"].replace('&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1', '')
        time.sleep(0.1)

        scraper = SyncWebScraper(TARGET_URL, firm_info)

        # HTML parse
        soup = scraper.Get()

        trs = soup.select('tr')
        article['ARTICLE_TITLE'] = trs[0].select_one('td').get_text().strip()
        try:
            img = soup.select_one('#contents > div.tbViewCon > div > html > body > p > img')
            alt_value = img.get("alt") if img else None
            if alt_value:
                # alt 값에서 필요한 정보만 추출하고 순서 재배치
                base_value = alt_value.split(".")[0]  # 확장자를 제외한 부분 추출
                parts = base_value.split("_")  # 언더스코어를 기준으로 분할

                # URL 생성 (alt_value가 있는 경우)
                URL_PARAM = article["REG_DT"]  # 예: "20231105" 형식
                url = f"https://msg.ls-sec.co.kr/eum/K_{URL_PARAM}_{parts[0]}_{parts[1]}.pdf"

            else:
                # alt_value가 None인 경우 첨부 파일 URL 생성 (기존 방식 사용)


                # B포스팅 월
                URL_PARAM = article["REG_DT"]  # 예: "20231105" 형식
                URL_PARAM_0 = 'B' + URL_PARAM[:6]  # 'BYYYYMM' 형식으로 변환

                ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
                ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%') 
                URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)

                # 최종 첨부 파일 URL 생성
                ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
                url = ATTACH_URL.format(URL_PARAM_0, URL_PARAM_1)

            # URL 인코딩 => 사파리 한글처리 
            article['ARTICLE_URL'] = urllib.parse.quote(url, safe=':/')
            article['TELEGRAM_URL'] = urllib.parse.quote(url, safe=':/')
            article['DOWNLOAD_URL'] = urllib.parse.quote(url, safe=':/')

        except Exception as e:
            print(f"Error processing article: {e}")

    print(articles)
    return articles


if __name__ == "__main__":
    test = [{"KEY": "https://www.ls-sec.co.kr/EtwFrontBoard/View.jsp?skey=&sval=&board_no=36&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1&board_seq=7679835",
             "REG_DT": "20241106"
             }]
    
    firm_info = FirmInfo(sec_firm_order=0)
    LS_detail(test, firm_info)
