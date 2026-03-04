import asyncio
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.SQLiteManager import SQLiteManager
from models.GeminiManager import GeminiManager
from utils.file_util import download_file_wget

async def run_batch_summary(batch_limit=10):
    print(f"🚀 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AI 요약 배치 작업을 시작합니다...")
    
    db_manager = SQLiteManager()
    # 요약이 없는 최신 레포트 목록 조회
    pending_reports = await db_manager.fetch_pending_summary_reports(limit=batch_limit)
    
    if not pending_reports:
        print("✅ 요약할 대상 레포트가 없습니다. 작업을 종료합니다.")
        return

    print(f"📋 총 {len(pending_reports)}개의 레포트 요약을 시도합니다.")
    gemini = GeminiManager() # 모델: models/gemini-2.5-flash-lite
    
    success_count = 0
    fail_count = 0

    for report in pending_reports:
        print(f"\n[작업 시작] {report['ARTICLE_TITLE']} ({report['FIRM_NM']})")
        
        # 유효한 PDF URL 확인
        download_url = report.get('ATTACH_URL') or report.get('TELEGRAM_URL') or report.get('DOWNLOAD_URL')
        # if not download_url or not ('.pdf' in download_url.lower() or '.PDF' in download_url.lower()):
        #     print(f"⚠️ 유효한 PDF URL이 아님: {download_url}")
        #     continue

        file_name = f"temp_batch_{report['id']}.pdf"
        
        try:
            # 1. PDF 다운로드
            success = await download_file_wget(report, URL=download_url, FILE_NAME=file_name)
            
            if not success or not os.path.exists(file_name) or os.path.getsize(file_name) < 1024:
                print(f"❌ 다운로드 실패 또는 파일 손상. (Size: {os.path.getsize(file_name) if os.path.exists(file_name) else 0} bytes)")
                fail_count += 1
                continue

            # 2. 제미나이 요약
            print(f"🤖 제미나이 분석 중...")
            result = await gemini.summarize_pdf(file_name)
            
            if result['status'] == 'success':
                # 3. DB 업데이트
                await db_manager.update_report_summary(
                    record_id=report['id'],
                    summary=result['summary'],
                    model_name=result['model']
                )
                print(f"✨ 요약 완료 및 DB 저장 성공!")
                success_count += 1
            else:
                print(f"❌ 요약 실패: {result.get('error')}")
                fail_count += 1
                # 쿼터 에러(429) 발생 시 전체 작업 중단하고 다음 크론탭 기약
                if "429" in str(result.get('error')):
                    print("🛑 쿼터 초과 에러 발생. 이번 배치를 중단합니다.")
                    break

            # 4. API 부하 방지를 위한 짧은 대기 (무료 티어 권장)
            await asyncio.sleep(10)

        except Exception as e:
            print(f"🔥 예기치 못한 에러 발생: {e}")
            fail_count += 1
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    print(f"\n📊 작업 종료: 성공 {success_count}, 실패 {fail_count}")

if __name__ == "__main__":
    load_dotenv()
    # 배치 제한 개수 설정 (한 번 실행 시 최대 10개)
    asyncio.run(run_batch_summary(batch_limit=10))
