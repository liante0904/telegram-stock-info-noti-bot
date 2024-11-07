# -*- coding:utf-8 -*- 
import os
import time
import urllib.request
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.WebScraper import SyncWebScraper
from models.FirmInfo import FirmInfo


def LS_detail(articles, firm_info):
    for article in articles:
        
        TARGET_URL = article["KEY"].replace('&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1', '')
        time.sleep(0.1)

        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        soup = scraper.Get()
        img = soup.select_one('#contents > div.tbViewCon > div > html > body > p > img')
        
        alt_value = img.get("alt")

        # alt 값에서 필요한 정보만 추출하고 순서 재배치
        base_value = alt_value.split(".")[0]  # 확장자를 제외한 부분 추출
        parts = base_value.split("_")  # 언더스코어를 기준으로 분할


        # 게시글 제목
        trs = soup.select('tr')
        article['ARTICLE_TITLE'] = trs[0].select_one('td').text
        
        
        # 첨부파일 URL 조립 예시  
        # => https://www.ls-sec.co.kr/upload/EtwBoardData/B202410/20241002_한국 9월 소비자물가.pdf
        
        # # B포스팅 월
        URL_PARAM = article["REG_DT"]  # 예: "20231105" 형식
        URL_PARAM_0 = 'B' + URL_PARAM[:6]  # 'BYYYYMM' 형식으로 변환


        # parts[2] (날짜) + parts[0] + parts[1] 순으로 배치하여 URL 생성
        url = f"https://msg.ls-sec.co.kr/eum/K_{URL_PARAM}_{parts[0]}_{parts[1]}.pdf"
        # # 첨부 파일 이름과 URL 인코딩 처리
        # ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
        # ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%') 
        # URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)

        # # 최종 첨부 파일 URL 생성
        # ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
        # ATTACH_URL = ATTACH_URL.format(URL_PARAM_0, URL_PARAM_1)
        
        # # URL 인코딩 => 사파리 한글처리 
        # article['LIST_ARTICLE_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')
        # article['TELEGRAM_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')

        article['LIST_ARTICLE_URL'] = url
        article['TELEGRAM_URL'] = url
        
        # item['LIST_ARTICLE_TITLE'] = LIST_ARTICLE_TITLE
        # print(article)
        # print('*********확인용**************')
    print(articles)
    
    return articles
        


if __name__ == "__main__":
    test = [{"KEY": "https://www.ls-sec.co.kr/EtwFrontBoard/View.jsp?skey=&sval=&board_no=37&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1&board_seq=7679815",
             "REG_DT": "20241106"
             }]
    
    firm_info = FirmInfo(sec_firm_order=0)
    LS_detail(test, firm_info)