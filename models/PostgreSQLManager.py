import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

class PostgreSQLManager:
    def __init__(self):
        load_dotenv()
        self.host = os.getenv('POSTGRES_HOST')
        self.port = os.getenv('POSTGRES_PORT', '5432')
        self.database = os.getenv('POSTGRES_DB')
        self.user = os.getenv('POSTGRES_USER')
        self.password = os.getenv('POSTGRES_PASSWORD')

    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )

    def load_keywords_from_db(self):
        """
        PostgreSQL에서 활성화된 키워드 정보를 가져와 기존 JSON 구조와 호환되는 dict 형태로 반환합니다.
        구조: { "user_id": [ { "keyword": "...", "code": "", "timestamp": "ISO_FORMAT" } ] }
        """
        conn = None
        try:
            conn = self.get_connection()
            # RealDictCursor를 사용하여 결과를 딕셔너리 형태로 받습니다.
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                SELECT user_id, keyword, created_at
                FROM "REPORT_ALERT_KEYWORDS"
                WHERE is_active = true
                ORDER BY user_id, created_at ASC;
                """
                cur.execute(query)
                rows = cur.fetchall()

            user_keywords = {}
            for row in rows:
                user_id = str(row['user_id'])
                keyword = row['keyword']
                # created_at이 Unix Timestamp(int/float)인 경우와 datetime 객체인 경우 모두 대응
                created_at = row['created_at']
                
                if isinstance(created_at, (int, float)):
                    timestamp_iso = datetime.fromtimestamp(created_at).isoformat()
                elif isinstance(created_at, datetime):
                    timestamp_iso = created_at.isoformat()
                else:
                    # 기타 경우 현재 시간으로 대체 (안전책)
                    timestamp_iso = datetime.now().isoformat()

                keyword_obj = {
                    "keyword": keyword,
                    "code": "",
                    "timestamp": timestamp_iso
                }

                if user_id not in user_keywords:
                    user_keywords[user_id] = []
                user_keywords[user_id].append(keyword_obj)

            return user_keywords

        except Exception as e:
            print(f"Error loading keywords from PostgreSQL: {e}")
            return {}
        finally:
            if conn:
                conn.close()
