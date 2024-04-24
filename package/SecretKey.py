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


def GetSecretKey(*args):
    global SECRETS # 시크릿 키
    global ORACLECLOUD_MYSQL_DATABASE_URL
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
    global BASE_PATH
    

    SECRETS = ''

    # 현재 스크립트 파일의 절대 경로 가져오기
    script_path = os.path.abspath(__file__)

    # 프로젝트 루트 디렉토리까지 올라가기
    PROJECT_ROOT = script_path
    while not os.path.isfile(os.path.join(PROJECT_ROOT, 'main.py')):
        PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

    # print('PROJECT_ROOT', PROJECT_ROOT)
    # TODO 로컬, 서버 구별 추가 필요 => heroku
    if os.path.isfile(os.path.join(PROJECT_ROOT, 'secrets.json')): # 로컬 개발 환경
        with open((os.path.join(PROJECT_ROOT, 'secrets.json'))) as f:
            SECRETS = json.loads(f.read())

    #SECRETS = ''
    #print(os.getcwd())
    #if os.path.isfile(os.path.join(os.getcwd(), 'secrets.json')): # 로컬 개발 환경
    #    with open("secrets.json") as f:
    #        SECRETS = json.loads(f.read())        
        ORACLECLOUD_MYSQL_DATABASE_URL              =   SECRETS['ORACLECLOUD_MYSQL_DATABASE_URL'] 
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
        # IS_DEV                                      =   True
    # else: # 서버 배포 환경(heroku)
    #     TELEGRAM_BOT_INFO                           =   os.environ.get('TELEGRAM_BOT_INFO')
    #     TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   os.environ.get('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
    #     TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   os.environ.get('TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET')
    #     TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
    #     TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')
    #     TELEGRAM_CHANNEL_ID_ITOOZA                  =   os.environ.get('TELEGRAM_CHANNEL_ID_ITOOZA')
    #     TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   os.environ.get('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
    #     TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   os.environ.get('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
    #     TELEGRAM_CHANNEL_ID_TODAY_REPORT            =   os.environ.get('TELEGRAM_CHANNEL_ID_TODAY_REPORT')
    #     TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN         =   os.environ.get('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
    #     TELEGRAM_CHANNEL_ID_TEST                    =   os.environ.get('TELEGRAM_CHANNEL_ID_TEST')
    #     TELEGRAM_USER_ID_DEV                        =   os.environ.get('TELEGRAM_USER_ID_DEV')
    #     IS_DEV                                      =   False

    # print(SECRETS)


class SecretKey:
    SECRETS = GetSecretKey()
    def __init__(self):
        self.SECRETS                                     = ""   # 시크릿 키
        # self.CLEARDB_DATABASE_URL                        = ""
        self.ORACLECLOUD_MYSQL_DATABASE_URL              = SECRETS['ORACLECLOUD_MYSQL_DATABASE_URL']
        self.TELEGRAM_BOT_INFO                           = SECRETS['TELEGRAM_BOT_INFO']
        self.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      = SECRETS['TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET']
        self.TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     = SECRETS['TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET']
        self.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         = SECRETS['TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS']
        self.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          = SECRETS['TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS']
        self.TELEGRAM_CHANNEL_ID_ITOOZA                  = SECRETS['TELEGRAM_CHANNEL_ID_ITOOZA']
        self.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            = SECRETS['TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT']
        self.TELEGRAM_CHANNEL_ID_REPORT_ALARM            = SECRETS['TELEGRAM_CHANNEL_ID_REPORT_ALARM']
        self.TELEGRAM_CHANNEL_ID_TODAY_REPORT            = SECRETS['TELEGRAM_CHANNEL_ID_TODAY_REPORT']
        self.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN         = SECRETS['TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN']
        self.TELEGRAM_CHANNEL_ID_TEST                    = SECRETS['TELEGRAM_CHANNEL_ID_TEST']
        self.TELEGRAM_USER_ID_DEV                        = SECRETS['TELEGRAM_USER_ID_DEV']
        self.IS_DEV                                      = ""

    def PrintSecretKeyInfo(*args):
        SECRETS = GetSecretKey()
        print(SECRETS)
