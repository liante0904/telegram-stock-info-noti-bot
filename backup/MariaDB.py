import pymysql
from urllib.parse import urlparse

class MariaDB:
    def __init__(self, db_url):
        self.db_url = urlparse(db_url)
        self.conn = None
        self.cursor = None

    def open_connect(self):
        try:
            self.conn = pymysql.connect(
                host=self.db_url.hostname,
                user=self.db_url.username,
                password=self.db_url.password,
                charset='utf8',
                db=self.db_url.path.replace('/', ''),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            self.cursor = self.conn.cursor()
        except Exception as e:
            print("MySQL 데이터베이스 연결 실패:", e)
            self.conn = None
            self.cursor = None

    def close_connect(self):
        if self.conn:
            self.conn.close()

    def SelNxtKey(self, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
        query = """
            SELECT FIRM_NM, BOARD_NM, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, BOARD_URL, 
                   NXT_KEY, NXT_KEY_BF, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, 
                   TODAY_SEND_YN, TIMESTAMPDIFF(second, CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 
            FROM NXT_KEY
            WHERE SEC_FIRM_ORDER = %s AND ARTICLE_BOARD_ORDER = %s
        """
        self.cursor.execute(query, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
        return self.cursor.fetchone()

    def InsNxtKey(self, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY):
        query = """
            INSERT INTO NXT_KEY (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, CHANGE_DATE_TIME)
            VALUES (%s, %s, %s, DEFAULT)
        """
        self.cursor.execute(query, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY))
        self.conn.commit()

    def UpdNxtKey(self, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE):
        query = """
            UPDATE NXT_KEY SET NXT_KEY = %s, NXT_KEY_ARTICLE_TITLE = %s 
            WHERE SEC_FIRM_ORDER = %s AND ARTICLE_BOARD_ORDER = %s
        """
        self.cursor.execute(query, (FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
        self.conn.commit()

    def UpdTodaySendKey(self, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, TODAY_SEND_YN):
        query = """
            UPDATE NXT_KEY SET TODAY_SEND_YN = %s 
            WHERE SEC_FIRM_ORDER = %s AND ARTICLE_BOARD_ORDER = %s
        """
        self.cursor.execute(query, (TODAY_SEND_YN, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
        self.conn.commit()
