import asyncio
import sys
import os

# 현재 디렉토리를 sys.path에 추가
sys.path.append(os.getcwd())

from modules.LS_0 import LS_checkNewArticle

def test_ls():
    print("LS_checkNewArticle 실행 중...")
    try:
        articles = LS_checkNewArticle(page=1)
        print(f"발견된 게시글 수: {len(articles)}")
        if articles:
            for article in articles[:3]:
                print(f"- 제목: {article['article_title']}, 날짜: {article['reg_dt']}")
        else:
            print("게시글이 발견되지 않았습니다.")
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    test_ls()
