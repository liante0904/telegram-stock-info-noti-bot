#!/usr/bin/env python3
"""
Export recent production PostgreSQL rows to JSON, upsert them into V2, and compare.

Default range is the last 2 calendar days including today, based on SAVE_TIME.
This script does not depend on DB_BACKEND and does not touch the production table.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from loguru import logger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


ROOT = Path(__file__).resolve().parents[1]
V1_TABLE = '"TB_SEC_REPORTS"'
V2_TABLE = "tb_sec_reports_v2"

V1_COLUMNS = [
    "report_id",
    '"SEC_FIRM_ORDER"',
    '"ARTICLE_BOARD_ORDER"',
    '"FIRM_NM"',
    '"ATTACH_URL"',
    '"ARTICLE_TITLE"',
    '"ARTICLE_URL"',
    '"SEND_USER"',
    '"MAIN_CH_SEND_YN"',
    '"DOWNLOAD_STATUS_YN"',
    '"DOWNLOAD_URL"',
    '"SAVE_TIME"',
    '"REG_DT"',
    '"WRITER"',
    '"KEY"',
    '"TELEGRAM_URL"',
    '"MKT_TP"',
    '"GEMINI_SUMMARY"',
    '"SUMMARY_TIME"',
    '"SUMMARY_MODEL"',
    '"ARCHIVE_STATUS"',
    '"ARCHIVE_FILE_NAME"',
    '"ARCHIVE_PATH"',
    '"PDF_URL"',
    '"retry_count"',
    '"sync_status"',
]

JSON_COLUMNS = [
    "report_id",
    "SEC_FIRM_ORDER",
    "ARTICLE_BOARD_ORDER",
    "FIRM_NM",
    "ATTACH_URL",
    "ARTICLE_TITLE",
    "ARTICLE_URL",
    "SEND_USER",
    "MAIN_CH_SEND_YN",
    "DOWNLOAD_STATUS_YN",
    "DOWNLOAD_URL",
    "SAVE_TIME",
    "REG_DT",
    "WRITER",
    "KEY",
    "TELEGRAM_URL",
    "MKT_TP",
    "GEMINI_SUMMARY",
    "SUMMARY_TIME",
    "SUMMARY_MODEL",
    "ARCHIVE_STATUS",
    "ARCHIVE_FILE_NAME",
    "ARCHIVE_PATH",
    "PDF_URL",
    "retry_count",
    "sync_status",
]

V2_COLUMNS = [
    "sec_firm_order",
    "article_board_order",
    "firm_nm",
    "attach_url",
    "article_title",
    "article_url",
    "send_user",
    "main_ch_send_yn",
    "download_status_yn",
    "download_url",
    "save_time",
    "reg_dt",
    "writer",
    "key",
    "telegram_url",
    "mkt_tp",
    "gemini_summary",
    "summary_time",
    "summary_model",
    "archive_status",
    "archive_file_name",
    "archive_path",
    "pdf_url",
    "retry_count",
    "sync_status",
]

JSON_TO_V2 = {
    "SEC_FIRM_ORDER": "sec_firm_order",
    "ARTICLE_BOARD_ORDER": "article_board_order",
    "FIRM_NM": "firm_nm",
    "ATTACH_URL": "attach_url",
    "ARTICLE_TITLE": "article_title",
    "ARTICLE_URL": "article_url",
    "SEND_USER": "send_user",
    "MAIN_CH_SEND_YN": "main_ch_send_yn",
    "DOWNLOAD_STATUS_YN": "download_status_yn",
    "DOWNLOAD_URL": "download_url",
    "SAVE_TIME": "save_time",
    "REG_DT": "reg_dt",
    "WRITER": "writer",
    "KEY": "key",
    "TELEGRAM_URL": "telegram_url",
    "MKT_TP": "mkt_tp",
    "GEMINI_SUMMARY": "gemini_summary",
    "SUMMARY_TIME": "summary_time",
    "SUMMARY_MODEL": "summary_model",
    "ARCHIVE_STATUS": "archive_status",
    "ARCHIVE_FILE_NAME": "archive_file_name",
    "ARCHIVE_PATH": "archive_path",
    "PDF_URL": "pdf_url",
    "retry_count": "retry_count",
    "sync_status": "sync_status",
}

COMPARE_COLUMNS = [column for column in JSON_COLUMNS if column != "report_id"]


def clean(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    return value


def json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def comparable(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    if isinstance(value, str):
        return value.replace("T", " ")
    return str(value)


def get_pg_conn():
    from models.ConfigManager import config

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "ssh_reports_hub"),
        user=os.getenv("POSTGRES_USER", "ssh_reports_hub"),
        password=os.getenv("POSTGRES_PASSWORD", config.get_secret("POSTGRES_PASSWORD")),
    )


def export_recent_postgres(days, output_path):
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    select_cols = ",".join(V1_COLUMNS)
    sql = f"""
        SELECT {select_cols}
        FROM {V1_TABLE}
        WHERE DATE("SAVE_TIME") >= DATE(%s)
          AND "KEY" IS NOT NULL
          AND "KEY" != ''
        ORDER BY "SAVE_TIME" DESC, report_id DESC
    """

    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (start_date,))
            rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=json_default)

    logger.info(f"PostgreSQL V1 export range: SAVE_TIME >= {start_date}")
    logger.info(f"PostgreSQL V1 rows exported: {len(rows)}")
    logger.info(f"JSON written: {output_path}")
    return rows, start_date


def load_rows_from_json(input_path):
    with input_path.open("r", encoding="utf-8") as f:
        rows = json.load(f)
    logger.info(f"JSON loaded: {input_path}")
    logger.info(f"Rows loaded: {len(rows)}")
    return rows


def upsert_v2(rows, page_size=1000):
    if not rows:
        return 0, 0

    values = [
        tuple(clean(row.get(json_column)) for json_column in JSON_TO_V2)
        for row in rows
    ]
    insert_cols = ",".join(V2_COLUMNS)
    update_assignments = ",".join(
        f"{column}=EXCLUDED.{column}" for column in V2_COLUMNS if column != "key"
    )
    sql = f"""
        INSERT INTO {V2_TABLE} ({insert_cols})
        VALUES %s
        ON CONFLICT (key) DO UPDATE SET {update_assignments}
        RETURNING (xmax = 0) AS inserted
    """

    inserted = updated = 0
    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(cur, sql, values, page_size=page_size)
                for (is_inserted,) in cur.fetchall():
                    if is_inserted:
                        inserted += 1
                    else:
                        updated += 1
    finally:
        conn.close()

    logger.info(f"V2 upsert complete: inserted={inserted}, updated={updated}")
    return inserted, updated


def fetch_v2_by_keys(keys):
    if not keys:
        return {}

    select_cols = ",".join(V2_COLUMNS)
    conn = get_pg_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT {select_cols} FROM {V2_TABLE} WHERE key = ANY(%s)",
                (list(keys),),
            )
            return {row["key"]: dict(row) for row in cur.fetchall()}
    finally:
        conn.close()


def compare_rows(source_rows):
    source_by_key = {row["KEY"]: row for row in source_rows if row.get("KEY")}
    v2_by_key = fetch_v2_by_keys(source_by_key.keys())

    missing_in_v2 = sorted(set(source_by_key) - set(v2_by_key))
    mismatches = []
    for key, source_row in source_by_key.items():
        v2_row = v2_by_key.get(key)
        if not v2_row:
            continue
        for source_column in COMPARE_COLUMNS:
            v2_column = JSON_TO_V2[source_column]
            if comparable(source_row.get(source_column)) != comparable(v2_row.get(v2_column)):
                mismatches.append(
                    {
                        "KEY": key,
                        "column": source_column,
                        "v1": comparable(source_row.get(source_column)),
                        "v2": comparable(v2_row.get(v2_column)),
                    }
                )
                break

    logger.info(f"Compare keys: v1={len(source_by_key)}, v2={len(v2_by_key)}")
    if missing_in_v2:
        logger.error(f"Missing in V2: {len(missing_in_v2)}")
        logger.error(f"Missing sample: {missing_in_v2[:5]}")
    if mismatches:
        logger.error(f"Column mismatches: {len(mismatches)}")
        logger.error(f"Mismatch sample: {mismatches[:5]}")

    if missing_in_v2 or mismatches:
        raise SystemExit(1)

    logger.success("PostgreSQL V1 and V2 recent data match by KEY and compared columns.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--output", default=None)
    parser.add_argument("--input", default=None, help="Use an existing JSON file instead of exporting V1.")
    parser.add_argument("--dry-run", action="store_true", help="Export/load JSON only; do not upsert V2.")
    parser.add_argument("--skip-compare", action="store_true", help="Skip KEY/column comparison after upsert.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)

    if args.input:
        rows = load_rows_from_json(Path(args.input))
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = (
            Path(args.output)
            if args.output
            else ROOT / "json" / f"postgres_recent_{args.days}d_for_v2_{timestamp}.json"
        )
        rows, _ = export_recent_postgres(args.days, output_path)

    if args.dry_run:
        logger.info("Dry run enabled; V2 upsert skipped.")
        return

    upsert_v2(rows)
    if not args.skip_compare:
        compare_rows(rows)


if __name__ == "__main__":
    main()
