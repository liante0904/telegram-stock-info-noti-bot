# -*- coding:utf-8 -*-
import asyncio
import gc
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.ConfigManager import config
from models.FirmInfo import FirmInfo


MOBILE_LIST_URL = "https://m.shinhansec.com/mweb/invt/shrh/ishrh1001?tabIdx=0"
MOBILE_API_URL = "https://m.shinhansec.com/mweb/api/invt/shrh/ishrhShrhList"

# Match the legacy module's board order exactly when a board code is present.
BOARD_MAP = {
    "giindustry": 0,        # 산업분석
    "gicompanyanalyst": 1,  # 기업분석
    "giresearchIPO": 2,     # 스몰캡
    "foreignstock": 3,      # 해외 주식
    "alternative": 4,       # 대체투자
    "foreignbond": 5,       # 해외 채권
    "gibond": 6,            # 채권/신용분석
    "gicomment": 7,         # 주식전략/시황
    "gieconomy": 8,         # 경제
    "gifuture": 9,          # 기술적분석/파생시황
    "gigoodpolio": 10,      # 주식 포트폴리오
    "giperiodicaldaily": 11,# Daily 신한생각
    "issuebroker": 12,      # 의무리포트
    "shinhannews": 13,      # 신한 속보
    "gistockchart": 11,     # Daily 계열
    "plananalysis": 10,     # 기획분석
    "fxmarket": 8,          # 경제/외환
    "commodity": 8,         # 경제/외환
    "gifund2": 4,           # 대체자산
}


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_reg_dt(value: str) -> str:
    if not value:
        return ""
    value = str(value).strip()
    value = value.replace("년", "-").replace("월", "-").replace("일", "")
    value = re.sub(r"[^0-9]", "", value)
    if len(value) >= 8:
        return value[:8]
    return value


def _first_non_empty(*values: Optional[str]) -> str:
    for value in values:
        if value:
            stripped = str(value).strip()
            if stripped:
                return stripped
    return ""


def _abs_url(base_url: str, href: str) -> str:
    if not href:
        return ""
    return urljoin(base_url, href)


