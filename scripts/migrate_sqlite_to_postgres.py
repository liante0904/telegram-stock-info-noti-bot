#!/usr/bin/env python3
"""
SQLite → PostgreSQL 데이터 마이그레이션 스크립트
Usage: python3 scripts/migrate_sqlite_to_postgres.py [--tables all|firm|main|naver|hankyung] [--truncate]
"""
import sqlite3
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import psycopg2
import psycopg2.extras
from loguru import logger

SQLITE_DB = os.path.expanduser("~/sqlite3/telegram.db")

def _clean(v):
    """Strip NUL bytes that PostgreSQL rejects in text columns."""
    if isinstance(v, str):
        return v.replace("\x00", "")
    return v


def get_pg_conn():
    from models.ConfigManager import config
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "ssh_reports_hub"),
        user=os.getenv("POSTGRES_USER", "ssh_reports_hub"),
        password=os.getenv("POSTGRES_PASSWORD", config.get_secret("POSTGRES_PASSWORD")),
    )


def migrate_firm_info():
    logger.info("Migrating TBM_SEC_FIRM_INFO and TBM_SEC_FIRM_BOARD_INFO...")
    sq = sqlite3.connect(SQLITE_DB)
    sq.row_factory = sqlite3.Row

    firms = [dict(r) for r in sq.execute("SELECT * FROM TBM_SEC_FIRM_INFO").fetchall()]
    boards = [dict(r) for r in sq.execute("SELECT * FROM TBM_SEC_FIRM_BOARD_INFO").fetchall()]
    sq.close()

    pg = get_pg_conn()
    cur = pg.cursor()

    # FIRM_INFO
    psycopg2.extras.execute_values(
        cur,
        '''INSERT INTO "TBM_SEC_FIRM_INFO" ("SEC_FIRM_ORDER","FIRM_NM","TELEGRAM_UPDATE_YN")
           VALUES %s
           ON CONFLICT ("SEC_FIRM_ORDER") DO UPDATE SET
               "FIRM_NM"=EXCLUDED."FIRM_NM",
               "TELEGRAM_UPDATE_YN"=EXCLUDED."TELEGRAM_UPDATE_YN"''',
        [(r["SEC_FIRM_ORDER"], r["FIRM_NM"], r["TELEGRAM_UPDATE_YN"]) for r in firms],
    )

    # BOARD_INFO
    psycopg2.extras.execute_values(
        cur,
        '''INSERT INTO "TBM_SEC_FIRM_BOARD_INFO"
               ("SEC_FIRM_ORDER","ARTICLE_BOARD_ORDER","BOARD_NM","BOARD_CD","LABEL_NM")
           VALUES %s
           ON CONFLICT ("SEC_FIRM_ORDER","ARTICLE_BOARD_ORDER") DO UPDATE SET
               "BOARD_NM"=EXCLUDED."BOARD_NM",
               "BOARD_CD"=EXCLUDED."BOARD_CD",
               "LABEL_NM"=EXCLUDED."LABEL_NM"''',
        [(r["SEC_FIRM_ORDER"], r["ARTICLE_BOARD_ORDER"], r["BOARD_NM"], r["BOARD_CD"], r["LABEL_NM"])
         for r in boards],
    )

    pg.commit()
    cur.close()
    pg.close()
    logger.info(f"  firms: {len(firms)}, boards: {len(boards)}")


