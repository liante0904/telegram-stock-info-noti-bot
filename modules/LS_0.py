# -*- coding:utf-8 -*- 
import os
import gc
import requests
import time
import re
import urllib.request
import sys
import requests
from bs4 import BeautifulSoup
import time

from datetime import datetime, timedelta, date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.WebScraper import SyncWebScraper
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

def LS_checkNewArticle(page=1, is_imported=False, skip_boards=None):
    SEC_FIRM_ORDER = 0
    json_data_list = []
    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = (
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=146&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=36&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=37&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=38&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=147&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=39&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=183&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=145&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=33&currPage={page}',
        f'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=253&currPage={page}'
    )

    if skip_boards is None:
        skip_boards = set()

    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        if ARTICLE_BOARD_ORDER in skip_boards:
            continue  # Skip this board if no more articles are available

        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        retries = 3
        while retries > 0:
            try:
                scraper = SyncWebScraper(TARGET_URL, firm_info)
                soup = scraper.Get()
                if soup is None:
                    raise ValueError("Empty response from server.")
                soupList = soup.select('#contents > table > tbody > tr')
                break  # 성공하면 while loop 탈출
            except (AttributeError, ValueError) as e:
                print(f"Error fetching data: {e}. Retrying... ({3 - retries} retries left)")
                retries -= 1
                time.sleep(1)
                if retries == 0:
                    skip_boards.add(ARTICLE_BOARD_ORDER)
                    print(f"Skipping board {ARTICLE_BOARD_ORDER} from page {page} onward.")
                    continue

        print(f"{firm_info.get_firm_name()}의 {firm_info.get_board_name()} 게시판...")

        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        if not soupList and not is_imported:
            continue

        for list in soupList:
            try:
                str_date = list.select('td')[3].get_text()
                list = list.select('a')
                # print(list[0]['href'])
                LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", "")
                LIST_ARTICLE_TITLE = list[0].get_text()
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]")+1:len(LIST_ARTICLE_TITLE)]
                POST_DATE = str_date.strip()

                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", POST_DATE),
                    "ARTICLE_URL": '',
                    "ATTACH_URL": '',
                    "DOWNLOAD_URL": '',
                    "TELEGRAM_URL": '',
                    "KEY": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            except IndexError:
                print("IndexError: list index out of range - Skipping this board.")
                skip_boards.add(ARTICLE_BOARD_ORDER)  # Add to skip_boards on IndexError
                break  # Skip the rest of this board’s articles

    del soup
    gc.collect()
    return json_data_list#, skip_boards

def LS_detail(articles, firm_info):
    requests.packages.urllib3.disable_warnings()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    # articles가 리스트가 아닐 경우 리스트로 변환하여 단일 항목도 처리 가능하게 함
    if isinstance(articles, dict):
        articles = [articles]  # 단일 딕셔너리를 리스트로 변환
    elif isinstance(articles, str):
        print("Error: Invalid article format. Expected a dictionary or a list of dictionaries.")
        return []  # 문자열이 주어진 경우 빈 리스트 반환
    
    for article in articles:
        TARGET_URL = article["KEY"]#.replace('&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1', '')
        time.sleep(0.1)

        # '.pdf'가 URL에 포함된 경우 해당 URL을 그대로 사용하고 다음 레코드로 진행
        if '.pdf' in TARGET_URL:
            article['ARTICLE_URL'] = TARGET_URL
            article['TELEGRAM_URL'] = TARGET_URL
            article['DOWNLOAD_URL'] = TARGET_URL
            continue

        # 요청 보내기
        try:
            response = requests.get(TARGET_URL, headers=headers, verify=False)
            # 상태 코드가 200이 아닌 경우 로그 출력 후 다음 레코드로 이동
            if response.status_code != 200:
                print(f"Skipping URL due to status code {response.status_code}: {TARGET_URL}")
                continue  # 다음 레코드로 넘어감
        except requests.RequestException as e:
            print(f"Error requesting URL {TARGET_URL}: {e}")
            continue  # 요청 실패 시 다음 레코드로 이동

        # HTML 파싱
        soup = BeautifulSoup(response.content, "html.parser")


        # 각 tr에서 데이터 추출
        trs = soup.select('tr')
        for tr in trs:
            th = tr.select_one('th')
            td = tr.select_one('td')

            if th and td:
                th_text = th.get_text(strip=True)
                td_text = td.get_text(strip=True)

                if th_text == '제목':
                    article['ARTICLE_TITLE'] = td_text
                elif th_text == '작성일':
                    pass # 이미 메인 fetch에서 가져옴
                    # article['REG_DT'] = td_text
                elif th_text == '첨부파일':
                    attach_a = tr.select_one('td.attach a')
                    if attach_a:
                        article['ATTACH_FILE_NAME'] = attach_a.get_text(strip=True)
                        
                    try:
                        img = soup.select_one('#contents > div.tbViewCon > div > html > body > p > img')
                        print('******본문 이미지 추출******')
                        print(img) # 본문 이미지 추출 
                        print('******본문 이미지 파일명******')
                        img_filename = img.get("alt") if img else None
                        print(img_filename) # 본문 이미지 파일명
                        if img_filename:
                            name, extension  = os.path.splitext(img_filename)

                            # 정규표현식으로 '_8자리 숫자' 찾기
                            match = re.search(r'_(\d{8})$', name)

                            if match:
                                # 날짜 추출
                                date_part = match.group(1)
                                # 날짜를 제외한 나머지 이름 추출
                                new_name = re.sub(r'_(\d{8})$', '', name)
                                # 새로운 파일명 생성
                                new_filename = f"{date_part}_{new_name}.pdf"
                                url = f"https://msg.ls-sec.co.kr/eum/K_{new_filename}"
                                print(url)  # 출력: https://msg.ls-sec.co.kr/eum/K_20210618_jh.shin_410.pdf
                            else:
                                URL_PARAM = article["REG_DT"]
                                URL_PARAM_0 = 'B' + URL_PARAM[:6]

                                ATTACH_FILE_NAME = article['ATTACH_FILE_NAME']
                                ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%') 
                                URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)

                                ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
                                url = ATTACH_URL.format(URL_PARAM_0, URL_PARAM_1)
                                print("파일명에서 _8자리 숫자를 찾을 수 없습니다.")
                                
                        else:
                            URL_PARAM = article["REG_DT"]
                            URL_PARAM_0 = 'B' + URL_PARAM[:6]

                            ATTACH_FILE_NAME = article['ATTACH_FILE_NAME']
                            ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%') 
                            URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)

                            ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
                            url = ATTACH_URL.format(URL_PARAM_0, URL_PARAM_1)

                        article['ARTICLE_URL'] = urllib.parse.quote(url, safe=':/')
                        article['TELEGRAM_URL'] = urllib.parse.quote(url, safe=':/')
                        article['DOWNLOAD_URL'] = urllib.parse.quote(url, safe=':/')

                    except Exception as e:
                        print(f"Error processing article: {e}")

    return articles


if __name__ == "__main__":
    page = 1
    all_articles = []
    skip_boards = set()

    while True:
        print(f"Page:{page}.. Process..")
        articles, skip_boards = LS_checkNewArticle(page, is_imported=False, skip_boards=skip_boards)
        if not any(articles):
            break  # Exit loop if no articles found
        all_articles.extend(articles)
        page += 1

    if not all_articles:
        print("No articles found.")
    else:
        db = SQLiteManager()
        inserted_count = db.insert_json_data_list(all_articles, 'data_main_daily_send')
        print(f"Inserted {inserted_count} articles.")
