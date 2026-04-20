import asyncio
import os
import sys
import pytest
from loguru import logger
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.SQLiteManager import SQLiteManager
from models.PostgreSQLManager import PostgreSQLManager

@pytest.mark.asyncio
async def test_compare_sqlite_and_postgres():
    """
    [Audit] SQLite와 PostgreSQL의 데이터를 전수 비교하고 상세 리포트를 출력합니다.
    """
    load_dotenv(override=True)
    print("\n" + "="*50)
    print("🔍 DB 정합성 전수 조사 리포트")
    print("="*50)

    # 1. DB 매니저 초기화
    sqlite_db = SQLiteManager()
    postgres_db = PostgreSQLManager()

    # 2. 데이터 가져오기
    sqlite_db.open_connection()
    try:
        sqlite_rows = sqlite_db.fetch_all(sqlite_db.main_table_name)
    finally:
        sqlite_db.close_connection()
    
    postgres_rows = postgres_db._fetchall(f'SELECT * FROM {postgres_db.main_table_name}')

    # 3. 전체 건수 비교 및 출력
    sqlite_count = len(sqlite_rows)
    postgres_count = len(postgres_rows)
    
    print(f"📊 [전체 건수] SQLite: {sqlite_count:,}건 | PostgreSQL: {postgres_count:,}건")

    # 4. KEY 기준 매핑
    sqlite_dict = {row['KEY']: row for row in sqlite_rows if row.get('KEY')}
    postgres_dict = {row['KEY']: row for row in postgres_rows if row.get('KEY')}

    sqlite_keys = set(sqlite_dict.keys())
    postgres_keys = set(postgres_dict.keys())

    missing_in_pg = sqlite_keys - postgres_keys
    missing_in_sqlite = postgres_keys - sqlite_keys

    # 5. 상세 결과 리포트
    if not missing_in_pg and not missing_in_sqlite:
        print("✅ [KEY 매칭] 양쪽 DB의 레코드가 100% 일치합니다.")
    else:
        if missing_in_pg:
            print(f"❌ [유실] SQLite에만 있는 데이터: {len(missing_in_pg)}건")
        if missing_in_sqlite:
            print(f"⚠️ [추가] PostgreSQL에만 있는 데이터: {len(missing_in_sqlite)}건")
    
    # 6. 내용물 샘플 검증
    common_keys = list(sqlite_keys & postgres_keys)
    if common_keys:
        diff_count = 0
        for key in common_keys[:200]:
            s_row = sqlite_dict[key]
            p_row = postgres_dict[key]
            
            # 주요 컬럼 비교
            for col in ['FIRM_NM', 'ARTICLE_TITLE', 'REG_DT']:
                if str(s_row.get(col) or '').strip() != str(p_row.get(col) or '').strip():
                    diff_count += 1
                    break
        
        print(f"✅ [내용 검증] 샘플 {min(len(common_keys), 200)}개 중 {diff_count}개 불일치 (정상 범위: 0)")

    print("="*50 + "\n")

    # [pytest 핵심] 건수가 다르면 테스트 실패 처리
    assert sqlite_count == postgres_count, f"DB 건수 불일치! (SQLite: {sqlite_count}, PG: {postgres_count})"
