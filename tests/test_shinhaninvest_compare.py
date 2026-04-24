import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import modules.ShinHanInvest_1 as shinhan_current
import modules.ShinHanInvest_1_legacy as shinhan_legacy


LEGACY_RESPONSE = {
    "body": {
        "collectionList": [
            {
                "itemList": [
                    {
                        "BOARD_NAME": "gicomment",
                        "REG_DT": "20260801123000",
                        "ATTACHMENT_ID": "8072",
                        "TITLE": "시황: K-버튜버 시장 투자해도 된다",
                        "REGISTER_NICKNAME": "박석중",
                    }
                ]
            }
        ]
    }
}

PDF_URL = "https://bbs2.shinhansec.com/board/message/file.pdf.do?attachmentId=8072"
ARTICLE_URL = "https://bbs2.shinhansec.com/mobile/view.do?boardName=gicomment&messageId=935312&messageNumber=8072"


class _FakeLegacyResponse:
    status = 200

    async def json(self):
        return LEGACY_RESPONSE


class _FakeLegacyPostContext:
    async def __aenter__(self):
        return _FakeLegacyResponse()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeLegacySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        return _FakeLegacyPostContext()


@pytest.mark.asyncio
async def test_shinhan_legacy_and_current_mobile_compare_same_core_fields(monkeypatch):
    async def fake_fetch_mobile_api(session, url):
        return {
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
                            "date": "20260801123000",
                            "category": "Daily 신한생각",
                            "title": "시황: K-버튜버 시장 투자해도 된다",
                            "nickname": "박석중",
                            "attachment_url": "http://bbs2.shinhaninvest.com/board/message/file.do?attachmentId=8072",
                            "bbs_name": "gicomment",
                            "message_id": "8072",
                            "message_url": ARTICLE_URL,
                        }
                    ]
                }
            }
        }

    monkeypatch.setattr(shinhan_legacy.aiohttp, "ClientSession", _FakeLegacySession)
    monkeypatch.setattr(shinhan_current, "_fetch_mobile_api", fake_fetch_mobile_api)

    legacy_rows = await shinhan_legacy.ShinHanInvest_checkNewArticle()
    new_rows = await shinhan_current.ShinHanInvest_checkNewArticle()

    assert len(legacy_rows) == 1
    assert len(new_rows) == 1

    legacy_row = legacy_rows[0]
    new_row = new_rows[0]

    # DB 공통 필드만 비교한다.
    comparable_fields = [
        "SEC_FIRM_ORDER",
        "ARTICLE_BOARD_ORDER",
        "FIRM_NM",
        "REG_DT",
        "ARTICLE_TITLE",
        "WRITER",
        "DOWNLOAD_URL",
        "TELEGRAM_URL",
        "PDF_URL",
        "KEY",
    ]

    for field in comparable_fields:
        assert legacy_row[field] == new_row[field], field

    # 신규 모바일 모듈은 상세 URL을 추가로 보존한다.
    assert new_row["ARTICLE_URL"] == ARTICLE_URL
    assert legacy_row.get("ARTICLE_URL") is None
