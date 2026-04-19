import pytest
import asyncio
import os
import sys
import traceback
from loguru import logger

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트할 스크래퍼 함수들 임포트
from modules.LS_0 import LS_checkNewArticle
from modules.ShinHanInvest_1 import ShinHanInvest_checkNewArticle
from modules.NHQV_2 import NHQV_checkNewArticle
from modules.HANA_3 import HANA_checkNewArticle
from modules.KBsec_4 import KB_checkNewArticle
from modules.Samsung_5 import Samsung_checkNewArticle
from modules.Sangsanginib_6 import Sangsanginib_checkNewArticle
from modules.Shinyoung_7 import Shinyoung_checkNewArticle
from modules.Miraeasset_8 import Miraeasset_checkNewArticle
from modules.Hmsec_9 import Hmsec_checkNewArticle

from utils.telegram_util import send_system_alert

# 테스트 대상 리스트 (이름, 함수, 비동기여부)
SCRAPERS = [
    ("LS증권", LS_checkNewArticle, False),
    ("신한투자", ShinHanInvest_checkNewArticle, True),
    ("NH투자", NHQV_checkNewArticle, True),
    ("하나증권", HANA_checkNewArticle, True),
    ("KB증권", KB_checkNewArticle, True),
    ("삼성증권", Samsung_checkNewArticle, False),
    ("상상인", Sangsanginib_checkNewArticle, True),
    ("신영증권", Shinyoung_checkNewArticle, False),
    ("미래에셋", Miraeasset_checkNewArticle, False),
    ("현대차증권", Hmsec_checkNewArticle, False),
]

@pytest.mark.parametrize("name, func, is_async", SCRAPERS)
@pytest.mark.asyncio
async def test_scraper_health(name, func, is_async):
    """
    각 증권사 스크래퍼의 헬스 체크를 수행하고, 실패 시 상세 정보를 텔레그램으로 발송합니다.
    """
    logger.info(f"Checking health for: {name}")
    
    try:
        if is_async:
            result = await func()
        else:
            result = await asyncio.to_thread(func)
        
        assert result is not None, f"{name}: 결과가 None입니다."
        assert isinstance(result, list), f"{name}: 리스트 형식이 아닙니다."
        
        if len(result) > 0:
            sample = result[0]
            assert "ARTICLE_TITLE" in sample, f"{name}: 'ARTICLE_TITLE' 누락"
            logger.success(f"{name}: OK ({len(result)} articles)")
        else:
            logger.warning(f"{name}: OK (No data today)")

    except Exception as e:
        # 에러의 상세 스택 트레이스 추출 (마지막 3줄)
        tb = traceback.format_exc()
        # 텔레그램 메시지용으로 가공
        error_msg = f"❌ **{name} 스크래퍼 점검 필요!**\n\n"
        error_msg += f"**에러:** `{str(e)}`\n"
        error_msg += f"**위치:**\n```{tb[-300:]}```" # 너무 길면 잘림 방지
        
        await send_system_alert(error_msg)
        pytest.fail(error_msg)
