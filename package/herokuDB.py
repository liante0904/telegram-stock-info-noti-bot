# -*- coding:utf-8 -*- 
import os
import sys
import datetime
from pytz import timezone
import telegram
import requests
import datetime
import time
import ssl
import json
import re
import asyncio
import pymysql
import pymysql.cursors
from typing import List
from bs4 import BeautifulSoup
import urllib.parse as urlparse
import urllib.request


global SECRETS # 시크릿 키
global CLEARDB_DATABASE_URL
global TELEGRAM_BOT_INFO
global TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET
global TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET
global TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS
global TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS
global TELEGRAM_CHANNEL_ID_ITOOZA
global TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT
global TELEGRAM_CHANNEL_ID_REPORT_ALARM
global TELEGRAM_CHANNEL_ID_TODAY_REPORT
global TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN
global TELEGRAM_CHANNEL_ID_TEST
global TELEGRAM_USER_ID_DEV
global IS_DEV


SECRETS = ''
print(os.getcwd())
j = os.path.join("../", 'secrets.json')
if os.path.isfile(j): # 로컬 개발 환경
    with open(j) as f:
        SECRETS = json.loads(f.read())
        print("SECRETS:",SECRETS)
    CLEARDB_DATABASE_URL                        =   SECRETS['CLEARDB_DATABASE_URL']
    TELEGRAM_BOT_INFO                           =   SECRETS['TELEGRAM_BOT_INFO']
    TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   SECRETS['TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET']
    TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   SECRETS['TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET']
    TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS']
    TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS']
    TELEGRAM_CHANNEL_ID_ITOOZA                  =   SECRETS['TELEGRAM_CHANNEL_ID_ITOOZA']
    TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   SECRETS['TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT']
    TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   SECRETS['TELEGRAM_CHANNEL_ID_REPORT_ALARM']
    TELEGRAM_CHANNEL_ID_TODAY_REPORT            =   SECRETS['TELEGRAM_CHANNEL_ID_TODAY_REPORT']
    TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN         =   SECRETS['TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN']
    TELEGRAM_CHANNEL_ID_TEST                    =   SECRETS['TELEGRAM_CHANNEL_ID_TEST']
    TELEGRAM_USER_ID_DEV                        =   SECRETS['TELEGRAM_USER_ID_DEV']
    IS_DEV                                      =   True
else: # 서버 배포 환경(heroku)
    CLEARDB_DATABASE_URL                        =   os.environ.get('CLEARDB_DATABASE_URL')
    TELEGRAM_BOT_INFO                           =   os.environ.get('TELEGRAM_BOT_INFO')
    TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   os.environ.get('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
    TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   os.environ.get('TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET')
    TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
    TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')
    TELEGRAM_CHANNEL_ID_ITOOZA                  =   os.environ.get('TELEGRAM_CHANNEL_ID_ITOOZA')
    TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   os.environ.get('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
    TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   os.environ.get('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
    TELEGRAM_CHANNEL_ID_TODAY_REPORT            =   os.environ.get('TELEGRAM_CHANNEL_ID_TODAY_REPORT')
    TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN         =   os.environ.get('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
    TELEGRAM_CHANNEL_ID_TEST                    =   os.environ.get('TELEGRAM_CHANNEL_ID_TEST')
    TELEGRAM_USER_ID_DEV                        =   os.environ.get('TELEGRAM_USER_ID_DEV')
    IS_DEV                                      =   False

    print



def MySQL_Open_Connect():
    global conn
    global cursor
    
    # clearDB 
    # url = urlparse.urlparse(os.environ['CLEARDB_DATABASE_URL'])
    url = urlparse.urlparse(CLEARDB_DATABASE_URL)
    conn = pymysql.connect(host=url.hostname, user=url.username, password=url.password, charset='utf8', db=url.path.replace('/', ''), cursorclass=pymysql.cursors.DictCursor, autocommit=True)
    cursor = conn.cursor()
    return cursor

def SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
    global FIRM_NM
    global BOARD_NM
    global BOARD_URL
    global NXT_KEY
    global TEST_SEND_YN
    global NXT_KEY_ARTICLE_TITLE
    global SEND_YN
    global SEND_TIME_TERM
    global TODAY_SEND_YN
    global conn
    global cursor

    cursor = MySQL_Open_Connect()
    dbQuery  = " SELECT FIRM_NM, BOARD_NM, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, BOARD_URL, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s "
    dbResult = cursor.execute(dbQuery, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print(row)
        FIRM_NM = row['FIRM_NM']
        BOARD_NM = row['BOARD_NM']
        BOARD_URL = row['BOARD_URL']
        NXT_KEY = row['NXT_KEY']
        NXT_KEY_ARTICLE_TITLE = row['NXT_KEY_ARTICLE_TITLE']
        SEND_YN = row['SEND_YN']
        SEND_TIME_TERM = int(row['SEND_TIME_TERM'])
        TODAY_SEND_YN = row['TODAY_SEND_YN']

    conn.close()
    return dbResult

def SelSleepKey(*args):
    global NXT_KEY
    global TEST_SEND_YN
    global SEND_YN
    global SEND_TIME_TERM
    global TODAY_SEND_YN
    global conn
    global cursor

    nSleepCnt = 0
    nSleepCntKey = 0

    cursor = MySQL_Open_Connect()
    dbQuery  = " SELECT 		SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   "
    dbResult = cursor.execute(dbQuery, (9999))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print(row)
        nSleepCnt = row['ARTICLE_BOARD_ORDER']
        nSleepCntKey = row['NXT_KEY']

    conn.close()
    SleepTuple = (int(nSleepCnt), int(nSleepCntKey))
    return SleepTuple

def DelSleepKey(*args):
    cursor = MySQL_Open_Connect()
    dbQuery  = " DELETE  FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = 9999"
    dbResult = cursor.execute(dbQuery)

    conn.close()
    return dbResult

def InsSleepKey(*args):
    global NXT_KEY
    global TEST_SEND_YN
    global conn
    global cursor
    cursor = MySQL_Open_Connect()
    dbQuery = "INSERT INTO NXT_KEY (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, CHANGE_DATE_TIME)VALUES ( 9999, 0, ' ', DEFAULT);"
    cursor.execute(dbQuery)
    conn.close()
    return dbQuery

def InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY):
    global NXT_KEY
    global TEST_SEND_YN
    global conn
    global cursor
    cursor = MySQL_Open_Connect()
    dbQuery = "INSERT INTO NXT_KEY (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, CHANGE_DATE_TIME)VALUES ( %s, %s, %s, DEFAULT);"
    cursor.execute(dbQuery, ( SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY ))
    NXT_KEY = FIRST_NXT_KEY
    conn.close()
    return NXT_KEY

def UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE):
    global NXT_KEY
    global TEST_SEND_YN
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET NXT_KEY = %s , NXT_KEY_ARTICLE_TITLE = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, ( FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER ))
    if dbResult:
        print('####DB업데이트 된 연속키####', end='\n')
        print(dbResult)
        NXT_KEY = FIRST_NXT_KEY
    conn.close()
    return dbResult

def UpdTodaySendKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, TODAY_SEND_YN):
    global NXT_KEY
    global TEST_SEND_YN
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET TODAY_SEND_YN = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, (TODAY_SEND_YN, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    conn.close()
    return dbResult
 