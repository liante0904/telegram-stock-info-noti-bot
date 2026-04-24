import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import modules.ShinHanInvest_1 as shinhan_current


@pytest.mark.asyncio
async def test_shinhan_mobile_parses_article_and_preserves_db_shape(monkeypatch):
    api_response = {
        "header": {
            "succesCode": "0",
            "resultCode": "00000",
            "resultMsg": "정상적으로 처리되었습니다.",
            "repeatKeyP": "",
            "repeatKeyN": "20",
        },
        "body": {
            "list01": {
                "outputList": [
                    {
                        "date": "20260422083319",
                        "category": "Daily 신한생각",
                        "title": "시황: K-버튜버 시장 투자해도 된다",
                        "nickname": "박석중",
                        "attachment_url": "http://bbs2.shinhaninvest.com/board/message/file.do?attachmentId=8072",
                        "bbs_name": "gicomment",
                        "message_id": "8072",
                        "message_url": "http://bbs2.shinhaninvest.com/mobile/view.do?boardName=gicomment&messageId=935312&messageNumber=8072",
                    }
                ]
            }
        }
    }

    async def fake_fetch_mobile_api(session, url):
        return api_response

    monkeypatch.setattr(shinhan_current, "_fetch_mobile_api", fake_fetch_mobile_api)

    rows = await shinhan_current.ShinHanInvest_checkNewArticle()

    assert len(rows) == 1
    row = rows[0]
    assert row["SEC_FIRM_ORDER"] == 1
    assert row["ARTICLE_BOARD_ORDER"] == 7
    assert row["FIRM_NM"]
    assert row["REG_DT"] == "20260422"
    assert row["ARTICLE_TITLE"] == "시황: K-버튜버 시장 투자해도 된다"
    assert row["WRITER"] == "박석중"
    assert row["ARTICLE_URL"] == "https://bbs2.shinhansec.com/mobile/view.do?boardName=gicomment&messageId=935312&messageNumber=8072"
    assert row["KEY"] == "https://bbs2.shinhansec.com/board/message/file.pdf.do?attachmentId=8072"
    assert row["DOWNLOAD_URL"].endswith("attachmentId=8072")
    assert row["TELEGRAM_URL"].endswith("attachmentId=8072")
    assert row["PDF_URL"].endswith("attachmentId=8072")
    assert "SAVE_TIME" in row


@pytest.mark.asyncio
async def test_shinhan_mobile_falls_back_to_html(monkeypatch):
    async def fake_fetch_mobile_api(session, url):
        raise RuntimeError("api down")

    html = """
    <html>
      <body>
        <a href="/mweb/invt/shrh/ishrh1001?tabIdx=1&subTabIdx=&message_id=8072">
          시황: K-버튜버 시장 투자해도 된다
        </a>
      </body>
    </html>
    """

    async def fake_fetch_mobile_page(session, url):
        return html

    async def fake_resolve_pdf_url(session, article_url):
        return "https://bbs2.shinhansec.com/board/message/file.pdf.do?attachmentId=8072"

    monkeypatch.setattr(shinhan_current, "_fetch_mobile_api", fake_fetch_mobile_api)
    monkeypatch.setattr(shinhan_current, "_fetch_mobile_page", fake_fetch_mobile_page)
    monkeypatch.setattr(shinhan_current, "_resolve_pdf_url", fake_resolve_pdf_url)

    rows = await shinhan_current.ShinHanInvest_checkNewArticle()

    assert len(rows) == 1
    assert rows[0]["KEY"].endswith("attachmentId=8072")