def migrate_main(batch_size=5000, truncate=False):
    logger.info('Migrating TB_SEC_REPORTS...')
    sq = sqlite3.connect(SQLITE_DB)
    sq.row_factory = sqlite3.Row

    total = sq.execute("SELECT COUNT(*) FROM data_main_daily_send").fetchone()[0]
    logger.info(f"  total SQLite rows: {total}")

    pg = get_pg_conn()
    cur = pg.cursor()

    if truncate:
        logger.warning('Truncating TB_SEC_REPORTS before migration...')
        cur.execute('TRUNCATE TABLE "TB_SEC_REPORTS" CASCADE')
        pg.commit()
        logger.info('  Table truncated.')

    # Check already-migrated max report_id
    cur.execute('SELECT COALESCE(MAX(report_id), 0) FROM "TB_SEC_REPORTS"')
    max_pg_id = cur.fetchone()[0]
    logger.info(f"  PostgreSQL max report_id: {max_pg_id} — starting from there")

    offset = 0
    sq_cur = sq.cursor()
    sq_cur.execute(
        "SELECT report_id,SEC_FIRM_ORDER,ARTICLE_BOARD_ORDER,FIRM_NM,ATTACH_URL,"
        "ARTICLE_TITLE,ARTICLE_URL,SEND_USER,MAIN_CH_SEND_YN,DOWNLOAD_STATUS_YN,"
        "DOWNLOAD_URL,SAVE_TIME,REG_DT,WRITER,KEY,TELEGRAM_URL,MKT_TP,"
        "GEMINI_SUMMARY,SUMMARY_TIME,SUMMARY_MODEL,ARCHIVE_STATUS,ARCHIVE_FILE_NAME,"
        "ARCHIVE_PATH,retry_count,sync_status,PDF_URL "
        "FROM data_main_daily_send ORDER BY report_id"
    )

    while True:
        rows = sq_cur.fetchmany(batch_size)
        if not rows:
            break

        records = [
            (
                r["report_id"], r["SEC_FIRM_ORDER"], r["ARTICLE_BOARD_ORDER"],
                _clean(r["FIRM_NM"]), _clean(r["ATTACH_URL"]), _clean(r["ARTICLE_TITLE"]),
                _clean(r["ARTICLE_URL"]), _clean(r["SEND_USER"]),
                _clean(r["MAIN_CH_SEND_YN"]), _clean(r["DOWNLOAD_STATUS_YN"] or ''),
                _clean(r["DOWNLOAD_URL"]), _clean(r["SAVE_TIME"]),
                _clean(r["REG_DT"] or ''), _clean(r["WRITER"] or ''),
                _clean(r["KEY"]), _clean(r["TELEGRAM_URL"] or ''),
                _clean(r["MKT_TP"] or 'KR'), _clean(r["GEMINI_SUMMARY"]),
                _clean(r["SUMMARY_TIME"]), _clean(r["SUMMARY_MODEL"]),
                _clean(r["ARCHIVE_STATUS"] or 'INIT'),
                _clean(r["ARCHIVE_FILE_NAME"]), _clean(r["ARCHIVE_PATH"]),
                r["retry_count"] or 0, r["sync_status"] or 0, _clean(r["PDF_URL"] or ''),
            )
            for r in rows
        ]

        psycopg2.extras.execute_values(
            cur,
            '''INSERT INTO "TB_SEC_REPORTS" (
                report_id,"SEC_FIRM_ORDER","ARTICLE_BOARD_ORDER","FIRM_NM","ATTACH_URL",
                "ARTICLE_TITLE","ARTICLE_URL","SEND_USER","MAIN_CH_SEND_YN","DOWNLOAD_STATUS_YN",
                "DOWNLOAD_URL","SAVE_TIME","REG_DT","WRITER","KEY","TELEGRAM_URL","MKT_TP",
                "GEMINI_SUMMARY","SUMMARY_TIME","SUMMARY_MODEL","ARCHIVE_STATUS","ARCHIVE_FILE_NAME",
                "ARCHIVE_PATH","retry_count","sync_status","PDF_URL"
            ) VALUES %s
            ON CONFLICT ("KEY") DO UPDATE SET
                "REG_DT"             = EXCLUDED."REG_DT",
                "WRITER"             = EXCLUDED."WRITER",
                "MKT_TP"             = EXCLUDED."MKT_TP",
                "MAIN_CH_SEND_YN"    = EXCLUDED."MAIN_CH_SEND_YN",
                "DOWNLOAD_STATUS_YN" = EXCLUDED."DOWNLOAD_STATUS_YN",
                "GEMINI_SUMMARY"     = COALESCE(NULLIF(EXCLUDED."GEMINI_SUMMARY",''), "TB_SEC_REPORTS"."GEMINI_SUMMARY"),
                "DOWNLOAD_URL"       = COALESCE(NULLIF(EXCLUDED."DOWNLOAD_URL",''),  "TB_SEC_REPORTS"."DOWNLOAD_URL"),
                "TELEGRAM_URL"       = COALESCE(NULLIF(EXCLUDED."TELEGRAM_URL",''),  "TB_SEC_REPORTS"."TELEGRAM_URL"),
                "PDF_URL"            = COALESCE(NULLIF(EXCLUDED."PDF_URL",''),        "TB_SEC_REPORTS"."PDF_URL")''',
            records,
            page_size=batch_size,
        )
        pg.commit()
        offset += len(rows)
        logger.info(f"  progress: {offset}/{total}")

    # Advance sequence past max id
    cur.execute('SELECT MAX(report_id) FROM "TB_SEC_REPORTS"')
    max_id = cur.fetchone()[0] or 0
    cur.execute(f"SELECT setval('tb_sec_reports_report_id_seq', {max_id})")
    pg.commit()

    cur.close()
    pg.close()
    sq.close()
    logger.info(f"  Done. {offset} rows processed.")


