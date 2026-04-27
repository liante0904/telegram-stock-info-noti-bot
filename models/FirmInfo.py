import os
from loguru import logger
from models.ConfigManager import config

class MetaFirmInfo(type):
    """FirmInfo 클래스 레벨의 프로퍼티(firm_names 등)를 지원하기 위한 메타클래스"""
    @property
    def firm_names(cls):
        if not cls._is_loaded:
            cls.load_data_from_db()
        # 키(sec_firm_order) 순으로 정렬된 firm_nm 리스트 반환
        max_order = max(cls._firm_data.keys()) if cls._firm_data else -1
        names = []
        for i in range(max_order + 1):
            names.append(cls._firm_data.get(i, {}).get("name", f"Unknown({i})"))
        return names

class FirmInfo(metaclass=MetaFirmInfo):
    """
    증권사 및 게시판 정보를 관리하는 클래스.
    데이터(DB 정보)는 클래스 수준에서 한 번만 로드하여 모든 인스턴스가 공유합니다. (데이터 싱글톤)
    """
    _firm_data = {}
    _board_data = {}
    _is_loaded = False

    @classmethod
    def load_data_from_db(cls):
        if cls._is_loaded:
            return

        backend = os.getenv("DB_BACKEND", "sqlite").lower()
        if backend == "postgres":
            cls._load_from_postgres()
        else:
            cls._load_from_sqlite()

    @classmethod
    def _load_from_postgres(cls):
        try:
            import psycopg2
            import psycopg2.extras
            from dotenv import load_dotenv
            load_dotenv(override=True)
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                dbname=os.getenv("POSTGRES_DB", "ssh_reports_hub"),
                user=os.getenv("POSTGRES_USER", "ssh_reports_hub"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
            )
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute('SELECT sec_firm_order, firm_nm, telegram_update_yn FROM tbm_sec_firm_info ORDER BY sec_firm_order')
                for row in cur.fetchall():
                    cls._firm_data[row['sec_firm_order']] = {
                        "name": row['firm_nm'],
                        "update_required": row['telegram_update_yn'] == 'Y'
                    }
                cur.execute('SELECT sec_firm_order, article_board_order, board_nm, board_cd, label_nm FROM tbm_sec_firm_board_info')
                for row in cur.fetchall():
                    cls._board_data[(row['sec_firm_order'], row['article_board_order'])] = {
                        "name": row['board_nm'],
                        "code": row['board_cd'] or "",
                        "label": row['label_nm'] or ""
                    }
            conn.close()
            cls._is_loaded = True
            logger.debug("FirmInfo: Data successfully loaded from PostgreSQL.")
        except Exception as e:
            logger.error(f"FirmInfo Error: Failed to load data from PostgreSQL: {e}")

    @classmethod
    def _load_from_sqlite(cls):
        import sqlite3
        db_path = config.DB_PATH
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT sec_firm_order, firm_nm, telegram_update_yn FROM tbm_sec_firm_info ORDER BY sec_firm_order")
            for row in cursor.fetchall():
                cls._firm_data[row['sec_firm_order']] = {
                    "name": row['firm_nm'],
                    "update_required": row['telegram_update_yn'] == 'Y'
                }

            cursor.execute("SELECT sec_firm_order, article_board_order, board_nm, board_cd, label_nm FROM tbm_sec_firm_board_info")
            for row in cursor.fetchall():
                cls._board_data[(row['sec_firm_order'], row['article_board_order'])] = {
                    "name": row['board_nm'],
                    "code": row['board_cd'] or "",
                    "label": row['label_nm'] or ""
                }
            cls._is_loaded = True
            logger.debug(f"FirmInfo: Data successfully loaded from SQLite ({db_path}).")
            conn.close()
        except Exception as e:
            logger.error(f"FirmInfo Error: Failed to load data from SQLite ({db_path}): {e}")

    def __init__(self, sec_firm_order=0, article_board_order=0, firm_info=None):
        if not self._is_loaded:
            self.load_data_from_db()

        if firm_info:
            self.sec_firm_order = firm_info.sec_firm_order
            self.article_board_order = firm_info.article_board_order
        else:
            self.sec_firm_order = sec_firm_order
            self.article_board_order = article_board_order

        firm_info_cached = self._firm_data.get(self.sec_firm_order, {})
        self.telegram_update_required = firm_info_cached.get("update_required", False)

    def get_firm_name(self):
        return self._firm_data.get(self.sec_firm_order, {}).get("name", f"Unknown({self.sec_firm_order})")

    def get_board_name(self):
        key = (self.sec_firm_order, self.article_board_order)
        return self._board_data.get(key, {}).get("name", "")

    def get_board_code(self):
        key = (self.sec_firm_order, self.article_board_order)
        return self._board_data.get(key, {}).get("code", "")

    def get_label_name(self):
        key = (self.sec_firm_order, self.article_board_order)
        return self._board_data.get(key, {}).get("label", "")

    def set_sec_firm_order(self, sec_firm_order):
        self.sec_firm_order = sec_firm_order
        self.telegram_update_required = self._firm_data.get(self.sec_firm_order, {}).get("update_required", False)

    def set_article_board_order(self, article_board_order):
        self.article_board_order = article_board_order

    def get_state(self):
        return {
            "sec_firm_order": self.sec_firm_order,
            "article_board_order": self.article_board_order,
            "FIRM_NAME": self.get_firm_name(),
            "BOARD_NAME": self.get_board_name(),
            "LABEL_NAME": self.get_label_name(),
            "TELEGRAM_UPDATE_REQUIRED": self.telegram_update_required
        }

if __name__ == "__main__":
    print(f"Total firm names: {len(FirmInfo.firm_names)}")
    test_info = FirmInfo(sec_firm_order=27, article_board_order=0)
    print(f"Instance State: {test_info.get_state()}")
