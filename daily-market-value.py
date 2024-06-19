# -*- coding:utf-8 -*- 
import sys
import telegram
import requests
import asyncio
from bs4 import BeautifulSoup

from package.common import *
from package.SecretKey import SecretKey
import package.common as common

############공용 상수############
# INTERVAL_TIME = 3 # 사용하지 않음

# 게시글 갱신 시간
# REFRESH_TIME = 60 * 20 # 사용하지 않음

# 텔레그램 채널 발송 여부
# SEND_YN = '' # 사용하지 않음
# TODAY_SEND_YN = '' # 사용하지 않음

# 이모지
# EMOJI_FIRE = u'\U0001F525' # 사용하지 않음
# EMOJI_PICK = u'\U0001F449' # 사용하지 않음

# 연속키용 상수
# FIRST_ARTICLE_INDEX = 0 # 사용하지 않음

# 메세지 전송용 레포트 제목(말줄임표 사용 증권사)
# LIST_ARTICLE_TITLE = '' # 사용하지 않음
#################### global 변수 정리 ###################################
# FIRM_NM = '' # 사용하지 않음
# BOARD_NM = '' # 사용하지 않음
#################### global 변수 정리 끝###################################
SECRET_KEY = SecretKey()
SECRET_KEY.load_secrets()

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    # 운영 채널(증권사 신규 레포트 게시물 알림방)
    return await bot.sendMessage(chat_id = SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

def GetSendChatId():
    SendMessageChatId = SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM # 
    return SendMessageChatId
   
def main():
    print(common.GetCurrentDate('YYYYMMDD'), common.GetCurrentDay())
    sendMessageText = ''
    url = 'https://stockwatch.co.kr'
    
    response = requests.get(url)
    # HTML parse
    soup = BeautifulSoup(response.text, "html.parser")
    rTitle1 = soup.select_one('body > div.layout > div.content > div.market_wrap > div > div.group.jisu > div.header > h3')
    rTitle1_1 = soup.select_one('body > div.layout > div.content > div.market_wrap > div > div.group.jisu > div.header > p')
    rTitle1_2 = soup.select_one('#jisu > div:nth-child(1)')
    rTitle1_3 = soup.select_one('#jisu > div:nth-child(2)')
    rTitle1_4 = soup.select_one('#jisu > div:nth-child(3)')

    rTitle2 = soup.select_one('body > div.layout > div.content > div.market_wrap > div > div.group.valuation > div.header > h3')
    
    soupList = soup.select('body > div.layout > div.content > div.market_wrap > div > div.group.valuation > div.items')
    rDate = soup.select_one('body > div.layout > div.content > div.market_wrap > div > div.group.valuation > div.header > p').get_text()

    sendMessageText = "\n\n" + "* ●" + '마켓밸류에이션*  ' + '_' + rDate + '일자 기준_' + "\n \n" 
    for r in soupList:
        print(rTitle1.get_text(separator='\n').strip(), rTitle1_1.get_text(separator='\n').strip())
        # 코스피
        sendMessageText += extract_data(rTitle1_2) + "\n"
        # 코스닥
        sendMessageText += extract_data(rTitle1_3) + "\n"
        sendMessageText += "\n"
        # 마켓벨류
        sendMessageText += r.select_one('.item1').text.strip().replace('\n\n', '\n').replace('\n', ' / ').replace('PER', '*PER* : ').replace('PBR', '*PBR* : ').replace('ROE', '*ROE* : ') + "\n" 
        sendMessageText += r.select_one('.item2').text.strip().replace('\n\n', '\n').replace('\n', ' / ').replace('PER', '*PER* : ').replace('PBR', '*PBR* : ').replace('ROE', '*ROE* : ') + "\n" 
        sendMessageText += "\n"
        # 달러
        sendMessageText += extract_data(rTitle1_4) + "\n"

    print(sendMessageText)

    if len(sendMessageText) > 0: asyncio.run(sendMessage(sendMessageText))

def extract_data(element):
    if element:
        # index_name 추출
        index_name = element.select_one('.index_name').get_text(strip=True)
        
        # index_value 추출
        index_value_tag = element.select_one('.index_value')
        if index_value_tag:
            index_value_str = index_value_tag.get_text(strip=True).replace(",", "")
            index_value = float(index_value_str)
        
        # stock-down 또는 stock-up 값 추출 및 전일종가 지수 계산
        index_range_tag = element.select_one('.index_range > span')
        if index_range_tag:
            class_name = index_range_tag.get('class', [None])[0]
            index_range_value_str = index_range_tag.get_text(strip=True).replace(",", "")
            index_range_value = float(index_range_value_str)
            
            if index_name == "원/달러":
                if class_name == 'stock-down':
                    previous_close = index_value + index_range_value
                    result = (f"원&달러 / {index_value:.2f}원  / -{index_range_value:.2f}원 하락 (전일 {previous_close:.2f}원)")
                elif class_name == 'stock-up':
                    previous_close = index_value - index_range_value
                    result = (f"원&달러 / {index_value:.2f}원  / +{index_range_value:.2f}원 상승 (전일 {previous_close:.2f}원)")
            else:
                if class_name == 'stock-down':
                    previous_close = index_value + index_range_value
                    previous_label = {
                        "코스피": "→ 코스피 지수 :",
                        "코스닥": "→ 코스닥 지수 :"
                    }.get(index_name, "전일 지수")
                    result = (f"{previous_label} {previous_close:.2f}pt")
                elif class_name == 'stock-up':
                    previous_close = index_value - index_range_value
                    previous_label = {
                        "코스피": "→ 코스피 지수 :",
                        "코스닥": "→ 코스닥 지수 :"
                    }.get(index_name, "전일 지수")
                    result = (f"{previous_label} {previous_close:.2f}pt")
            return result
    else:
        return "Element not found"

if __name__ == "__main__":
    main()