def migrate_aux_table(table_name):
    logger.info(f"Migrating {table_name}...")
    sq = sqlite3.connect(SQLITE_DB)
    sq.row_factory = sqlite3.Row

    rows = [dict(r) for r in sq.execute(
        f"SELECT SEC_FIRM_ORDER,ARTICLE_BOARD_ORDER,FIRM_NM,ATTACH_URL,"
        f"ARTICLE_TITLE,SEND_USER,MAIN_CH_SEND_YN,SAVE_TIME,ARTICLE_URL,DOWNLOAD_URL,WRITER"
        f" FROM {table_name}"
    ).fetchall()]
    sq.close()

    if not rows:
        logger.info(f"  {table_name}: empty, skipping")
        return

    pg = get_pg_conn()
    cur = pg.cursor()
    psycopg2.extras.execute_values(
        cur,
        f'''INSERT INTO {table_name}
               ("SEC_FIRM_ORDER","ARTICLE_BOARD_ORDER","FIRM_NM","ATTACH_URL",
                "ARTICLE_TITLE","SEND_USER","MAIN_CH_SEND_YN","SAVE_TIME",
                "ARTICLE_URL","DOWNLOAD_URL","WRITER")
           VALUES %s
           ON CONFLICT ("ATTACH_URL") DO NOTHING''',
        [(r["SEC_FIRM_ORDER"], r["ARTICLE_BOARD_ORDER"], r["FIRM_NM"], r["ATTACH_URL"],
          r["ARTICLE_TITLE"], r["SEND_USER"], r["MAIN_CH_SEND_YN"], r["SAVE_TIME"],
          r["ARTICLE_URL"], r["DOWNLOAD_URL"], r["WRITER"] or '') for r in rows],
    )
    pg.commit()
    cur.close()
    pg.close()
    logger.info(f"  {table_name}: {len(rows)} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", default="all",
                        choices=["all", "firm", "main", "naver", "hankyung"])
    parser.add_argument("--truncate", action="store_true", help="Truncate tables before migration")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/prod/ssh-reports-scraper/.env"))

    if args.tables in ("all", "firm"):
        migrate_firm_info()
    if args.tables in ("all", "main"):
        migrate_main(truncate=args.truncate)
    if args.tables in ("all", "naver"):
        migrate_aux_table("naver_research")
    if args.tables in ("all", "hankyung"):
        migrate_aux_table("hankyungconsen_research")

    logger.info("Migration complete.")
