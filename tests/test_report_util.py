import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.report_util import get_report_messages


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
