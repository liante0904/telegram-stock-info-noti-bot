import pytest
import asyncio
import os
import sys
import traceback
from loguru import logger

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 텔레그램 알림용
from utils.telegram_util import send_system_alert

# 모든 스크래퍼 모듈 동적 임포트 테스트 및 리스트업
def get_all_scrapers():
    scrapers = [
        ("LS증권", "modules.LS_0", "LS_checkNewArticle", False),
        ("신한투자", "modules.ShinHanInvest_1", "ShinHanInvest_checkNewArticle", True),
        ("NH투자", "modules.NHQV_2", "NHQV_checkNewArticle", True),
        ("하나증권", "modules.HANA_3", "HANA_checkNewArticle", True),
        ("KB증권", "modules.KBsec_4", "KB_checkNewArticle", True),
        ("삼성증권", "modules.Samsung_5", "Samsung_checkNewArticle", False),
        ("상상인", "modules.Sangsanginib_6", "Sangsanginib_checkNewArticle", True),
        ("신영증권", "modules.Shinyoung_7", "Shinyoung_checkNewArticle", False),
        ("미래에셋", "modules.Miraeasset_8", "Miraeasset_checkNewArticle", False),
        ("현대차증권", "modules.Hmsec_9", "Hmsec_checkNewArticle", False),
        ("키움증권", "modules.Kiwoom_10", "Kiwoom_checkNewArticle", False),
        ("대신증권", "modules.Daeshin_17", "Daeshin_checkNewArticle", False),
        ("DB금융투자", "modules.DBfi_19", "DBfi_checkNewArticle", True),
        ("유진투자", "modules.eugenefn_12", "eugenefn_checkNewArticle", False),
        ("한국투자", "modules.Koreainvestment_13", "Koreainvestment_checkNewArticle", False),
        ("다올투자", "modules.DAOL_14", "DAOL_checkNewArticle", True),
        ("토스증권", "modules.TOSSinvest_15", "TOSS_checkNewArticle", True),
        ("리딩투자", "modules.Leading_16", "Leading_checkNewArticle", True),
        ("iM증권", "modules.iMfnsec_18", "iM_checkNewArticle", True),
        ("메리츠", "modules.MERITZ_20", "Meritz_checkNewArticle", True),
        ("한화투자", "modules.Hanwhawm_21", "Hanwha_checkNewArticle", True),
        ("한양증권", "modules.Hygood_22", "Hanyang_checkNewArticle", True),
        ("BNK투자", "modules.BNKfn_23", "BNK_checkNewArticle", True),
        ("교보증권", "modules.Kyobo_24", "Kyobo_checkNewArticle", True),
        ("IBK투자", "modules.IBKs_25", "IBK_checkNewArticle", True),
        ("SK증권", "modules.SKS_26", "SK_checkNewArticle", True),
        ("유안타증권", "modules.Yuanta_27", "Yuanta_checkNewArticle", True),
    ]
    return scrapers

@pytest.mark.parametrize("name, mod_path, func_name, is_async", get_all_scrapers())
@pytest.mark.asyncio
async def test_scraper_health(name, mod_path, func_name, is_async):
    """
    각 증권사 스크래퍼의 임포트 및 헬스 체크를 수행합니다.
    """
    logger.info(f"Checking health for: {name} ({mod_path})")
    
    try:
        # 1. 임포트 테스트 (KeyError 등 초기화 에러 잡기)
        import importlib
        module = importlib.import_module(mod_path)
        func = getattr(module, func_name)
        
        # 2. 실행 테스트 (네트워크/구조 에러 잡기)
        if is_async:
            result = await func()
        else:
            result = await asyncio.to_thread(func)
        
        assert result is not None, f"{name}: 결과가 None입니다."
        assert isinstance(result, list), f"{name}: 리스트 형식이 아닙니다."
        
        logger.success(f"{name}: OK ({len(result)} articles)")

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"{name} 헬스체크 실패:\n{tb}")
        
        # 실제 운영 환경일 때만 알림 발송 (테스트 시 소음 방지)
        if os.getenv('ENV') == 'prod':
            error_msg = f"❌ **{name} 스크래퍼 점검 필요!**\n\n"
            error_msg += f"**에러:** `{str(e)}`\n"
            error_msg += f"**위치:**\n```{tb[-300:]}```"
            await send_system_alert(error_msg)
            
        pytest.fail(f"{name} failed: {str(e)}")
