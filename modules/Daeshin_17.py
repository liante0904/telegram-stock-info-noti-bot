# -*- coding:utf-8 -*- 
import sys
import os
import re
import asyncio
import aiohttp
from datetime import datetime

from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo

async def Daeshin_checkNewArticle():
    SEC_FIRM_ORDER      = 17
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    """대신증권의 새 게시글 정보를 비동기로 확인하는 함수"""
    BASE_URL = "https://money2.creontrade.com/E5/m_net/ResearchCenter/Work/"
    url = BASE_URL + "mre_DM_Mobile_Research.aspx?b_code=91&m=0&p=0&v=0&word=SVBPKOq4sOyXheqzteqwnCkg7KO86rSA6riw7JeF&searchtype=Research&category="

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Referer": url
    }

    async def fetch_hidden_values(session, url):
        """초기 페이지에서 hidden 필드 값을 추출하는 함수"""
        async with session.get(url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # hidden 필드 값 추출
            viewstate = soup.find(id="__VIEWSTATE")['value']
            viewstate_gen = soup.find(id="__VIEWSTATEGENERATOR")['value']
            event_validation = soup.find(id="__EVENTVALIDATION")['value']
            
            return viewstate, viewstate_gen, event_validation

    async def fetch_page_data(session, page, viewstate, viewstate_gen, event_validation):
        """각 페이지의 데이터와 hidden 필드를 갱신하여 크롤링하는 함수"""
        data = {
            "ctl00$sm1": "ctl00$ContentPlaceHolder1$UpdatePanel1|ctl00$ContentPlaceHolder1$bt_refresh",
            "ctl00$ContentPlaceHolder1$hf_page": str(page),
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_gen,
            "__EVENTVALIDATION": event_validation,
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$bt_refresh": ""
        }

        async with session.post(url, headers=headers, data=data) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 게시글 목록 추출
            items = soup.find_all("li")
            if not items:
                return None  # 더 이상 데이터가 없으면 None 반환
            
            for item in items:
                title = item.find("strong", class_="title1").text.strip()
                # Check if the input string starts with '[대신증권'
                if title.startswith("[대신증권 "):
                    # Using replace method to modify the string
                    title = title.replace("[대신증권 ", "[")
                reg_dt = item.find("span", class_="date").text.strip()
                author = item.find("span", class_="time").text.strip()
                
                # 더 일반적인 'a' 태그 찾기
                link_tag = item.find("a")
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    article_url = BASE_URL + href
                else:
                    print("No href found for this item")
                    continue
                
                # 개별 게시글의 ATTACH_URL 추출
                attach_url = await fetch_attach_url(session, article_url)

                # json 데이터 생성 및 리스트에 추가
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", reg_dt),
                    "ARTICLE_URL": article_url,
                    "DOWNLOAD_URL": attach_url,
                    "TELEGRAM_URL": attach_url,
                    "KEY": attach_url,
                    "ARTICLE_TITLE": title,
                    "WRITER": author,
                    "SAVE_TIME": datetime.now().isoformat()
                })

    async def fetch_attach_url(session, article_url):
        """ARTICLE_URL 페이지에서 ATTACH_URL 추출"""
        async with session.get(article_url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            attach_element = soup.find(id="btnPdfLoad")
            
            if attach_element:
                return attach_element['href']
            return None

    async with aiohttp.ClientSession() as session:
        # 초기 GET 요청으로 hidden 값 추출
        viewstate, viewstate_gen, event_validation = await fetch_hidden_values(session, url)
        
        # 각 페이지 비동기적으로 요청
        tasks = []
        for page in range(1, 5):
            tasks.append(fetch_page_data(session, page, viewstate, viewstate_gen, event_validation))
        
        # 모든 태스크 완료 대기
        await asyncio.gather(*tasks)
        # print(json_data_list)
        return json_data_list


async def main():
    articles = await Daeshin_checkNewArticle()
    # detailed_articles = await fetch_detailed_url(articles)
    # db = SQLiteManager()
    # inserted_count = db.insert_json_data_list(detailed_articles, 'data_main_daily_send')  # 모든 데이터를 한 번에 삽입
    # print(inserted_count)
    # print(json.dumps(detailed_articles, indent=4, ensure_ascii=False))
    print(articles)

if __name__ == "__main__":
    asyncio.run(main())