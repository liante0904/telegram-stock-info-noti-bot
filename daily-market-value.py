# -*- coding:utf-8 -*- 
import sys
import telegram
import requests
import asyncio
from bs4 import BeautifulSoup

from package.common import *
from package.SecretKey import SecretKey
import package.common as common

SECRET_KEY = SecretKey()
SECRET_KEY.load_secrets()

async def sendMessage(sendMessageText):
    bot = telegram.Bot(token=SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM, text=sendMessageText, disable_web_page_preview=True, parse_mode="Markdown")

def GetSendChatId():
    return SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM

def extract_data(element):
    if element:
        index_name = element.select_one('.index_name').get_text(strip=True)
        index_value_tag = element.select_one('.index_value')
        index_value = ""
        if index_value_tag:
            index_value_str = index_value_tag.get_text(strip=True).replace(",", "")
            index_value = float(index_value_str)

        index_range_tag = element.select_one('.index_range > span')
        index_range = ""
        if index_range_tag:
            class_name = index_range_tag.get('class', [None])[0]
            index_range_value_str = index_range_tag.get_text(strip=True).replace(",", "")
            index_range_value = float(index_range_value_str)

            if class_name == 'stock-down':
                #previous_close = index_value + index_range_value
                index_range = f"📉 || -{index_range_value:.2f}"#(전일 {previous_close:.2f})
            elif class_name == 'stock-up':
                #previous_close = index_value - index_range_value
                index_range = f"📈 || +{index_range_value:.2f}"#(전일 {previous_close:.2f})"

        return f"======={index_name}=======\n {index_value:.2f}{index_range}"
    else:
        return "Element not found"

def main():
    print(common.GetCurrentDate('YYYYMMDD'), common.GetCurrentDay())
    sendMessageText = ''
    url = 'https://itooza.com/'
    
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    indices_data = []
    indices_items = soup.select("div.data.indices div.items div.inner div.item")
    for item in indices_items:
        indices_data.append(extract_data(item))

    valuation_data = []
    valuation_items = soup.select("div.data.valuation div.items div.inner div.item")
    for item in valuation_items:
        market_name = item.select_one("div.index_name").get_text(strip=True)
        per_value = item.select_one("div.index_cate.per span.index_value").get_text(strip=True)
        pbr_value = item.select_one("div.index_cate.pbr span.index_value").get_text(strip=True)
        roe_value = item.select_one("div.index_cate.roe span.index_value").get_text(strip=True)
        msg = f"======={market_name}=======\nPER: {per_value} || PBR: {pbr_value} || ROE: {roe_value}"
        valuation_data.append(msg)

    # 마켓 밸류에이션 날짜 정보 추출
    rDate_element = soup.select_one('div.data.valuation div.header > p')
    rDate = rDate_element.get_text() if rDate_element else "날짜 정보 없음"

    # 메시지 구성
    sendMessageText += "\n\n" + "* ●" + '마켓밸류에이션*  ' + '_' + rDate + '일자 기준_' + "\n \n"
    sendMessageText += "*오늘의 주요 지수*\n\n"
    for data in indices_data:
        sendMessageText += data + "\n\n"

    sendMessageText += "\n\n*마켓 밸류에이션*\n\n"
    for data in valuation_data:
        sendMessageText += data + "\n\n"

    print(sendMessageText)

    if len(sendMessageText) > 0: asyncio.run(sendMessage(sendMessageText))

if __name__ == "__main__":
    main()
