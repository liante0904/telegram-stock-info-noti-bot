import pymysql
from urllib.parse import urlparse

class DatabaseManager:
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
            print("Connected to the database")
        except Exception as e:
            print("MySQL 데이터베이스 연결 실패:", e)
            self.conn = None
            self.cursor = None

    def close_connect(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed")

    def execute_select_query(self, query, params=None):
        result = None
        if self.conn and self.cursor:
            try:
                self.cursor.execute(query, params)
                result = self.cursor.fetchall()
            except Exception as e:
                print("Error executing SELECT query:", e)
        return result

    def execute_insert_query(self, query, values):
        if self.conn and self.cursor:
            try:
                self.cursor.execute(query, values)
            except Exception as e:
                print("Error executing INSERT query:", e)
