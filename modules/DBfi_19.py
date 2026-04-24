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
DBFI_KEY_LOOKBACK_DAYS = int(os.getenv("DBFI_KEY_LOOKBACK_DAYS", "3650"))
DBFI_DETAIL_MAX_KEYS = int(os.getenv("DBFI_DETAIL_MAX_KEYS", "0"))
HEADERS_TEMPLATE = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}

# SSL 검증 완전히 비활성화
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers("DEFAULT")


async def extract_dbfi_pdf_url(session, encoded_url):
    """
    DB증권 gate 토큰에서 실제 PDF 다운로드 URL을 추출합니다.

    흐름:
    1) /pv/auth 로 세션 쿠키 발급
    2) /pv/viewer 로 진입
    3) hidden .item 의 id를 docId로 추출
    4) /streamdocs/v4/documents/{docId} 형태의 PDF URL 반환
    """
    if not encoded_url:
        return None

    token = urlparse.unquote(encoded_url)
    gate_q = urlparse.quote(token, safe="")
    gate_url = f"https://whub.dbsec.co.kr/pv/gate?q={gate_q}"

    pv_headers = {
        "User-Agent": HEADERS_TEMPLATE["User-Agent"],
        "Content-Type": HEADERS_TEMPLATE["Content-Type"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": gate_url,
    }

    try:
        # Session-level auth cookie is reusable across multiple viewer requests.
        if not getattr(session, "_dbfi_auth_done", False):
            async with session.post("https://whub.dbsec.co.kr/pv/auth", headers=pv_headers) as auth_response:
                await auth_response.text()
            setattr(session, "_dbfi_auth_done", True)

        viewer_payload = {
            "q": token,
            "c": "",
            "target": "",
            "docId": "",
        }
        async with session.post(
            "https://whub.dbsec.co.kr/pv/viewer",
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
            pdf_url = f"https://whub.dbsec.co.kr/streamdocs/v4/documents/{doc_id}"
            return {
                "gate_url": gate_url,
                "viewer_url": "https://whub.dbsec.co.kr/pv/viewer",
                "doc_id": doc_id,
                "file_name": file_name,
                "pdf_url": pdf_url,
            }
    except Exception as e:
        logger.error(f"DBfi: Failed to extract PDF URL: {e}")
        return None


# DB금융투자 기사 체크 함수
async def DBfi_checkNewArticle():
    SEC_FIRM_ORDER = 19
    urls = [
        "/appData/rsh_entr_lst.json",
        "/appData/rsh_bond_lst.json",
        "/appData/rsh_stock_lst.json"
    ]
    json_data_list = []

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=timeout) as session:
        for ARTICLE_BOARD_ORDER, url_path in enumerate(urls):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            headers = {
                **HEADERS_TEMPLATE,
                "Referer": f"{BASE_URL}/mre/mre_CompanyAll_lst.do",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }

            logger.debug(f"DBfi Scraper Start: {firm_info.get_firm_name()} path {url_path}")
            try:
                async with session.post(f"{BASE_URL}{url_path}", headers=headers) as response:
                    if response.status == 200:
                        try:
                            jres = await response.json()
                            data_items = jres.get("data", [])
                            logger.info(f"DBfi Scraper: Found {len(data_items)} items for {url_path}")
                        except (json.JSONDecodeError, KeyError):
                            logger.warning(f"No items found or JSON error for URL {url_path}.")
                            continue

                        for item in data_items:
                            detail_url = f"{BASE_URL}/appData/descRsh/{item['rid']}.json"
                            json_data_list.append({
                                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                                "FIRM_NM": firm_info.get_firm_name(),
                                "REG_DT": item['rdt'][:8],
                                "ARTICLE_URL": "",
                                "TELEGRAM_URL": "",
                                "PDF_URL": "",
                                "ARTICLE_TITLE": item['tit'],
                                "WRITER": item['wnm'],
                                "CATEGORY": item['div'],
                                "KEY": detail_url,
                                "SAVE_TIME": datetime.now().isoformat()
                            })
                    else:
                        logger.warning(f"Failed to fetch page data for URL {url_path}. Status code: {response.status}")
            except Exception as e:
                logger.error(f"Network or timeout error while fetching {url_path}: {e}")

    return json_data_list


# 상세 URL로 후처리 데이터 획득 함수
async def fetch_detailed_url(articles):
    def _extract_rid_from_key(key_url: str) -> int:
        m = re.search(r"/descRsh/(\d+)\.json", key_url or "")
        return int(m.group(1)) if m else -1

    existing_keys = set()
    try:
        db = get_db()
        if hasattr(db, "fetch_all_keys"):
            existing_keys = await db.fetch_all_keys(sec_firm_order=19)
            logger.info("DBfi: loaded {} existing keys from DB (all)", len(existing_keys))
        elif hasattr(db, "fetch_recent_keys"):
            existing_keys = await db.fetch_recent_keys(sec_firm_order=19, days_limit=DBFI_KEY_LOOKBACK_DAYS)
            logger.info(
                "DBfi: loaded {} existing keys from DB ({} days, fallback)",
                len(existing_keys),
                DBFI_KEY_LOOKBACK_DAYS,
            )
    except Exception as e:
        logger.warning(f"DBfi: failed to load recent keys, fallback to full scan: {e}")

    max_existing_rid = max((_extract_rid_from_key(k) for k in existing_keys), default=-1)

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=timeout) as session:
        # Group by KEY to avoid repeated detail/API requests for duplicates.
        pending_by_key = {}
        skipped_existing = 0
        for article in articles:
            if article.get("TELEGRAM_URL") and article.get("PDF_URL"):
                continue
            key_url = article.get("KEY")
            if not key_url:
                continue
            rid = _extract_rid_from_key(key_url)
            if max_existing_rid > 0 and rid > 0 and rid <= max_existing_rid:
                skipped_existing += 1
                continue
            if key_url in existing_keys:
                skipped_existing += 1
                continue
            pending_by_key.setdefault(key_url, []).append(article)

        encoded_url_cache = {}
        extracted_cache = {}
        logger.info(
            "DBfi: detail enrichment targets={} unique_keys={} skipped_existing={}",
            sum(len(v) for v in pending_by_key.values()),
            len(pending_by_key),
            skipped_existing,
        )

        if DBFI_DETAIL_MAX_KEYS > 0 and len(pending_by_key) > DBFI_DETAIL_MAX_KEYS:
            def _key_sort_score(url: str):
                m = re.search(r"/descRsh/(\d+)\.json", url or "")
                return int(m.group(1)) if m else -1

            sorted_keys = sorted(pending_by_key.keys(), key=_key_sort_score, reverse=True)
            keep_keys = set(sorted_keys[:DBFI_DETAIL_MAX_KEYS])
            dropped = len(pending_by_key) - len(keep_keys)
            pending_by_key = {k: v for k, v in pending_by_key.items() if k in keep_keys}
            logger.warning(
                "DBfi: detail key cap applied. keeping={} dropped={} (DBFI_DETAIL_MAX_KEYS={})",
                len(pending_by_key),
                dropped,
                DBFI_DETAIL_MAX_KEYS,
            )

        for key_url, key_articles in pending_by_key.items():
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
                gate_url = extracted["gate_url"]
                for article in key_articles:
                    article["TELEGRAM_URL"] = gate_url
                    article["ARTICLE_URL"] = gate_url
                    article["PDF_URL"] = pdf_url
                    article["FILE_NAME"] = extracted["file_name"]
                    article["DOC_ID"] = extracted["doc_id"]
                    article["GATE_URL"] = gate_url
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
