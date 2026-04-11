import asyncio
import sys
import os
import sqlite3
import time
# 1. 로그 설정 (색상 강제 적용)
logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")

# 프로젝트 루트 경로 추가 (run 폴더의 상위 경로)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.LS_0 import process_article

def update_db_batch(results):
    """동기식으로 DB 배치를 업데이트하여 락 문제를 최소화함"""
    db_path = os.getenv('SQLITE_DB_PATH', os.path.expanduser('~/sqlite3/telegram.db'))
    retries = 10  # 대량 처리 시 충돌 가능성 대비 재시도 횟수 상향
    while retries > 0:
        try:
            conn = sqlite3.connect(db_path, timeout=60)
            cursor = conn.cursor()
            for res in results:
                t_url = res.get('TELEGRAM_URL', '')
                p_url = res.get('PDF_URL') or t_url
                title = res.get('ARTICLE_TITLE', '')
                r_id = res['report_id']
                
                cursor.execute("""
                    UPDATE data_main_daily_send 
                    SET TELEGRAM_URL = ?, ARTICLE_TITLE = ?, PDF_URL = ?
                    WHERE report_id = ?
                """, (t_url, title, p_url, r_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                logger.warning(f"DB Locked, retrying... ({retries} left)")
                time.sleep(3)
                retries -= 1
            else:
                raise e
    return False

async def fix_ls_all_history():
    db_path = os.getenv('SQLITE_DB_PATH', os.path.expanduser('~/sqlite3/telegram.db'))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 30일 제한 해제 및 오래된 순서(ASC)로 정렬
    sql = """
    SELECT report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, REG_DT, ARTICLE_TITLE, TELEGRAM_URL, PDF_URL, KEY 
    FROM data_main_daily_send 
    WHERE SEC_FIRM_ORDER = 0 
      AND (TELEGRAM_URL LIKE '%EtwBoardData%' OR TELEGRAM_URL IS NULL OR TELEGRAM_URL = '')
    ORDER BY REG_DT ASC
    """
    logger.info("🔍 Fetching all pending LS records from database...")
    cursor.execute(sql)
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    total = len(records)
    if total == 0:
        logger.info("✅ 보정 대상 LS 레코드가 없습니다.")
        return

    batch_size = 20  # 대량 처리를 위해 배치 사이즈 소폭 상향
    logger.info(f"🚀 총 {total:,}개의 LS 레코드 보정을 시작합니다 (과거 데이터부터 순차 진행).")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.ls-sec.co.kr/",
    }

    async with ClientSession() as session:
        for start_idx in range(0, total, batch_size):
            batch = records[start_idx : start_idx + batch_size]
            current_batch_results = []
            
            progress = (start_idx + len(batch)) / total * 100
            logger.info(f"📊 Progress: {start_idx + len(batch):,}/{total:,} ({progress:.1f}%) | Batch {start_idx + 1} ~ {min(start_idx + batch_size, total)}")
            
            for article in batch:
                try:
                    # process_article 내부에서 Warp(9091) 프록시를 사용할 수 있음
                    await process_article(session, article, headers)
                    
                    # 보정이 성공한 건만 결과 리스트에 추가
                    t_url = article.get('TELEGRAM_URL', '')
                    if t_url and t_url.lower().endswith('.pdf'):
                        current_batch_results.append(article)
                    
                    # 개별 요청 간 짧은 대기 (서버 부하 방지)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"❌ Error processing ID {article.get('report_id')}: {e}")

            if current_batch_results:
                if update_db_batch(current_batch_results):
                    logger.success(f"✅ Batch Update Success: {len(current_batch_results)} rows")
                else:
                    logger.error("❌ Batch Update Final Failure (DB Lock issues)")
            
            # 배치 간 대기 (서버 부하 및 DB Lock 경감)
            await asyncio.sleep(1.0)

    logger.success("✨ 모든 LS 과거 데이터 보정 작업이 완료되었습니다.")

if __name__ == "__main__":
    try:
        asyncio.run(fix_ls_all_history())
    except KeyboardInterrupt:
        logger.warning("Stopped by user.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
