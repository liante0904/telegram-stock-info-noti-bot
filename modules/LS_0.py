# -*- coding:utf-8 -*- 
import os
import gc
import requests
import time
import re
import urllib.request
import sys
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
    return json_data_list, skip_boards

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
                base_value = alt_value.split(".")[0]
                parts = base_value.split("_")

                URL_PARAM = article["REG_DT"]
                url = f"https://msg.ls-sec.co.kr/eum/K_{URL_PARAM}_{parts[0]}_{parts[1]}.pdf"
            else:
                URL_PARAM = article["REG_DT"]
                URL_PARAM_0 = 'B' + URL_PARAM[:6]

                ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
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
