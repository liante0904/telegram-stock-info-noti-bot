import asyncio
import json
import os
import sys
from loguru import logger
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# SQLite 강제 설정
os.environ["DB_BACKEND"] = "sqlite"
load_dotenv(override=True)

from models.SQLiteManager import SQLiteManager

async def import_json_to_sqlite():
    """
    postgres_to_sqlite_sync.json 파일을 SQLite에 주입합니다.
    """
    logger.info("Starting SQLite data import (Reverse Sync)...")
    
    file_path = os.path.join(os.path.dirname(__file__), '..', 'json', 'postgres_to_sqlite_sync.json')
    
    if not os.path.exists(file_path):
        logger.error(f"Export file not found: {file_path}. Run tests/test_db_export_postgres.py first.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
        logger.info(f"Loaded {len(data_list)} records from export file.")
    except Exception as e:
        logger.error(f"Failed to load JSON file: {e}")
        return

    # SQLiteManager 사용 (insert_json_data_list 메서드가 동기 함수임을 감안)
    db = SQLiteManager()
    
    try:
        # SQLite 인서트 수행 (기존 upsert 로직 활용)
        # insert_json_data_list는 내부적으로 open_connection/close_connection을 수행함
        ins, upd = db.insert_json_data_list(data_list)
        
        logger.success("====================================================")
        logger.success(f"SQLite Sync Result (SUCCESS):")
        logger.success(f" - New records inserted: {ins}")
        logger.success(f" - Existing records updated: {upd}")
        logger.success("====================================================")
        return True

    except Exception as e:
        logger.error(f"SQLite sync failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(import_json_to_sqlite())
