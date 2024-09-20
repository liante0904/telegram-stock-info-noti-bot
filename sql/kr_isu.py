import sqlite3
import os
import argparse
from datetime import datetime

# 데이터베이스 파일 경로
db_path = os.path.expanduser('~/sqlite3/telegram.db')

# SQLite 데이터베이스 연결
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 명령행 인자 파서 설정
parser = argparse.ArgumentParser(description="SQLite STOCK_INFO_MASTER_KR_ISU Table Management Script")
parser.add_argument('action', choices=['create', 'insert', 'select', 'update', 'delete', 'drop'], help="Action to perform")
parser.add_argument('--isu_no', help="6자리 종목 코드")
parser.add_argument('--isu_nm', help="40자리 종목명")
parser.add_argument('--market', help="시장 종류 (KOSPI, KOSDAQ)")
parser.add_argument('--sector', help="업종")
parser.add_argument('--date', help="조회할 날짜 (YYYYMMDD, YYMMDD, YYYY-MM-DD)")
args = parser.parse_args()

def drop_table():
    """STOCK_INFO_MASTER_KR_ISU 테이블을 삭제합니다."""
    cursor.execute("DROP TABLE IF EXISTS STOCK_INFO_MASTER_KR_ISU")
    conn.commit()
    print("Table STOCK_INFO_MASTER_KR_ISU dropped successfully.")

def create_table():
    """STOCK_INFO_MASTER_KR_ISU 테이블을 생성합니다."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS STOCK_INFO_MASTER_KR_ISU (
            ISU_NO TEXT(6) UNIQUE,           -- 6자리 종목 코드 (유니크 설정)
            ISU_NM TEXT(40) PRIMARY KEY,     -- 40자리 종목명 (PRIMARY KEY로 설정)
            MARKET TEXT NOT NULL,            -- 시장 종류 (KOSPI, KOSDAQ)
            SECTOR TEXT,                     -- 업종
            LAST_UPDATED DATETIME DEFAULT CURRENT_TIMESTAMP  -- 마지막 업데이트 시점
        )
    """)
    conn.commit()
    print("Table STOCK_INFO_MASTER_KR_ISU created with ISU_NM as primary key.")


def insert_data(isu_no, isu_nm, market, sector):
    """STOCK_INFO_MASTER_KR_ISU 테이블에 데이터를 삽입합니다."""
    cursor.execute("""
        INSERT INTO STOCK_INFO_MASTER_KR_ISU (ISU_NO, ISU_NM, MARKET, SECTOR) 
        VALUES (?, ?, ?, ?)
    """, (isu_no, isu_nm, market, sector))
    conn.commit()
    print(f"Data inserted: {isu_no}, {isu_nm}, {market}, {sector}")

def select_data(isu_no=None, date=None):
    """STOCK_INFO_MASTER_KR_ISU 테이블에서 데이터를 조회합니다."""
    query = "SELECT ISU_NO, ISU_NM, MARKET, SECTOR, LAST_UPDATED FROM STOCK_INFO_MASTER_KR_ISU"
    params = []

    if isu_no:
        query += " WHERE ISU_NO = ?"
        params.append(isu_no)
    elif date:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            if len(date) == 8:  # YYYYMMDD
                date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')
            elif len(date) == 6:  # YYMMDD
                date = datetime.strptime(date, '%y%m%d').strftime('%Y-%m-%d')
            else:
                raise ValueError("Invalid date format. Use 'YYYYMMDD', 'YYMMDD', or 'YYYY-MM-DD'.")
        query += " WHERE DATE(LAST_UPDATED) = ?"
        params.append(date)
    
    cursor.execute(query, params)
    results = cursor.fetchall()

    print("\nFetched Data:")
    for row in results:
        print(row)

def update_data(isu_no, isu_nm=None, market=None, sector=None):
    """STOCK_INFO_MASTER_KR_ISU 테이블의 데이터를 업데이트합니다."""
    if not isu_no:
        raise ValueError("ISU_NO is required for update operation.")

    updates = []
    params = []

    if isu_nm:
        updates.append("ISU_NM = ?")
        params.append(isu_nm)
    if market:
        updates.append("MARKET = ?")
        params.append(market)
    if sector:
        updates.append("SECTOR = ?")
        params.append(sector)

    params.append(isu_no)

    if not updates:
        print("No fields to update.")
        return

    query = f"UPDATE STOCK_INFO_MASTER_KR_ISU SET {', '.join(updates)}, LAST_UPDATED = CURRENT_TIMESTAMP WHERE ISU_NO = ?"
    cursor.execute(query, params)
    conn.commit()
    print(f"Data updated for ISU_NO: {isu_no}")

def delete_data(isu_no):
    """STOCK_INFO_MASTER_KR_ISU 테이블에서 데이터를 삭제합니다."""
    cursor.execute("DELETE FROM STOCK_INFO_MASTER_KR_ISU WHERE ISU_NO = ?", (isu_no,))
    conn.commit()
    print(f"Data deleted for ISU_NO: {isu_no}")

if __name__ == "__main__":
    if args.action == 'create':
        create_table()
    elif args.action == 'insert':
        if not (args.isu_no and args.isu_nm and args.market):
            raise ValueError("ISU_NO, ISU_NM, and MARKET are required for insert operation.")
        insert_data(args.isu_no, args.isu_nm, args.market, args.sector)
    elif args.action == 'select':
        select_data(args.isu_no, args.date)
    elif args.action == 'update':
        if not args.isu_no:
            raise ValueError("ISU_NO is required for update operation.")
        update_data(args.isu_no, args.isu_nm, args.market, args.sector)
    elif args.action == 'delete':
        if not args.isu_no:
            raise ValueError("ISU_NO is required for delete operation.")
        delete_data(args.isu_no)
    elif args.action == 'drop':
        drop_table()
    
    conn.close()
