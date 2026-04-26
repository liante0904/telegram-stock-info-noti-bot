import asyncio
import aiohttp
import json
import ssl
import re
from datetime import datetime
import os
import sys
import urllib.parse as urlparse
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config
from models.db_factory import get_db

BASE_URL = config.get_urls("DBfi_19")[0]
VIEWER_BASE = config.get_urls("DBfi_19")[1]
HEADERS_TEMPLATE = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers("DEFAULT")


async def extract_dbfi_pdf_url(session, encoded_url):
    """
    DB증권 gate 토큰에서 실제 PDF 다운로드 URL을 추출합니다.

    흐름:
    1) __DBFI_AUTH_PATH__ 로 세션 쿠키 발급
    2) __DBFI_VIEWER_PATH__ 로 진입
    3) hidden .item 의 id를 docId로 추출
    4) /streamdocs/v4/documents/{docId} 형태의 PDF URL 반환
    """
    if not encoded_url:
        return None

    token = urlparse.unquote(encoded_url)
    gate_q = urlparse.quote(token, safe="")
    gate_url = f"{VIEWER_BASE}__DBFI_GATE_PATH__?q={gate_q}"

    pv_headers = {
        "User-Agent": HEADERS_TEMPLATE["User-Agent"],
        "Content-Type": HEADERS_TEMPLATE["Content-Type"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": gate_url,
    }

    try:
        async with session.post(f"{VIEWER_BASE}__DBFI_AUTH_PATH__", headers=pv_headers) as auth_response:
            await auth_response.text()

        viewer_payload = {
            "q": token,
            "c": "",
            "target": "",
            "docId": "",
        }
        async with session.post(
            f"{VIEWER_BASE}__DBFI_VIEWER_PATH__",
            headers=pv_headers,
            data=viewer_payload,
        ) as viewer_response:
            if viewer_response.status != 200:
                logger.warning(f"DBfi: viewer request failed ({viewer_response.status})")
                return None

            viewer_html = await viewer_response.text()
            match = re.search(r'<div[^>]*id="([^"]+)"[^>]*class="item"', viewer_html)
            if not match:
                match = re.search(r'<div[^>]*class="item"[^>]*id="([^"]+)"', viewer_html)

            if not match:
                logger.warning("DBfi: Could not find StreamDocs document id in viewer HTML")
                return None

            doc_id = match.group(1)
            title_match = re.search(
                rf'<div[^>]*id="{re.escape(doc_id)}"[^>]*class="item"[^>]*>\s*<span>(.*?)</span>',
                viewer_html,
                flags=re.S,
            )
            file_name = title_match.group(1).strip() if title_match else "리서치"
            pdf_url = f"{VIEWER_BASE}__DBFI_DOCUMENT_PATH_TEMPLATE__"
            return {
                "gate_url": gate_url,
                "viewer_url": f"{VIEWER_BASE}__DBFI_VIEWER_PATH__",
                async def extract_dbfi_pdf_url(session, encoded_url):
                    """
                    DB증권 gate 토큰에서 실제 PDF 다운로드 URL을 추출합니다.
                ...
                    except Exception as e:
                        logger.error(f"DBfi: Failed to extract PDF URL: {e}")
                        return None


                async def DBfi_checkNewArticle():
                    SEC_FIRM_ORDER = 19
                    url_paths = [
                        ("__DBFI_LIST_PATH_ENTR__", 0),
                        ("__DBFI_LIST_PATH_BOND__", 1),
                        ("__DBFI_LIST_PATH_STOCK__", 2),
                    ]

                    # 1. 우리 DB 최근 7일 KEY 조회 (PostgreSQLManager 공통 메서드 사용)
                    db = get_db()
                    existing_keys = db.fetch_existing_keys(SEC_FIRM_ORDER, days_limit=7)
                    logger.info(f"DBfi: DB에 기존 KEY {len(existing_keys)}개 (최근 7일)")

                    # 2. 서버 목록 스크랩

    timeout = aiohttp.ClientTimeout(total=15)
    candidates = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=timeout) as session:
        for url_path, board_order in url_paths:
            firm_info = FirmInfo(sec_firm_order=SEC_FIRM_ORDER, article_board_order=board_order)
            headers = {
                **HEADERS_TEMPLATE,
                "Referer": f"{BASE_URL}__DBFI_LIST_REFERER_PATH__",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            }
            try:
                async with session.post(f"{BASE_URL}{url_path}", headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"DBfi: 목록 조회 실패 {url_path} ({response.status})")
                        continue
                    jres = await response.json()
                    items = jres.get("data", [])[:50]
                    logger.info(f"DBfi: {url_path} → {len(items)}건 (최근 50건)")

                    # 3. 신규 항목만 추출 (서버 - DB)
                    for item in items:
                        key = f"{BASE_URL}__DBFI_DETAIL_PATH_TEMPLATE__"
                        if key in existing_keys:
                            continue
                        candidates.append({
                            "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                            "ARTICLE_BOARD_ORDER": board_order,
                            "FIRM_NM": firm_info.get_firm_name(),
                            "REG_DT": item["rdt"][:8],
                            "ARTICLE_URL": "",
                            "TELEGRAM_URL": "",
                            "PDF_URL": "",
                            "ARTICLE_TITLE": item["tit"],
                            "WRITER": item["wnm"],
                            "CATEGORY": item["div"],
                            "KEY": key,
                            "SAVE_TIME": datetime.now().isoformat(),
                        })
            except Exception as e:
                logger.error(f"DBfi: {url_path} 네트워크 오류: {e}")

    logger.info(f"DBfi: 신규 {len(candidates)}건 (중복 제거 후)")
    if not candidates:
        return []

    # 4. 신규에 대해서만 상세 POST 처리 (PDF URL 추출)
    return await fetch_detailed_url(candidates)


# 상세 URL로 후처리 데이터 획득 함수
async def fetch_detailed_url(articles):
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    def _article_signature(article: dict) -> tuple[str, str, str, str]:
        # DB증권은 동일 리포트가 여러 게시판에 중복 노출되는 경우가 있어
        # 제목/작성자/등록일/카테고리 기준으로 대표 건만 상세 조회합니다.
        return (
            _normalize_text(article.get("REG_DT", "")),
            _normalize_text(article.get("ARTICLE_TITLE", "")),
            _normalize_text(article.get("WRITER", "")),
            _normalize_text(article.get("CATEGORY", "")),
        )

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=timeout) as session:
        # Group by article signature first, then choose a single representative KEY
        # to avoid hitting detail endpoints for the same report multiple times.
        pending_by_signature = {}
        skipped_existing = 0
        collapsed_duplicates = 0
        for article in articles:
            if article.get("TELEGRAM_URL") and article.get("PDF_URL"):
                continue
            key_url = article.get("KEY")
            if not key_url:
                continue
            signature = _article_signature(article)
            bucket = pending_by_signature.setdefault(
                signature,
                {"representative_key": key_url, "articles": [], "keys": set()},
            )
            if bucket["articles"]:
                collapsed_duplicates += 1
            bucket["keys"].add(key_url)
            bucket["articles"].append(article)

        encoded_url_cache = {}
        extracted_cache = {}
        representative_items = list(pending_by_signature.values())
        logger.info(
            "DBfi: detail enrichment targets={} representative_keys={} skipped_existing={} collapsed_duplicates={}",
            sum(len(item["articles"]) for item in representative_items),
            len(representative_items),
            skipped_existing,
            collapsed_duplicates,
        )

        for item in representative_items:
            key_url = item["representative_key"]
            key_articles = item["articles"]
            try:
                encoded_url = encoded_url_cache.get(key_url)
                if not encoded_url:
                    async with session.post(key_url, headers=HEADERS_TEMPLATE) as response:
                        if response.status != 200:
                            logger.warning(f"Failed to fetch details from {key_url}. Status code: {response.status}")
                            continue
                        try:
                            detail_data = await response.json()
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON for {key_url}")
                            continue
                        encoded_url = detail_data.get("data", {}).get("url", "")
                        encoded_url_cache[key_url] = encoded_url

                if not encoded_url:
                    logger.warning(f"DBfi: Empty document id for {key_url}")
                    continue

                extracted = extracted_cache.get(encoded_url)
                if extracted is None:
                    extracted = await extract_dbfi_pdf_url(session, encoded_url)
                    extracted_cache[encoded_url] = extracted

                if not extracted:
                    logger.warning(f"DBfi: PDF URL extraction failed for {key_url}")
                    continue

                pdf_url = extracted["pdf_url"]
                for article in key_articles:
                    article["TELEGRAM_URL"] = pdf_url
                    article["PDF_URL"] = pdf_url
                    article["FILE_NAME"] = extracted["file_name"]
                    article["DOC_ID"] = extracted["doc_id"]
                    article["GATE_URL"] = extracted["gate_url"]
                    article["VIEWER_URL"] = extracted["viewer_url"]
                logger.info(
                    "DBfi: key={} affected={} file={} docId={} pdf={}",
                    key_url,
                    len(key_articles),
                    extracted["file_name"],
                    extracted["doc_id"],
                    pdf_url,
                )
            except Exception as e:
                logger.error(f"Network or timeout error while fetching detailed URL ({key_url}): {e}")

    return articles


async def main():
    articles = await DBfi_checkNewArticle()
    detailed_articles = await fetch_detailed_url(articles)
    logger.info(f"Fetched total {len(detailed_articles)} detailed articles.")
    for article in detailed_articles[:5]:
        logger.info(
            "DBfi sample | title={} | file={} | pdf={}",
            article.get("ARTICLE_TITLE"),
            article.get("FILE_NAME"),
            article.get("PDF_URL"),
        )


if __name__ == "__main__":
    asyncio.run(main())
