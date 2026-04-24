import os
from loguru import logger
from models.ConfigManager import config

class MetaFirmInfo(type):
    """FirmInfo 클래스 레벨의 프로퍼티(firm_names 등)를 지원하기 위한 메타클래스"""
    @property
    def firm_names(cls):
        if not cls._is_loaded:
            cls.load_data_from_db()
        # 키(SEC_FIRM_ORDER) 순으로 정렬된 FIRM_NM 리스트 반환
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
    def reload(cls):
        """캐시를 버리고 DB에서 다시 로드."""
        cls._is_loaded = False
        cls._firm_data = {}
        cls._board_data = {}
        cls.load_data_from_db()

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
                cur.execute('SELECT "SEC_FIRM_ORDER","FIRM_NM","TELEGRAM_UPDATE_YN" FROM "TBM_SEC_FIRM_INFO" ORDER BY "SEC_FIRM_ORDER"')
                for row in cur.fetchall():
                    cls._firm_data[row['SEC_FIRM_ORDER']] = {
                        "name": row['FIRM_NM'],
                        "update_required": row['TELEGRAM_UPDATE_YN'] == 'Y'
                    }
                cur.execute('SELECT "SEC_FIRM_ORDER","ARTICLE_BOARD_ORDER","BOARD_NM","BOARD_CD","LABEL_NM" FROM "TBM_SEC_FIRM_BOARD_INFO"')
                for row in cur.fetchall():
                    cls._board_data[(row['SEC_FIRM_ORDER'], row['ARTICLE_BOARD_ORDER'])] = {
                        "name": row['BOARD_NM'],
                        "code": row['BOARD_CD'] or "",
                        "label": row['LABEL_NM'] or ""
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

            cursor.execute("SELECT SEC_FIRM_ORDER, FIRM_NM, TELEGRAM_UPDATE_YN FROM TBM_SEC_FIRM_INFO ORDER BY SEC_FIRM_ORDER")
            for row in cursor.fetchall():
                cls._firm_data[row['SEC_FIRM_ORDER']] = {
                    "name": row['FIRM_NM'],
                    "update_required": row['TELEGRAM_UPDATE_YN'] == 'Y'
                }

            cursor.execute("SELECT SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, BOARD_NM, BOARD_CD, LABEL_NM FROM TBM_SEC_FIRM_BOARD_INFO")
            for row in cursor.fetchall():
                cls._board_data[(row['SEC_FIRM_ORDER'], row['ARTICLE_BOARD_ORDER'])] = {
                    "name": row['BOARD_NM'],
                    "code": row['BOARD_CD'] or "",
                    "label": row['LABEL_NM'] or ""
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
            self.SEC_FIRM_ORDER = firm_info.SEC_FIRM_ORDER
            self.ARTICLE_BOARD_ORDER = firm_info.ARTICLE_BOARD_ORDER
        else:
            self.SEC_FIRM_ORDER = sec_firm_order
            self.ARTICLE_BOARD_ORDER = article_board_order

        firm_info_cached = self._firm_data.get(self.SEC_FIRM_ORDER, {})
        self.telegram_update_required = firm_info_cached.get("update_required", False)

    def get_firm_name(self):
        cached = self._firm_data.get(self.SEC_FIRM_ORDER, {}).get("name")
        if cached:
            return cached
        # 캐시 miss → DB에서 단건 조회 후 캐시 갱신
        name = self._fetch_firm_name_from_db(self.SEC_FIRM_ORDER)
        if name:
            self._firm_data.setdefault(self.SEC_FIRM_ORDER, {})["name"] = name
            return name
        return f"Unknown({self.SEC_FIRM_ORDER})"

    @classmethod
    def _fetch_firm_name_from_db(cls, sec_firm_order: int):
        backend = os.getenv("DB_BACKEND", "sqlite").lower()
        try:
            if backend == "postgres":
                import psycopg2
                conn = psycopg2.connect(
                    host=os.getenv("POSTGRES_HOST", "localhost"),
                    port=os.getenv("POSTGRES_PORT", "5432"),
                    dbname=os.getenv("POSTGRES_DB", "ssh_reports_hub"),
                    user=os.getenv("POSTGRES_USER", "ssh_reports_hub"),
                    password=os.getenv("POSTGRES_PASSWORD", ""),
                )
                with conn.cursor() as cur:
                    cur.execute('SELECT "FIRM_NM" FROM "TBM_SEC_FIRM_INFO" WHERE "SEC_FIRM_ORDER" = %s', (sec_firm_order,))
                    row = cur.fetchone()
                conn.close()
            else:
                import sqlite3
                conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
                cur = conn.cursor()
                cur.execute("SELECT FIRM_NM FROM TBM_SEC_FIRM_INFO WHERE SEC_FIRM_ORDER = ?", (sec_firm_order,))
                row = cur.fetchone()
                conn.close()
            if row:
                logger.debug(f"FirmInfo: fallback DB lookup SEC_FIRM_ORDER={sec_firm_order} → {row[0]}")
                return row[0]
        except Exception as e:
            logger.error(f"FirmInfo: fallback lookup failed for SEC_FIRM_ORDER={sec_firm_order}: {e}")
        return None

    def get_board_name(self):
        key = (self.SEC_FIRM_ORDER, self.ARTICLE_BOARD_ORDER)
        return self._board_data.get(key, {}).get("name", "")

    def get_board_code(self):
        key = (self.SEC_FIRM_ORDER, self.ARTICLE_BOARD_ORDER)
        return self._board_data.get(key, {}).get("code", "")

    def get_label_name(self):
        key = (self.SEC_FIRM_ORDER, self.ARTICLE_BOARD_ORDER)
        return self._board_data.get(key, {}).get("label", "")

    def set_sec_firm_order(self, sec_firm_order):
        self.SEC_FIRM_ORDER = sec_firm_order
        self.telegram_update_required = self._firm_data.get(self.SEC_FIRM_ORDER, {}).get("update_required", False)

    def set_article_board_order(self, article_board_order):
        self.ARTICLE_BOARD_ORDER = article_board_order

    def get_state(self):
        return {
            "SEC_FIRM_ORDER": self.SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER": self.ARTICLE_BOARD_ORDER,
            "FIRM_NAME": self.get_firm_name(),
            "BOARD_NAME": self.get_board_name(),
            "LABEL_NAME": self.get_label_name(),
            "TELEGRAM_UPDATE_REQUIRED": self.telegram_update_required
        }

if __name__ == "__main__":
    print(f"Total firm names: {len(FirmInfo.firm_names)}")
    test_info = FirmInfo(sec_firm_order=27, article_board_order=0)
    print(f"Instance State: {test_info.get_state()}")
