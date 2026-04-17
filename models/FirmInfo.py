import sqlite3
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
    def load_data_from_db(cls):
        if cls._is_loaded:
            return

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
            logger.error(f"FirmInfo Error: Failed to load data from DB ({db_path}): {e}")

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
        return self._firm_data.get(self.SEC_FIRM_ORDER, {}).get("name", f"Unknown({self.SEC_FIRM_ORDER})")

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