def _extract_message_id(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("message_id", [""])[0] or query.get("messageId", [""])[0]


def _resolve_board_order(board_code: str = "", text: str = "", url: str = "") -> int:
    board_code = str(board_code or "").strip()
    if board_code and board_code in BOARD_MAP:
        return BOARD_MAP[board_code]

    # Fallback only when the page exposes human-readable board labels or codes.
    haystack = f"{text} {url}"
    for code, board_order in BOARD_MAP.items():
        if code in haystack:
            return board_order
    return 99


def _looks_like_pdf(url: str) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return ".pdf" in lowered or "file.pdf.do" in lowered or "download" in lowered


def _extract_header_writer(soup: BeautifulSoup) -> str:
    page_text = _normalize_text(soup.get_text(" ", strip=True))
    m = re.search(r"([가-힣A-Za-z0-9._-]+)님의 분석자료", page_text)
    if m:
        return m.group(1).strip()
    return ""


def _collect_article_candidates_from_html(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    seen: set = set()
    page_writer = _extract_header_writer(soup)

    for anchor in soup.select('a[href*="message_id="], a[href*="messageId="]'):
        href = anchor.get("href", "")
        article_url = _abs_url(base_url, href)
        key = article_url or href
        if not key or key in seen:
            continue

        container = anchor.find_parent(["li", "article", "div", "tr"]) or anchor.parent
        container_text = _normalize_text(container.get_text(" ", strip=True) if container else "")
        anchor_text = _normalize_text(anchor.get_text(" ", strip=True))
        title = _first_non_empty(anchor_text)

        # Try common title tags around the link.
        if not title and container:
            title_node = container.find(["strong", "h2", "h3", "h4", "dt", "p"])
            if title_node:
                title = _normalize_text(title_node.get_text(" ", strip=True))

        # Remove obvious trailer text from titles.
        title = re.sub(r"\s*\(\d+개?\s*의\s*분석자료\)\s*$", "", title).strip()

        reg_dt = ""
        for pattern in (
            r"(20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2})",
            r"(20\d{6})",
            r"(20\d{2}\s*\d{1,2}\s*\d{1,2})",
        ):
            m = re.search(pattern, container_text)
            if m:
                reg_dt = _normalize_reg_dt(m.group(1))
                break

        writer = page_writer
        if not writer and container_text:
            m = re.search(r"작성자[:\s]+([가-힣A-Za-z0-9._-]+)", container_text)
            if m:
                writer = m.group(1).strip()

        board_order = _resolve_board_order(text=container_text, url=article_url)

        if title or article_url:
            candidates.append({
                "ARTICLE_URL": article_url,
                "TITLE": title,
                "WRITER": writer,
                "REG_DT": reg_dt,
                "BOARD_ORDER": str(board_order),
                "RAW_TEXT": container_text,
            })
            seen.add(key)

    return candidates


def _walk_json_for_candidates(data, base_url: str, page_writer: str = "") -> Iterable[Dict[str, str]]:
    if isinstance(data, dict):
        message_id = _first_non_empty(
            str(data.get("message_id", "")),
            str(data.get("messageId", "")),
            str(data.get("MESSAGE_ID", "")),
        )
        title = _first_non_empty(
            str(data.get("TITLE", "")),
            str(data.get("title", "")),
            str(data.get("BOARD_TITLE", "")),
            str(data.get("subject", "")),
            str(data.get("SUBJECT", "")),
            str(data.get("docTitle", "")),
            str(data.get("docTitleSub", "")),
        )
        writer = _first_non_empty(
            str(data.get("WRITER", "")),
            str(data.get("writer", "")),
            str(data.get("REGISTER_NICKNAME", "")),
            str(data.get("analystNm", "")),
            page_writer,
        )
        reg_dt = _first_non_empty(
            str(data.get("REG_DT", "")),
            str(data.get("regDt", "")),
            str(data.get("regDate", "")),
            str(data.get("date", "")),
            str(data.get("작성일", "")),
        )
        board_code = _first_non_empty(
            str(data.get("BOARD_NAME", "")),
            str(data.get("boardName", "")),
            str(data.get("BOARD_CD", "")),
            str(data.get("boardCode", "")),
            str(data.get("category", "")),
            str(data.get("tabName", "")),
        )

        article_url = ""
        if message_id:
            article_url = f"{base_url.split('?')[0]}?tabIdx=1&subTabIdx=&message_id={message_id}"
        elif data.get("url"):
            article_url = _abs_url(base_url, str(data.get("url")))

        attachment_url = _first_non_empty(
            str(data.get("PDF_URL", "")),
            str(data.get("pdfUrl", "")),
            str(data.get("downloadUrl", "")),
            str(data.get("DOWNLOAD_URL", "")),
            str(data.get("fileUrl", "")),
            str(data.get("ATTACH_URL", "")),
        )

        if article_url and (title or writer or reg_dt or attachment_url):
            yield {
                "ARTICLE_URL": article_url,
                "TITLE": title,
                "WRITER": writer,
                "REG_DT": _normalize_reg_dt(reg_dt),
                "BOARD_ORDER": str(_resolve_board_order(board_code=board_code, text=title, url=article_url)),
                "ATTACH_URL": attachment_url,
                "RAW_TEXT": "",
            }

        for value in data.values():
            yield from _walk_json_for_candidates(value, base_url, page_writer=page_writer)

    elif isinstance(data, list):
        for item in data:
            yield from _walk_json_for_candidates(item, base_url, page_writer=page_writer)


def _extract_candidates_from_embedded_json(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    page_writer = _extract_header_writer(soup)

    script_texts = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text(" ", strip=True)
        if text:
            script_texts.append(text)

    blob_patterns = [
        r"__NEXT_DATA__\s*=\s*(\{.*?\})\s*;</script>",
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;",
        r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;",
    ]

    extracted_objects = []
    for text in script_texts:
        for pattern in blob_patterns:
            for match in re.finditer(pattern, text, flags=re.S):
                raw_json = match.group(1)
                try:
                    extracted_objects.append(json.loads(raw_json))
                except Exception:
                    continue

    seen = set()
    for obj in extracted_objects:
        for item in _walk_json_for_candidates(obj, base_url, page_writer=page_writer):
            key = item.get("ARTICLE_URL") or item.get("ATTACH_URL")
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(item)

    return candidates


async def _resolve_pdf_url(session: aiohttp.ClientSession, article_url: str) -> str:
    if not article_url:
        return ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": MOBILE_LIST_URL,
        }
        async with session.get(article_url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as response:
            if response.status != 200:
                return ""
            html = await response.text(errors="ignore")
    except Exception as e:
        logger.debug(f"ShinHan mobile detail fetch failed: {article_url} ({e})")
        return ""

    soup = BeautifulSoup(html, "html.parser")
    candidates = []

    for anchor in soup.select('a[href]'):
        href = anchor.get("href", "")
        abs_href = _abs_url(article_url, href)
        if _looks_like_pdf(abs_href):
            candidates.append(abs_href)

    # Search the raw HTML as a fallback for embedded PDF or attachment URLs.
    if not candidates:
        for pattern in (
            r'https?://[^"\']+\.pdf[^"\']*',
            r'https?://[^"\']+file\.pdf\.do[^"\']*',
            r'attachmentId=[0-9A-Za-z_-]+',
        ):
            m = re.search(pattern, html, flags=re.I)
            if m:
                candidate = m.group(0)
                if candidate.startswith("attachmentId="):
                    candidate = f"https://bbs2.shinhansec.com/board/message/file.pdf.do?{candidate}"
                candidates.append(candidate)
                break

    return candidates[0] if candidates else ""


def _normalize_article_url(article_url: str) -> str:
    if not article_url:
        return ""
    return (
        article_url
        .replace("http://bbs2.shinhaninvest.com", "https://bbs2.shinhansec.com")
        .replace("http://bbs2.shinhansec.com", "https://bbs2.shinhansec.com")
    )


def _normalize_attachment_url(attachment_url: str) -> str:
    if not attachment_url:
        return ""
    url = attachment_url.replace("shinhaninvest.com", "shinhansec.com")
    url = url.replace("/board/message/file.do?", "/board/message/file.pdf.do?")
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


async def _fetch_mobile_api(session: aiohttp.ClientSession, url: str) -> Dict[str, object]:
    payload = {
        "url": "/mweb/api/invt/shrh/ishrhShrhList",
        "callbackFun": "noop",
        "bbs_name": "giperiodicaldaily|gistockchart|plananalysis|gicompanyanalyst|giindustry|gieconomy|fxmarket|commodity|gibond|foreignbond",
        "curPage": 1,
        "lastPageFlag": "true",
        "tran": False,
        "repeatKeyP": "",
        "repeatKeyN": "",
        "sendtype": "POST",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Referer": MOBILE_LIST_URL,
        "Origin": "https://m.shinhansec.com",
        "X-Requested-With": "XMLHttpRequest",
    }

    async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as response:
        response.raise_for_status()
        return await response.json(content_type=None)


def _build_record(
    firm_info: FirmInfo,
    article: Dict[str, str],
    pdf_url: str = "",
) -> Dict[str, str]:
    article_url = _first_non_empty(article.get("ARTICLE_URL"))
    download_url = _first_non_empty(pdf_url, article.get("ATTACH_URL"), article_url)
    telegram_url = download_url or article_url
    reg_dt = _normalize_reg_dt(article.get("REG_DT", ""))
    board_order = int(article.get("BOARD_ORDER") or 99)

    # Match the legacy module: prefer the downloadable PDF URL as the stable key.
    key = _first_non_empty(pdf_url, download_url, article_url)

    return {
        "SEC_FIRM_ORDER": 1,
        "ARTICLE_BOARD_ORDER": board_order,
        "FIRM_NM": firm_info.get_firm_name(),
        "REG_DT": reg_dt,
        "ARTICLE_URL": article_url,
        "ATTACH_URL": download_url or article_url,
        "DOWNLOAD_URL": download_url or article_url,
        "TELEGRAM_URL": telegram_url or article_url,
        "PDF_URL": pdf_url or download_url or article_url,
        "ARTICLE_TITLE": _normalize_text(article.get("TITLE", "")),
        "WRITER": _normalize_text(article.get("WRITER", "")),
        "KEY": key,
        "SAVE_TIME": datetime.now().isoformat(),
    }


async def _fetch_mobile_page(session: aiohttp.ClientSession, url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://m.shinhansec.com/",
    }

    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as response:
        response.raise_for_status()
        return await response.text(errors="ignore")


async def ShinHanInvest_checkNewArticle():
    """
    Mobile Shinhan Securities scraper.

    Uses the mobile API directly. HTML parsing is kept only as a fallback when
    the API shape changes or temporarily fails.
    """

    json_data_list: List[Dict[str, str]] = []
    target_urls = config.get_urls("ShinHanInvest_1") or [MOBILE_API_URL]

    async with aiohttp.ClientSession() as session:
        for raw_url in target_urls:
            url = raw_url or MOBILE_API_URL
            firm_info = FirmInfo(sec_firm_order=1, article_board_order=0)

            logger.debug(f"ShinHanInvest mobile scraper start: {url}")
            try:
                result = await _fetch_mobile_api(session, url)
            except Exception as e:
                logger.warning(f"ShinHan mobile API fetch failed: {e}")
                try:
                    html = await _fetch_mobile_page(session, MOBILE_LIST_URL)
                    soup = BeautifulSoup(html, "html.parser")
                    candidates = _collect_article_candidates_from_html(soup, MOBILE_LIST_URL)
                    if not candidates:
                        candidates = _extract_candidates_from_embedded_json(soup, MOBILE_LIST_URL)
                    if not candidates:
                        continue
                    logger.info(f"ShinHan mobile fallback HTML found {len(candidates)} article candidates")
                    detail_tasks = []
                    for item in candidates:
                        article_url = item.get("ARTICLE_URL", "")
                        if article_url and not _looks_like_pdf(item.get("ATTACH_URL", "")):
                            detail_tasks.append(_resolve_pdf_url(session, article_url))
                        else:
                            detail_tasks.append(asyncio.sleep(0, result=""))
                    pdf_urls = await asyncio.gather(*detail_tasks, return_exceptions=True)
                    for item, pdf_url in zip(candidates, pdf_urls):
                        if isinstance(pdf_url, Exception):
                            pdf_url = ""
                        record = _build_record(firm_info, item, pdf_url=str(pdf_url or ""))
                        json_data_list.append(record)
                except Exception as fallback_error:
                    logger.error(f"ShinHan mobile fallback HTML failed: {fallback_error}")
                continue

            collection_list = result.get("body", {}).get("list01", {}).get("outputList", []) if isinstance(result, dict) else []
            if not collection_list:
                logger.warning("ShinHan mobile API returned no items.")
                continue

            logger.info(f"ShinHan mobile API found {len(collection_list)} articles")
            for item in collection_list:
                article_url = _normalize_article_url(item.get("message_url", ""))
                attachment_url = _normalize_attachment_url(item.get("attachment_url", ""))
                board_code = item.get("bbs_name", "")
                reg_dt = _normalize_reg_dt(item.get("date", ""))

                article = {
                    "ARTICLE_URL": article_url,
                    "TITLE": item.get("title", ""),
                    "WRITER": item.get("nickname", ""),
                    "REG_DT": reg_dt,
                    "BOARD_ORDER": str(_resolve_board_order(board_code=board_code, text=item.get("category", ""), url=article_url)),
                    "ATTACH_URL": attachment_url,
                }
                pdf_url = attachment_url
                record = _build_record(firm_info, article, pdf_url=pdf_url)
                if not record["PDF_URL"] and article_url:
                    record["PDF_URL"] = article_url
                json_data_list.append(record)

    # Deduplicate on KEY while keeping the first/latest occurrence.
    deduped: Dict[str, Dict[str, str]] = {}
    for row in json_data_list:
        deduped.setdefault(row.get("KEY") or row.get("ATTACH_URL") or row.get("TELEGRAM_URL"), row)

    result = list(deduped.values())
    gc.collect()
    return result


def get_shinhan_board_info():
    """
    Best-effort helper that prints board-like metadata from the mobile page.
    """
    async def _runner():
        async with aiohttp.ClientSession() as session:
            html = await _fetch_mobile_page(session, MOBILE_LIST_URL)
            soup = BeautifulSoup(html, "html.parser")
            candidates = _collect_article_candidates_from_html(soup, MOBILE_LIST_URL)
            if not candidates:
                candidates = _extract_candidates_from_embedded_json(soup, MOBILE_LIST_URL)
            board_info = sorted({
                (str(item.get("BOARD_ORDER", "")), _normalize_text(item.get("WRITER", "")))
                for item in candidates
                if item.get("BOARD_ORDER") or item.get("WRITER")
            })
            for board_order, writer in board_info:
                logger.info(f"BOARD_ORDER: {board_order}, WRITER: {writer}")

    return asyncio.run(_runner())


if __name__ == "__main__":
    results = asyncio.run(ShinHanInvest_checkNewArticle())
    logger.info(f"Fetched {len(results)} articles from ShinHan mobile")
    preview_limit = int(os.getenv("SHINHAN_PREVIEW_LIMIT", "20"))
    print(json.dumps(results[:preview_limit], ensure_ascii=False, indent=2))
