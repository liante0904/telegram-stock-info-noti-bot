import asyncio
import aiohttp
import sys
import os
from loguru import logger
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# fix 스크립트 실행 시 msg.ls-sec.co.kr 탐색 범위를 ±5일로 설정 (작성일 기준 대부분 수렴)
os.environ["LS_SEARCH_DAYS"] = "5"

from models.db_factory import get_db
from modules.LS_0 import LS_detail, LS_checkNewArticle

async def fix_ls_urls():
    db = get_db()
    
    # 1. 대상 데이터 추출 (upload/ fallback + 빈 문자열)
    # 최근 30일치 위주로 먼저 확인
    query = """
        SELECT report_id, "article_title", "writer", "telegram_url", "article_url", "reg_dt", "key"
        FROM "tbl_sec_reports"
        WHERE "firm_nm" = 'LS증권'
          AND ("telegram_url" LIKE 'https://www.ls-sec.co.kr/upload/%'
               OR "telegram_url" IS NULL OR "telegram_url" = '')
          AND "key" IS NOT NULL AND "key" != ''
        ORDER BY "save_time" DESC
        LIMIT 500
    """
    
    records = await db.execute_query(query)
    total = len(records)
    upload_count = sum(1 for r in records if r.get('telegram_url', '').startswith('https://www.ls-sec.co.kr/upload/'))
    empty_count = total - upload_count
    logger.info(f"복구 대상: {total}건 (upload/ fallback {upload_count}건, 빈 문자열 {empty_count}건)")
    
    if total == 0:
        logger.info("복구할 데이터가 없습니다.")
        return

    # 상세 페이지 재파싱 및 정적 URL 탐색 진행
    # LS_detail 함수는 내부적으로 get_valid_url(±60일)을 호출함 (fix 전용 확대 범위)
    logger.info(f"상세 페이지 재접속 및 정적 URL(msg.) 탐색을 시작합니다... (탐색 범위: ±5일)")
    
    # LS_detail은 리스트를 받아서 내부 필드를 수정함
    # report_id 매핑을 위해 dict 형태로 유지
    updated_count = 0
    
    # 한 번에 너무 많이 하면 차단될 수 있으므로 청크 단위로 진행
    chunk_size = 10
    for i in range(0, total, chunk_size):
        chunk = records[i:i+chunk_size]
        logger.info(f"Processing chunk {i//chunk_size + 1}/{(total+chunk_size-1)//chunk_size}...")
        
        # LS_detail 호출
        results = await LS_detail(chunk)
        
        for article in results:
            new_url = article.get('telegram_url', '')
            # 정적 URL(msg.)로 변경되었는지 확인
            if new_url.startswith('https://msg.ls-sec.co.kr/'):
                success = await db.update_telegram_url(
                    record_id=article['report_id'],
                    telegram_url=new_url,
                    article_title=article['article_title'],
                    pdf_url=new_url
                )
                if success:
                    logger.success(f"복구 완료: {article['article_title']} -> {new_url}")
                    updated_count += 1
                else:
                    logger.error(f"DB 업데이트 실패: {article['article_title']}")
            else:
                logger.warning(f"복구 실패 (여전히 Fallback): {article['article_title']}")
        
        # LS 서버 부하 방지 및 차단 회피를 위한 대기 (이미 LS_detail 내부에 sleep이 있지만 추가 확보)
        await asyncio.sleep(1)

    logger.info("=" * 50)
    logger.info(f"LS URL 복구 작업 완료")
    logger.info(f"- 전체 대상: {total}건")
    logger.info(f"- 복구 성공: {updated_count}건")
    logger.info("=" * 50)

if __name__ == "__main__":
    asyncio.run(fix_ls_urls())
