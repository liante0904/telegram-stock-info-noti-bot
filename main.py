#!/usr/bin/env python
#pyenv https://www.daleseo.com/python-pyenv/

# encoding=utf-8
#https://kslee7746.tistory.com/entry/텔레그램-웹페이지-게시물-업데이트-알람-봇-만들기1
#https://besixdouze.net/24
#https://steemit.com/kr-dev/@maanya/30
#https://medium.com/@jesamkim/%EC%BD%94%EB%A1%9C%EB%82%9819-%EA%B5%AD%EB%82%B4-%EB%B0%9C%EC%83%9D-%ED%98%84%ED%99%A9-%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8-%EC%95%8C%EB%A6%BC%EB%B4%87-%EB%A7%8C%EB%93%A4%EA%B8%B0-792022cec710
#pip install python-telegram-bot
#pip freeze > requirements.txt
#https://beomi.github.io/gb-crawling/posts/2017-04-20-HowToMakeWebCrawler-Notice-with-Telegram.html
# 텔레그램 알림 채널 만들기 : https://blex.me/@mildsalmon/%ED%95%9C%EB%9D%BC%EB%8C%80%ED%95%99%EA%B5%90-%EA%B3%B5%EC%A7%80-%EC%95%8C%EB%A6%BC-%EB%B4%87-%EC%A0%9C%EC%9E%91%EA%B8%B0-3-%EC%BD%94%EB%93%9C%EB%B6%84%EC%84%9D-telegrambot

# BOT_INFO_URL = https://api.telegram.org/bot1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w/getUpdates
import os
import telegram
import requests
import time
import ssl
from bs4 import BeautifulSoup
from requests import get  # to make GET request
import urllib.request
from clint.textui import progress

# 기본 URL
ARTICLE_BASE_URL = ""
# 게시판 이름
BOARD_NAME  = ["이슈브리프" , "기업분석", "산업분석"]
# 게시글 갱신 시간
REFRESH_TIME = 600
# 텔레그램 발송 메세지 변수
sendMessageText = ""
# 발송한 연속키
#nNxtIdx = [2279, 7617, 3848]
nNxtIdx = [0, 0, 0]
# 새로 올라온 게시글 개수
nNewFeedCnt = 0

# 이모지
fire = u'\U0001F525'
pick = u'\U0001F449'

def checkNewArticle():
    # 게시글 url의 경우 
    # 1. 앞에 "https://www.ebestsec.co.kr/EtwFrontBoard/" 를 추가
    # 2. amp; 를 삭제처리를 해야함

    # 게시글 내 첨부파일의 경우 
    # 1. 앞에 "https://www.ebestsec.co.kr/_bt_lib/util/download.jsp?dataType=" 를 추가
    # 2. 링크에서 알맹이를 붙이면 됨 -> javascript:download("08573D2F59307A57F4FC67A81B8C333A4C884E6D2951A32F4A48B73EF4E6EC22A0E62B351A025A54E20CB47DEF8A0A801BF2F7B5E3E640975E88D7BACE3B4A49F83020ED90019B489B3C036CF8AB930DCF4795CE87DE76454465F0CF7316F47BF3A0BC08364132247378E3AABC8D0981627BD8F94134BF00D27B03D8F04AC8C04369354956052B75415A9585589694B5F63378DFA40C6BA6435302B96D780C3B3EB2BF0C866966D4CE651747574C8B25208B848CBEBB1BE0222821FC75DCE016")
    global ARTICLE_BASE_URL

    requests.packages.urllib3.disable_warnings()

    ARTICLE_BASE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/'
    # 이슈브리프
    TARGET_URL_0 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=146&left_menu_no=211&front_menu_no=1029&parent_menu_no=211'
    # 이베스트 기업분석 게시판
    TARGET_URL_1 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=36&left_menu_no=211&front_menu_no=212&parent_menu_no=211'
    # 산업분석
    TARGET_URL_2 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=37&left_menu_no=211&front_menu_no=213&parent_menu_no=211'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)
    
    # URL GET
    for idx, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        parse(idx, TARGET_URL)
        time.sleep(5)
 

