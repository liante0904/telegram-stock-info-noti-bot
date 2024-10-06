import os
from dotenv import load_dotenv


# 현재 파일 기준으로 상위 디렉토리에 있는 .env 파일 경로 설정
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path=env_path)

# 환경 변수 사용
env = os.getenv('ENV')

class SecretKey:
    def __init__(self):
        load_dotenv()  # .env 파일의 환경 변수를 로드합니다
        
        # 기본 경로 변수들
        self.BASE_PATH = os.getenv('BASE_PATH', '')  
        self.PROJECT_DIR = os.getenv('PROJECT_DIR', '')
        self.HOME_DIR = os.getenv('HOME_DIR', '')
        self.JSON_DIR = os.getenv('JSON_DIR', '')

        # 데이터베이스 URL
        self.ORACLECLOUD_MYSQL_DATABASE_URL = os.getenv('ORACLECLOUD_MYSQL_DATABASE_URL')
        self.CLEARDB_DATABASE_URL = os.getenv('CLEARDB_DATABASE_URL')
        self.CLEARDB_DATABASE_URL_BEFORE = os.getenv('CLEARDB_DATABASE_URL_BEFORE')

        # Telegram 봇 정보
        self.TELEGRAM_BOT_INFO = os.getenv('TELEGRAM_BOT_INFO')
        self.TELEGRAM_BOT_INFO1 = os.getenv('TELEGRAM_BOT_INFO1')

        # Telegram 봇 토큰 및 채널 ID
        self.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
        self.TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET = os.getenv('TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET')
        self.TELEGRAM_BOT_TOKEN_PROD = os.getenv('TELEGRAM_BOT_TOKEN_PROD')

        # Telegram 채널 ID
        self.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS = os.getenv('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
        self.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS = os.getenv('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')
        self.TELEGRAM_CHANNEL_ID_ITOOZA = os.getenv('TELEGRAM_CHANNEL_ID_ITOOZA')
        self.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT = os.getenv('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
        self.TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_DAILY_WEEKLY_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_DAILY_WEEKLY_REPORT_ALARM')
        self.TELEGRAM_CHANNEL_ID_TODAY_REPORT = os.getenv('TELEGRAM_CHANNEL_ID_TODAY_REPORT')
        self.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN = os.getenv('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
        self.TELEGRAM_CHANNEL_ID_TEST = os.getenv('TELEGRAM_CHANNEL_ID_TEST')

        # 개발자 Telegram ID
        self.TELEGRAM_USER_ID_DEV = os.getenv('TELEGRAM_USER_ID_DEV')


    def print_env_info(self):
        print(f"환경: {'개발' if self.IS_DEV else '프로덕션'}")
        print(f"BASE_PATH: {self.BASE_PATH}")
        print(f"PROJECT_DIR: {self.PROJECT_DIR}")
        print(f"HOME_DIR: {self.HOME_DIR}")
        print(f"JSON_DIR: {self.JSON_DIR}")
        print(f"Telegram 봇 토큰: {self.TELEGRAM_BOT_TOKEN_PROD}")
