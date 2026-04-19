import asyncio
import os
import sys
from loguru import logger
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.SQLiteManager import SQLiteManager
from models.PostgreSQLManager import PostgreSQLManager

async def compare_sqlite_and_postgres():
    """
    SQLite와 PostgreSQL의 데이터를 전수 비교합니다.
    """
    load_dotenv(override=True)
    logger.info("Starting Full DB Comparison (SQLite vs PostgreSQL)...")

    # 1. DB 매니저 초기화
    sqlite_db = SQLiteManager()
    postgres_db = PostgreSQLManager()

    # 2. 데이터 가져오기 (전체)
    logger.info("Fetching data from SQLite...")
    sqlite_db.open_connection()
    try:
        sqlite_rows = sqlite_db.fetch_all(sqlite_db.main_table_name)
    finally:
        sqlite_db.close_connection()
    
    logger.info("Fetching data from PostgreSQL...")
    # _fetchall은 일반 함수(def)이므로 await를 붙이지 않습니다.
    postgres_rows = postgres_db._fetchall(f'SELECT * FROM {postgres_db.main_table_name}')

    # 3. 전체 건수 비교
    sqlite_count = len(sqlite_rows)
    postgres_count = len(postgres_rows)
    
    logger.info(f"Summary: SQLite ({sqlite_count} rows) | PostgreSQL ({postgres_count} rows)")

    # 4. KEY 기준 매핑
    sqlite_dict = {row['KEY']: row for row in sqlite_rows if row.get('KEY')}
    postgres_dict = {row['KEY']: row for row in postgres_rows if row.get('KEY')}

    # 5. 유실된 데이터 확인
    sqlite_keys = set(sqlite_dict.keys())
    postgres_keys = set(postgres_dict.keys())

    missing_in_pg = sqlite_keys - postgres_keys
    missing_in_sqlite = postgres_keys - sqlite_keys

    logger.info("====================================================")
    if not missing_in_pg and not missing_in_sqlite:
        logger.success("✅ [KEY 매칭] 양쪽 DB의 레코드가 완벽하게 일치합니다.")
    else:
        if missing_in_pg:
            logger.error(f"❌ [유실] SQLite에만 있는 데이터: {len(missing_in_pg)}건")
        if missing_in_sqlite:
            logger.warning(f"⚠️ [추가] PostgreSQL에만 있는 데이터: {len(missing_in_sqlite)}건")
    
    # 6. 데이터 내용물 무작위 검증
    common_keys = list(sqlite_keys & postgres_keys)
    if common_keys:
        logger.info(f"Checking content integrity for common {len(common_keys)} records...")
        diff_count = 0
        for key in common_keys[:200]:
            s_row = sqlite_dict[key]
            p_row = postgres_dict[key]
            
            columns_to_check = ['FIRM_NM', 'ARTICLE_TITLE', 'REG_DT', 'WRITER']
            for col in columns_to_check:
                s_val = str(s_row.get(col) or '').strip()
                p_val = str(p_row.get(col) or '').strip()
                
                if s_val != p_val:
                    logger.error(f"❌ [내용 불일치] KEY: {key} | Column: {col}")
                    logger.error(f"   SQLite: {s_val}")
                    logger.error(f"   Postgres: {p_val}")
                    diff_count += 1
                    break
        
        if diff_count == 0:
            logger.success(f"✅ [내용 검증] 샘플 {min(len(common_keys), 200)}개의 데이터 내용이 완벽하게 일치합니다.")
        else:
            logger.error(f"❌ [내용 검증] {diff_count}개의 데이터에서 차이가 발견되었습니다.")

    logger.info("====================================================")

if __name__ == "__main__":
    asyncio.run(compare_sqlite_and_postgres())