def parse(idx, TARGET_URL):
    global sendMessageText
    global nNxtIdx
    global nNewFeedCnt

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    
    # 현재 최근 게시글 인덱스
    ntotalIdx = int( soup.select('span.info')[0].text.replace("Total", "").replace("Page 1", "").strip() )
    #nNxtIdx[idx] = int( totalIdx[0].text.replace("Total", "").replace("Page 1", "").strip() )
    print('전체 게시글', ntotalIdx, '게시글 연속키', nNxtIdx[idx])
    if nNxtIdx[idx] == 0: # 첫 실행인 경우 임의로 가장 마지막 게시글을 발송
        print('###첫실행구간###')
        # 게시글 제목
        soup = soup.find_all('td', class_='subject')
        ARTICLE_URL = ARTICLE_BASE_URL + soup[0].find('a').attrs['href'].replace("amp;", "")
        print('게시판 이름:', BOARD_NAME[idx]) # 게시판 종류
        print('게시글 제목:',soup[0].find('a').text ) # 게시글 제목
        print('게시글URL:',ARTICLE_BASE_URL + soup[0].find('a').attrs['href'].replace("amp;", "")) # 주소
        print('############')

        articleTitle = ''
        articleTitle += fire+ BOARD_NAME[idx] + fire + "\n"
        articleTitle += soup[0].find('a').text + "\n"
        sendMessageText = articleTitle 
        sendMessageText += pick + ARTICLE_URL 
        
        # ARTICLE_BASE_URL + soup[0].find('a').attrs['href'].replace("amp;", "")
        downloadFile(ARTICLE_URL)
        #send() # 서버 재 실행시 첫 발송 주석
        nNxtIdx[idx] = ntotalIdx # 첫 실행시 인덱스 설정

    else: # 두번째 실행인 경우
        print('###ELSE구간###')
        soup = soup.find_all('td', class_='subject')
        #nIdx = int(soup.select('tbody > tr > td')[0]) # 현재 게시글 번호
        nNewFeedCnt = ntotalIdx - nNxtIdx[idx] # 새로 올라온 게시글 개수
        
        print('### 새로운 게시글 개수:', nNewFeedCnt,' ###')
        while nNewFeedCnt > 0: # 새 게시글이 올라옴
            print('현재 게시판 :',BOARD_NAME[idx],' 새로운 게시글 수:', nNewFeedCnt)
            articleTitle = soup[nNewFeedCnt-1].find('a').text + "\n"
            sendMessageText = articleTitle 
            sendMessageText += ARTICLE_BASE_URL 
            sendMessageText += soup[nNewFeedCnt-1].find('a').attrs['href'].replace("amp;", "")
            send()
            nNewFeedCnt -= 1
            print('nNewFeedCnt', nNewFeedCnt)
            if nNewFeedCnt == 0 : 
                print('새로운 게시글 모두 전송 완료')
                nNxtIdx[idx] = ntotalIdx
                return

        return False


def downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME
    ATTACH_BASE_URL = 'https://www.ebestsec.co.kr/_bt_lib/util/download.jsp?dataType='

    webpage = requests.get(ARTICLE_URL, verify=False)
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a')['href']
    ATTACH_URL = attachFileCode.replace('Javascript:download("', ATTACH_BASE_URL).replace('")', '')
    print('첨부파일 URL : ',ATTACH_URL)
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').text.strip()
    print('첨부파일이름 : ',ATTACH_FILE_NAME)

    with open(ATTACH_FILE_NAME, "wb") as file:   # open in binary mode
        response = get(ATTACH_URL, verify=False)               # get request
        file.write(response.content)      # write to file
    
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def send():
    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 : ',me)

    #생성한 텔레그램 봇 /start 시작 후 사용자 id 받아 오기
    #chat_id = bot.getUpdates()[-1].message.chat.id

    chat_id = '-1001431056975' # 이베스트 게시물 알림 채널
    #chat_id = '-1001474652718' # 테스트 채널

    bot.sendMessage(chat_id = chat_id, text = sendMessageText)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    bot.sendDocument(chat_id = chat_id, document = open(ATTACH_FILE_NAME, 'rb') )
    os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
       
# 액션 플랜 
# 1. 10분 간격으로 게시글을 읽어옵니다.
# 2. 게시글이 마지막 게시글이 이전 게시글과 다른 경우(새로운 게시글이 올라온 경우) 
    # 메세지로 게시글 정보르 보냅니다
    # 아닌 경우 다시 1번을 반복합니다.
def main():
    print('########Program Start Run########')
    while True:
        print("checkNewArticle() => 새 게시글 정보 확인")
        checkNewArticle()
        time.sleep(REFRESH_TIME)
        print('######',REFRESH_TIME,'초 후 게시글 재 확인######')


if __name__ == "__main__":
	main()