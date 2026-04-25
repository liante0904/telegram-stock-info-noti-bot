import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def setup_v2_tables():
    load_dotenv(override=True)
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "ssh_reports_hub"),
        user=os.getenv("POSTGRES_USER", "ssh_reports_hub"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )
    cur = conn.cursor()

    try:
        # 1. tb_sec_reports_v2 생성
        logger_print("Creating tb_sec_reports_v2...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tb_sec_reports_v2 (
                report_id SERIAL PRIMARY KEY,
                sec_firm_order INTEGER,
                article_board_order INTEGER,
                firm_nm TEXT,
                attach_url TEXT,
                article_title TEXT,
                article_url TEXT,
                send_user TEXT,
                main_ch_send_yn TEXT,
                download_status_yn TEXT,
                download_url TEXT,
                save_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reg_dt TEXT,
                writer TEXT,
                key TEXT UNIQUE,
                telegram_url TEXT,
                mkt_tp TEXT DEFAULT 'KR',
                gemini_summary TEXT,
                summary_time TEXT,
                summary_model TEXT,
                archive_status TEXT DEFAULT 'INIT',
                archive_file_name TEXT,
                archive_path TEXT,
                pdf_url TEXT,
                retry_count INTEGER DEFAULT 0,
                sync_status INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_v2_reg_dt ON tb_sec_reports_v2 (reg_dt);
            CREATE INDEX IF NOT EXISTS idx_v2_sec_firm ON tb_sec_reports_v2 (sec_firm_order);
            CREATE INDEX IF NOT EXISTS idx_v2_save_time ON tb_sec_reports_v2 (save_time);
        """)

        # 2. report_alert_keywords 생성
        logger_print("Creating report_alert_keywords...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS report_alert_keywords (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        logger_print("V2 tables created successfully.")
    except Exception as e:
        conn.rollback()
        logger_print(f"Error creating V2 tables: {e}")
    finally:
        cur.close()
        conn.close()

def logger_print(msg):
    print(f"[SETUP_V2] {msg}")

if __name__ == "__main__":
    setup_v2_tables()
