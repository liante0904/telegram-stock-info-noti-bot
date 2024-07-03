import os
import json
import sys

class SecretKey:
    def __init__(self):
        self.SECRETS = ''
        self.ORACLECLOUD_MYSQL_DATABASE_URL = None
        self.TELEGRAM_BOT_INFO = None
        self.TELEGRAM_BOT_INFO1 = None
        self.CLEARDB_DATABASE_URL = None
        self.CLEARDB_DATABASE_URL_BEFORE = None
        self.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET = None
        self.TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET = None
        self.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS = None
        self.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS = None
        self.TELEGRAM_CHANNEL_ID_ITOOZA = None
        self.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT = None
        self.TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM = None
        self.TELEGRAM_CHANNEL_ID_REPORT_ALARM = None
        self.TELEGRAM_CHANNEL_ID_DAILY_WEEKLY_REPORT_ALARM = None
        self.TELEGRAM_CHANNEL_ID_TODAY_REPORT = None
        self.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN = None
        self.TELEGRAM_CHANNEL_ID_TEST = None
        self.TELEGRAM_USER_ID_DEV = None
        self.IS_DEV = False
        self.BASE_PATH = ''

    def load_secrets(self):
        main_module_path = sys.modules['__main__'].__file__
        main_module_path = os.path.abspath(main_module_path)
        self.BASE_PATH = os.path.dirname(main_module_path)
        print('BASE_PATH', self.BASE_PATH)

        if os.path.isfile(os.path.join(self.BASE_PATH, 'secrets.json')):
            # 로컬 개발 환경
            with open(os.path.join(self.BASE_PATH, 'secrets.json')) as f:
                self.SECRETS = json.loads(f.read())
                self._load_secrets_from_file()
                self.IS_DEV = True
        else:
            # 서버 배포 환경 (예: Heroku)
            self._load_secrets_from_env()
            self.IS_DEV = False

    def _load_secrets_from_file(self):
        self.ORACLECLOUD_MYSQL_DATABASE_URL = self.SECRETS.get('ORACLECLOUD_MYSQL_DATABASE_URL')
        self.TELEGRAM_BOT_INFO = self.SECRETS.get('TELEGRAM_BOT_INFO')
        self.TELEGRAM_BOT_INFO1 = self.SECRETS.get('TELEGRAM_BOT_INFO1')
        self.CLEARDB_DATABASE_URL = self.SECRETS.get('CLEARDB_DATABASE_URL')
        self.CLEARDB_DATABASE_URL_BEFORE = self.SECRETS.get('CLEARDB_DATABASE_URL_BEFORE')
        self.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET = self.SECRETS.get('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
        self.TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET = self.SECRETS.get('TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET')
        self.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS = self.SECRETS.get('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
        self.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS = self.SECRETS.get('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')
        self.TELEGRAM_CHANNEL_ID_ITOOZA = self.SECRETS.get('TELEGRAM_CHANNEL_ID_ITOOZA')
        self.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT = self.SECRETS.get('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
        self.TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM = self.SECRETS.get('TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_REPORT_ALARM = self.SECRETS.get('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_DAILY_WEEKLY_REPORT_ALARM = self.SECRETS.get('TELEGRAM_CHANNEL_ID_DAILY_WEEKLY_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_TODAY_REPORT = self.SECRETS.get('TELEGRAM_CHANNEL_ID_TODAY_REPORT')
        self.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN = self.SECRETS.get('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
        self.TELEGRAM_CHANNEL_ID_TEST = self.SECRETS.get('TELEGRAM_CHANNEL_ID_TEST')
        self.TELEGRAM_USER_ID_DEV = self.SECRETS.get('TELEGRAM_USER_ID_DEV')

    def _load_secrets_from_env(self):
        self.ORACLECLOUD_MYSQL_DATABASE_URL = os.environ.get('ORACLECLOUD_MYSQL_DATABASE_URL')
        self.TELEGRAM_BOT_INFO = os.environ.get('TELEGRAM_BOT_INFO')
        self.TELEGRAM_BOT_INFO1 = os.environ.get('TELEGRAM_BOT_INFO1')
        self.CLEARDB_DATABASE_URL = os.environ.get('CLEARDB_DATABASE_URL')
        self.CLEARDB_DATABASE_URL_BEFORE = os.environ.get('CLEARDB_DATABASE_URL_BEFORE')
        self.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET = os.environ.get('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
        self.TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET = os.environ.get('TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET')
        self.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS = os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
        self.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS = os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')
        self.TELEGRAM_CHANNEL_ID_ITOOZA = os.environ.get('TELEGRAM_CHANNEL_ID_ITOOZA')
        self.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT = os.environ.get('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
        self.TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM = os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.environ.get('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_DAILY_WEEKLY_REPORT_ALARM = os.environ.get('TELEGRAM_CHANNEL_ID_DAILY_WEEKLY_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_TODAY_REPORT = os.environ.get('TELEGRAM_CHANNEL_ID_TODAY_REPORT')
        self.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN = os.environ.get('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
        self.TELEGRAM_CHANNEL_ID_TEST = os.environ.get('TELEGRAM_CHANNEL_ID_TEST')
        self.TELEGRAM_USER_ID_DEV = os.environ.get('TELEGRAM_USER_ID_DEV')
