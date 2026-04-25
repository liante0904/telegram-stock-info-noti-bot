import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.report_util import get_report_messages
from utils.PostgreSQL_util import build_sql_telegram_message_query


def test_get_report_messages_uses_db_backend_sqlite(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "sqlite")

    rows = [
        {
            "SEC_FIRM_ORDER": 11,
            "FIRM_NM": "DS투자증권",
            "ARTICLE_TITLE": "테스트 리포트",
            "TELEGRAM_URL": "https://ssh-oci.netlify.app/share?id=231973064",
            "PDF_URL": "https://example.com/report.pdf",
        }
    ]

    messages = get_report_messages(rows)

    assert len(messages) == 1
    assert "[공유](https://ssh-oci.netlify.app/share?id=231973064)" in messages[0]
    assert "[원본](https://example.com/report.pdf)" in messages[0]


def test_get_report_messages_uses_db_backend_postgres(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "postgres")

    rows = [
        {
            "SEC_FIRM_ORDER": 11,
            "FIRM_NM": "DS투자증권",
            "ARTICLE_TITLE": "테스트 리포트",
            "TELEGRAM_URL": "https://ssh-oci.netlify.app/share?id=231973064",
            "PDF_URL": "https://example.com/report.pdf",
        }
    ]

    messages = get_report_messages(rows)

    assert len(messages) == 1
    assert "[공유](https://ssh-oci.netlify.app/share?id=231973064)" in messages[0]
    assert "[원본](https://example.com/report.pdf)" in messages[0]


def test_get_report_messages_supports_postgres_v2_lowercase_rows(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "postgres")

    rows = [
        {
            "sec_firm_order": 11,
            "firm_nm": "DS투자증권",
            "article_title": "테스트 리포트",
            "telegram_url": "https://ssh-oci.netlify.app/share?id=231973064",
            "pdf_url": "https://example.com/report.pdf",
        }
    ]

    messages = get_report_messages(rows)

    assert len(messages) == 1
    assert "[공유](https://ssh-oci.netlify.app/share?id=231973064)" in messages[0]
    assert "[원본](https://example.com/report.pdf)" in messages[0]


def test_build_sql_telegram_message_query_supports_v2_schema():
    query, params = build_sql_telegram_message_query(schema_version="v2")

    assert params == []
    assert "FROM tb_sec_reports_v2" in query
    assert "DATE(save_time) = CURRENT_DATE" in query
    assert "AND main_ch_send_yn = 'Y'" in query
    assert '"TB_SEC_REPORTS"' not in query
    assert '"SAVE_TIME"' not in query
