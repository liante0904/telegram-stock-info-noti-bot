import os
import sys
import psycopg2
import psycopg2.extras
from loguru import logger
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.PostgreSQLManager import PostgreSQLManager
from models.PostgreSQLManagerV2 import PostgreSQLManagerV2

def migrate_data():
    v1 = PostgreSQLManager()
    v2 = PostgreSQLManagerV2()

    # 1. Migrate TB_SEC_REPORTS
    logger.info("Migrating TB_SEC_REPORTS to tb_sec_reports_v2...")
    v1_conn = v1.get_connection()
    # Use RealDictCursor to get dict results
    v1_cur = v1_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    v2_conn = v2.get_connection()
    v2_cur = v2_conn.cursor()

    try:
        # Fetch all from V1
        v1_cur.execute('SELECT * FROM "TB_SEC_REPORTS" ORDER BY report_id')
        
        batch_size = 10000
        count = 0
        
        while True:
            rows = v1_cur.fetchmany(batch_size)
            if not rows:
                break
            
            records = []
            for r in rows:
                records.append((
                    r.get("SEC_FIRM_ORDER"), r.get("ARTICLE_BOARD_ORDER"), r.get("FIRM_NM"),
                    r.get("ATTACH_URL"), r.get("ARTICLE_TITLE"), r.get("ARTICLE_URL"),
                    r.get("SEND_USER"), r.get("MAIN_CH_SEND_YN"), r.get("DOWNLOAD_STATUS_YN"),
                    r.get("DOWNLOAD_URL"), r.get("SAVE_TIME"), r.get("REG_DT"),
                    r.get("WRITER"), r.get("KEY"), r.get("TELEGRAM_URL"),
                    r.get("MKT_TP") or 'KR', r.get("GEMINI_SUMMARY"), r.get("SUMMARY_TIME"),
                    r.get("SUMMARY_MODEL"), r.get("ARCHIVE_STATUS") or 'INIT',
                    r.get("ARCHIVE_FILE_NAME"), r.get("ARCHIVE_PATH"), r.get("PDF_URL"),
                    r.get("retry_count") or 0, r.get("sync_status") or 0
                ))

            sql = """
                INSERT INTO tb_sec_reports_v2 (
                    sec_firm_order, article_board_order, firm_nm, attach_url,
                    article_title, article_url, send_user, main_ch_send_yn,
                    download_status_yn, download_url, save_time, reg_dt,
                    writer, key, telegram_url, mkt_tp, gemini_summary,
                    summary_time, summary_model, archive_status, archive_file_name,
                    archive_path, pdf_url, retry_count, sync_status
                ) VALUES %s
                ON CONFLICT (key) DO NOTHING
            """
            psycopg2.extras.execute_values(v2_cur, sql, records)
            v2_conn.commit()
            count += len(records)
            logger.info(f"Progress: {count} rows migrated...")

        logger.info(f"Successfully migrated {count} records to tb_sec_reports_v2.")

    except Exception as e:
        logger.error(f"Error during TB_SEC_REPORTS migration: {e}")
        v2_conn.rollback()
    finally:
        v1_cur.close()
        v1_conn.close()
        v2_cur.close()
        v2_conn.close()

    # 2. Migrate REPORT_ALERT_KEYWORDS
    logger.info("Migrating REPORT_ALERT_KEYWORDS to report_alert_keywords...")
    v1_conn = v1.get_connection()
    v1_cur = v1_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    v2_conn = v2.get_connection()
    v2_cur = v2_conn.cursor()
    
    try:
        v1_cur.execute("SELECT * FROM \"REPORT_ALERT_KEYWORDS\"")
        keyword_rows = v1_cur.fetchall()
        
        if keyword_rows:
            keyword_records = []
            for r in keyword_rows:
                # Handle integer timestamp conversion
                ca = r.get("created_at")
                if isinstance(ca, (int, float)):
                    ca = datetime.fromtimestamp(ca)
                
                keyword_records.append((
                    r.get("user_id"), r.get("keyword"), r.get("is_active"), ca
                ))
            
            sql_kw = """
                INSERT INTO report_alert_keywords (user_id, keyword, is_active, created_at)
                VALUES %s
                ON CONFLICT DO NOTHING
            """
            psycopg2.extras.execute_values(v2_cur, sql_kw, keyword_records)
            v2_conn.commit()
            logger.info(f"Successfully migrated {len(keyword_records)} keywords.")
            
    except Exception as e:
        logger.warning(f"REPORT_ALERT_KEYWORDS migration skipped or failed: {e}")
        v2_conn.rollback()
    finally:
        v1_cur.close()
        v1_conn.close()
        v2_cur.close()
        v2_conn.close()

if __name__ == "__main__":
    migrate_data()
