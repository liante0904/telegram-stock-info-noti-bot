import os
import sys
import re
from datetime import datetime, timedelta
from loguru import logger

import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class PostgreSQLManager:
    """PostgreSQL backend — drop-in replacement for SQLiteManager.

    Existing keyword-alert usage (load_keywords_from_db) is preserved.
    New methods mirror SQLiteManager's interface for the scraper pipeline.
    """

    MAIN_TABLE = "tbl_sec_reports"
    _LEGACY_COLUMNS = (
        "sec_firm_order",
        "article_board_order",
        "firm_nm",
        "article_title",
        "article_url",
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
        "retry_count",
        "sync_status",
        "pdf_url",
        "pdf_sync_status",
    )

    # Callers that still pass the old SQLite table name are transparently remapped.
    _TABLE_MAP = {
        "data_main_daily_send": "tbl_sec_reports",
        "tbl_sec_reports": "tbl_sec_reports",
    }

    def __init__(self):
        load_dotenv(override=True)
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        self.database = os.getenv("POSTGRES_REPORT_DB", "ssh_reports_hub")
        self.keyword_database = os.getenv("POSTGRES_KEYWORD_DB", self.database)
        self.user = os.getenv("POSTGRES_USER", "ssh_reports_hub")
        self.password = os.getenv("POSTGRES_PASSWORD", "")
        self.main_table_name = self.MAIN_TABLE

    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def get_keyword_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.keyword_database,
            user=self.user,
            password=self.password,
        )

    # ------------------------------------------------------------------
    # Keyword-alert (existing, unchanged)
    # ------------------------------------------------------------------

    def load_keywords_from_db(self):
        """PostgreSQL에서 활성화된 키워드 정보를 가져와 기존 JSON 구조와 호환되는 dict 형태로 반환합니다."""
        conn = None
        try:
            conn = self.get_keyword_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT to_regclass('tbm_sec_reports_alert_keywords')
                """)
                table_exists = cur.fetchone()[0]
                if not table_exists:
                    logger.warning("Keyword table tbm_sec_reports_alert_keywords does not exist. Returning empty keyword set.")
                    return {}

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, keyword, created_at
                    FROM tbm_sec_reports_alert_keywords
                    WHERE is_active = true
                    ORDER BY user_id, created_at ASC
                """)
                rows = cur.fetchall()

            user_keywords = {}
            for row in rows:
                user_id = str(row["user_id"])
                created_at = row["created_at"]
                if isinstance(created_at, (int, float)):
                    ts = datetime.fromtimestamp(created_at).isoformat()
                elif isinstance(created_at, datetime):
                    ts = created_at.isoformat()
                else:
                    ts = datetime.now().isoformat()

                user_keywords.setdefault(user_id, []).append(
                    {"keyword": row["keyword"], "code": "", "timestamp": ts}
                )
            return user_keywords
        except Exception as e:
            logger.error(f"Error loading keywords from PostgreSQL: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    # ------------------------------------------------------------------
    # Scraper pipeline — mirrors SQLiteManager interface
    # ------------------------------------------------------------------

    def insert_json_data_list(self, json_data_list, table_name=None):
        """Insert/upsert a list of report dicts. Returns (inserted, updated)."""
        if table_name is None:
            table_name = self.main_table_name
        table_name = self._TABLE_MAP.get(table_name, table_name)

        records = [
            (
                entry.get("sec_firm_order"),
                entry.get("article_board_order"),
                entry.get("firm_nm"),
                entry.get("reg_dt", ""),
                entry.get("article_title"),
                entry.get("article_url"),
                entry.get("main_ch_send_yn", "N"),
                entry.get("download_url"),
                entry.get("telegram_url"),
                entry.get("pdf_url") or entry.get("telegram_url"),
                entry.get("writer", ""),
                entry.get("mkt_tp", "KR"),
                entry.get("key") or entry.get("article_url", ""),
                entry.get("save_time"),
            )
            for entry in json_data_list
        ]

        sql = f'''
            INSERT INTO {table_name} (
                sec_firm_order, article_board_order, firm_nm, reg_dt,
                article_title, article_url, main_ch_send_yn, download_url,
                telegram_url, pdf_url, writer, mkt_tp, key, save_time
            ) VALUES %s
            ON CONFLICT (key) DO UPDATE SET
                reg_dt       = EXCLUDED.reg_dt,
                writer       = EXCLUDED.writer,
                mkt_tp       = EXCLUDED.mkt_tp,
                download_url = COALESCE(NULLIF(EXCLUDED.download_url,\'\'),  {table_name}.download_url),
                telegram_url = COALESCE(NULLIF(EXCLUDED.telegram_url,\'\'), {table_name}.telegram_url),
                pdf_url      = COALESCE(NULLIF(EXCLUDED.pdf_url,\'\'),       {table_name}.pdf_url)
            RETURNING (xmax = 0) AS inserted
        '''

        inserted = updated = 0
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_values(cur, sql, records)
                    for (is_insert,) in cur.fetchall():
                        if is_insert:
                            inserted += 1
                        else:
                            updated += 1
        finally:
            conn.close()

        logger.info(f"PostgreSQL Data inserted: {inserted} rows, updated: {updated} rows.")
        return inserted, updated

    async def fetch_daily_articles_by_date(self, firm_info, date_str=None):
        query_date = date_str or datetime.now().strftime("%Y%m%d")
        firmInfo = firm_info.get_state()
        base = datetime.strptime(query_date, "%Y%m%d")
        date_from = (base - timedelta(days=3)).strftime("%Y%m%d")
        date_to = (base + timedelta(days=2)).strftime("%Y%m%d")

        sql = f"""
        SELECT report_id,sec_firm_order,article_board_order,firm_nm,reg_dt,
               article_title,article_url,main_ch_send_yn,
               download_url,writer,save_time,telegram_url,key,pdf_url
        FROM   {self.main_table_name}
        WHERE  reg_dt BETWEEN %s AND %s
          AND  sec_firm_order = %s
          AND  key IS NOT NULL
          AND  (telegram_url IS NULL OR telegram_url = '')
        ORDER BY sec_firm_order,article_board_order,save_time
        """
        return self._fetchall(sql, (date_from, date_to, str(firmInfo["sec_firm_order"])))

    async def fetch_all_empty_telegram_url_articles(self, firm_info, days_limit=None):
        firmInfo = firm_info.get_state()
        sql = f"""
        SELECT report_id,sec_firm_order,article_board_order,firm_nm,reg_dt,
               article_title,article_url,main_ch_send_yn,
               download_url,writer,save_time,telegram_url,key,pdf_url
        FROM   {self.main_table_name}
        WHERE  sec_firm_order = %s
          AND  key IS NOT NULL
          AND  (telegram_url IS NULL OR telegram_url = '')
        """
        params = [str(firmInfo["sec_firm_order"])]
        if days_limit:
            cutoff = (datetime.now() - timedelta(days=days_limit)).strftime("%Y-%m-%d %H:%M:%S")
            sql += ' AND save_time >= %s'
            params.append(cutoff)
        sql += ' ORDER BY reg_dt DESC, save_time DESC'
        return self._fetchall(sql, params)

    async def fetch_ls_detail_targets(self):
        sql = f"""
        SELECT report_id,sec_firm_order,article_board_order,firm_nm,reg_dt,
               article_title,article_url,main_ch_send_yn,
               download_url,writer,save_time,telegram_url,key
        FROM   {self.main_table_name}
        WHERE  sec_firm_order = 0
          AND  (telegram_url NOT LIKE \'%.pdf\'
                OR telegram_url IS NULL OR telegram_url = \'\')
        """
        return self._fetchall(sql)

    async def update_telegram_url(self, record_id, telegram_url, article_title=None, pdf_url=None):
        if pdf_url is None:
            pdf_url = telegram_url
        if article_title is not None:
            sql = f'UPDATE {self.main_table_name} SET telegram_url=%s,pdf_url=%s,article_title=%s WHERE report_id=%s'
            params = (telegram_url, pdf_url, article_title, record_id)
        else:
            sql = f'UPDATE {self.main_table_name} SET telegram_url=%s,pdf_url=%s WHERE report_id=%s'
            params = (telegram_url, pdf_url, record_id)
        return self._execute(sql, params)

    async def daily_select_data(self, date_str=None, type=None):
        if type not in ("send", "download"):
            raise ValueError("Invalid type. Must be 'send' or 'download'.")

        if date_str is None:
            query_date = datetime.now().strftime("%Y-%m-%d")
            query_reg_dt = (datetime.now() + timedelta(days=2)).strftime("%Y%m%d")
        else:
            query_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            query_reg_dt = (datetime.strptime(date_str, "%Y%m%d") + timedelta(days=2)).strftime("%Y%m%d")

        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")

        if type == "send":
            cond = """(main_ch_send_yn != 'Y' OR main_ch_send_yn IS NULL)
                      AND (sec_firm_order != 19 OR (sec_firm_order = 19 AND telegram_url <> ''))"""
        else:
            cond = 'main_ch_send_yn = \'Y\' AND download_status_yn != \'Y\''

        # DISTINCT ON replaces SQLite GROUP BY trick
        sql = f"""
        SELECT DISTINCT ON (
            CASE WHEN telegram_url IS NULL OR telegram_url = ''
                 THEN report_id::TEXT ELSE telegram_url END
        )
            report_id,sec_firm_order,article_board_order,firm_nm,reg_dt,
            article_title,article_url,main_ch_send_yn,
            download_url,writer,save_time,telegram_url
        FROM   {self.main_table_name}
        WHERE  DATE(save_time) = %s
          AND  reg_dt >= %s
          AND  reg_dt <= %s
          AND  {cond}
        ORDER BY
            CASE WHEN telegram_url IS NULL OR telegram_url = ''
                 THEN report_id::TEXT ELSE telegram_url END,
            sec_firm_order,article_board_order,save_time
        """
        return self._fetchall(sql, (query_date, three_days_ago, query_reg_dt))

    async def daily_update_data(self, date_str=None, fetched_rows=None, type=None):
        if type not in ("send", "download"):
            raise ValueError("Invalid type. Must be 'send' or 'download'.")
        if type == "send":
            for row in fetched_rows:
                tg = row.get("telegram_url")
                if tg:
                    self._execute(
                        f"UPDATE {self.main_table_name} SET main_ch_send_yn='Y' WHERE telegram_url=%s",
                        (tg,),
                    )
                else:
                    self._execute(
                        f"UPDATE {self.main_table_name} SET main_ch_send_yn='Y' WHERE report_id=%s",
                        (row["report_id"],),
                    )
        else:
            for row in fetched_rows:
                self._execute(
                    f"UPDATE {self.main_table_name} SET download_status_yn='Y' WHERE report_id=%s",
                    (row["report_id"],),
                )
        return {"status": "success"}

    async def update_report_summary_by_telegram_url(self, telegram_url, summary, model_name):
        sql = f"""
        UPDATE {self.main_table_name}
        SET gemini_summary=%s,summary_time=%s,summary_model=%s
        WHERE telegram_url=%s AND main_ch_send_yn='Y'
          AND report_id = (
              SELECT MAX(report_id) FROM {self.main_table_name}
              WHERE telegram_url=%s AND main_ch_send_yn='Y'
          )
        """
        return self._execute(sql, (summary, datetime.now().isoformat(), model_name, telegram_url, telegram_url))

    async def update_report_summary(self, record_id, summary, model_name):
        sql = f"""
        UPDATE {self.main_table_name}
        SET gemini_summary=%s,summary_time=%s,summary_model=%s
        WHERE report_id=%s
        """
        return self._execute(sql, (summary, datetime.now().isoformat(), model_name, record_id))

    async def fetch_pending_summary_reports(self, limit=10):
        sql = f"""
        SELECT * FROM {self.main_table_name}
        WHERE (gemini_summary IS NULL OR gemini_summary = '')
          AND article_url IS NOT NULL AND article_url != ''
          AND sec_firm_order NOT IN (19)
        ORDER BY save_time DESC
        LIMIT %s
        """
        return self._fetchall(sql, (limit,))

    def fetch_existing_keys(self, sec_firm_order: int, days_limit: int = 7) -> set:
        """특정 증권사의 key 목록을 조회하여 반환 (중복 방지용)"""
        sql = f'SELECT key FROM {self.main_table_name} WHERE sec_firm_order = %s'
        params = [sec_firm_order]
        
        if days_limit is not None:
            cutoff = (datetime.now() - timedelta(days=days_limit)).strftime("%Y-%m-%d %H:%M:%S")
            sql += ' AND save_time >= %s'
            params.append(cutoff)
            
        rows = self._fetchall(sql, tuple(params))
        return {r["key"] for r in rows if r.get("key")}

    async def reset_send_status(self, sec_firm_order: int, date_str: str, board_order: int = None):
        """특정 증권사/날짜의 발송 상태를 초기화 (\'N\'으로 변경)"""
        params = [sec_firm_order, date_str]
        sql = f"UPDATE {self.main_table_name} SET main_ch_send_yn = 'N' WHERE sec_firm_order = %s AND DATE(save_time) = %s"
        
        if board_order is not None:
            sql += ' AND article_board_order = %s'
            params.append(board_order)
            
        return self._execute(sql, tuple(params))

    # ------------------------------------------------------------------
    # Keyword-alert — report lookup & send-user tracking
    # ------------------------------------------------------------------

    def fetch_keyword_reports(self, date: str, keyword: str, user_id: str):
        """키워드 매칭된 미발송 리포트 조회 (tbl_report_send_history에 user_id 없는 것)"""
        sql = f"""
            SELECT r.report_id, r.firm_nm, r.article_title,
                   COALESCE(NULLIF(r.telegram_url,\'\'), NULLIF(r.download_url,\'\')) AS telegram_url,
                   r.save_time
            FROM {self.main_table_name} r
            LEFT JOIN tbl_report_send_history h 
                   ON r.report_id = h.report_id AND h.user_id = %s
            WHERE (r.article_title ILIKE %s OR r.writer ILIKE %s)
              AND DATE(r.save_time) = %s
              AND h.id IS NULL
            ORDER BY r.save_time ASC, r.firm_nm ASC
        """
        keyword_param = f"%{keyword}%"
        return self._fetchall(sql, (user_id, keyword_param, keyword_param, date))

    def update_keyword_send_user(self, date: str, keyword: str, user_id: str):
        """발송 완료한 user_id를 tbl_report_send_history 테이블에 기록 (중복 방지)"""
        fetch_sql = f"""
            SELECT r.report_id 
            FROM {self.main_table_name} r
            LEFT JOIN tbl_report_send_history h 
                   ON r.report_id = h.report_id AND h.user_id = %s
            WHERE (r.article_title ILIKE %s OR r.writer ILIKE %s)
              AND DATE(r.save_time) = %s
              AND h.id IS NULL
        """
        keyword_param = f"%{keyword}%"
        reports = self._fetchall(fetch_sql, (user_id, keyword_param, keyword_param, date))
        
        inserted_count = 0
        for report in reports:
            insert_sql = """
                INSERT INTO tbl_report_send_history (report_id, user_id, keyword)
                VALUES (%s, %s, %s)
                ON CONFLICT (report_id, user_id) DO NOTHING
            """
            result = self._execute(insert_sql, (report['report_id'], user_id, keyword))
            if result["affected_rows"] > 0:
                inserted_count += result["affected_rows"]
        
        if inserted_count > 0:
            logger.info(f"[tbl_report_send_history] {inserted_count} rows inserted for user {user_id}.")
        return {"affected_rows": inserted_count}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def execute_query(self, query, params=None, close=False):
        """SQLiteManager-compatible async query helper."""
        del close
        if params:
            query = query.replace("?", "%s")
        
        if query.strip().lower().startswith("select"):
            return self._fetchall(query, params)
        return self._execute(query, params)

    def _fetchall(self, sql, params=None):
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def _execute(self, sql, params=None):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return {"status": "success", "affected_rows": cur.rowcount}
        finally:
            conn.close()
