# -*- coding:utf-8 -*-
import gc
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.ConfigManager import config
from models.FirmInfo import FirmInfo


BASE_URL = "https://www.heungkuksec.co.kr"
SEC_FIRM_ORDER = 28


def _normalize_reg_dt(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    m = re.search(r"(20\d{2})\D+(\d{1,2})\D+(\d{1,2})", text)
    if m:
        y, mm, dd = m.groups()
        return f"{int(y):04d}{int(mm):02d}{int(dd):02d}"

    # Heungkuk list pages render dates like "Thu Apr 23 00:00:00 KST 2026".
    m = re.search(
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2})\s+\d{2}:\d{2}:\d{2}\s+\w+\s+(20\d{2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        months = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        mon, dd, y = m.groups()
        return f"{int(y):04d}{months[mon.lower()]:02d}{int(dd):02d}"

    digits = re.sub(r"[^0-9]", "", text)
    return digits[:8] if len(digits) >= 8 else ""


def _decode_response_text(resp: requests.Response) -> str:
    resp.encoding = "euc-kr"
    return resp.text


def _filename_ext(content_disposition: str) -> str:
    if not content_disposition:
        return ""
    m = re.search(r'filename="?([^";]+)"?', content_disposition, flags=re.IGNORECASE)
    if not m:
        return ""
    filename = m.group(1).lower()
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1]


class _HeungkukResolver:
    def __init__(self, session: requests.Session):
        self.session = session
        self.head_cache: Dict[int, Optional[Dict[str, str]]] = {}
        self.hash_cache: Dict[str, Optional[Dict[str, str]]] = {}

    def _head_download(self, key: int) -> Optional[Dict[str, str]]:
        if key in self.head_cache:
            return self.head_cache[key]

        url = f"{BASE_URL}/download.do?type=Board&key={key}"
        try:
            resp = self.session.head(url, allow_redirects=True, timeout=15, verify=False)
            if resp.status_code != 200:
                self.head_cache[key] = None
                return None
            cd = resp.headers.get("Content-Disposition", "")
            item = {
                "url": url,
                "content_disposition": cd,
                "content_length": resp.headers.get("Content-Length", ""),
                "ext": _filename_ext(cd),
            }
            self.head_cache[key] = item
            return item
        except Exception:
            self.head_cache[key] = None
            return None

    def _sha1_of_url(self, url: str) -> Optional[Dict[str, str]]:
        if url in self.hash_cache:
            return self.hash_cache[url]
        try:
            resp = self.session.get(url, timeout=20, verify=False)
            if resp.status_code != 200:
                self.hash_cache[url] = None
                return None
            raw = resp.content
            item = {"sha1": hashlib.sha1(raw).hexdigest(), "len": str(len(raw))}
            self.hash_cache[url] = item
            return item
        except Exception:
            self.hash_cache[url] = None
            return None

    def resolve_pdf_url(self, view_url: str, view_key: int) -> str:
        try:
            resp = self.session.get(view_url, timeout=20, verify=False)
            if resp.status_code != 200:
                return view_url
            html = _decode_response_text(resp)
        except Exception:
            return view_url

        direct = re.search(r"download\.do\?type=Board&key=(\d+)", html)
        if direct:
            return f"{BASE_URL}/download.do?type=Board&key={direct.group(1)}"

        short_link = re.search(r"https?://buly\.kr/[A-Za-z0-9]+", html)
        if short_link:
            try:
                s = self.session.head(short_link.group(0), allow_redirects=True, timeout=15, verify=False)
                if s.url and "download.do?type=Board&key=" in s.url:
                    return s.url
            except Exception:
                pass

        analyst_match = re.search(r"analyst/view\.do\?key=(\d+)", html)
        analyst_key = analyst_match.group(1) if analyst_match else ""

        soup = BeautifulSoup(html, "html.parser")
        upload_tag = soup.select_one("td.fonts_width_div img[src*='/upload/'], td.fonts_width_div img[src*='heungkuksec.co.kr/upload/']")
        upload_url = ""
        if upload_tag and upload_tag.get("src"):
            upload_url = upload_tag["src"].strip()
            if upload_url.startswith("/"):
                upload_url = urljoin(BASE_URL, upload_url)

        center = 2 * int(view_key) - 11927
        quick = [center, center + 1, center - 1, center + 2, center - 2, center + 3, center - 3]

        # Fast path for recent rows where center +/- 1 usually resolves PDF.
        best_pdf_key = None
        for candidate in quick:
            meta = self._head_download(candidate)
            if not meta or meta["ext"] != "pdf":
                continue
            if analyst_key and analyst_key in meta["content_disposition"]:
                return meta["url"]
            if best_pdf_key is None:
                best_pdf_key = candidate

        upload_digest = self._sha1_of_url(upload_url) if upload_url else None
        if upload_digest:
            image_key = None
            for candidate in range(center - 15, center + 16):
                meta = self._head_download(candidate)
                if not meta or meta["ext"] not in {"jpg", "jpeg", "png"}:
                    continue
                if meta["content_length"] and upload_digest["len"] and meta["content_length"] != upload_digest["len"]:
                    continue
                digest = self._sha1_of_url(meta["url"])
                if digest and digest["sha1"] == upload_digest["sha1"]:
                    image_key = candidate
                    break

            if image_key is not None:
                neighbors = [image_key - 1, image_key + 1, image_key - 2, image_key + 2]
                neighbors.sort(key=lambda x: abs(x - image_key))
                for candidate in neighbors:
                    meta = self._head_download(candidate)
                    if meta and meta["ext"] == "pdf":
                        return meta["url"]

        if best_pdf_key is not None:
            return f"{BASE_URL}/download.do?type=Board&key={best_pdf_key}"
        return view_url


def _fetch_list_rows(session: requests.Session, list_url: str, board_order: int) -> List[Dict[str, str]]:
    try:
        resp = session.get(list_url, timeout=20, verify=False)
        resp.raise_for_status()
        html = _decode_response_text(resp)
    except Exception as exc:
        logger.error(f"Heungkuk list fetch failed: {list_url} ({exc})")
        return []

    soup = BeautifulSoup(html, "html.parser")
    rows = []
    board_match = re.search(r"/research/([^/]+)/list\.do", list_url)
    board_path = board_match.group(1) if board_match else "company"

    for tr in soup.select("table.data_list_x tbody tr"):
        a = tr.select_one("a[onclick*=\"nav.go('view'\"]")
        if not a:
            continue

        onclick = a.get("onclick", "")
        key_match = re.search(r"key=(\d+)", onclick)
        if not key_match:
            continue

        view_key = int(key_match.group(1))
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue

        writer = re.sub(r"\s+", " ", cells[2].get_text(" ", strip=True))
        reg_dt = _normalize_reg_dt(cells[3].get_text(" ", strip=True))
        view_url = f"{BASE_URL}/research/{board_path}/view.do?key={view_key}"

        rows.append(
            {
                "ARTICLE_BOARD_ORDER": board_order,
                "ARTICLE_TITLE": title,
                "WRITER": writer,
                "REG_DT": reg_dt,
                "VIEW_KEY": str(view_key),
                "ARTICLE_URL": view_url,
            }
        )
    return rows


def Heungkuk_checkNewArticle():
    requests.packages.urllib3.disable_warnings()
    urls = config.get_urls("Heungkuk_28")
    if not urls:
        logger.error("Heungkuk_28 URLs are not configured.")
        return []

    json_data_list = []
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": f"{BASE_URL}/research/index.do",
        }
    )
    resolver = _HeungkukResolver(session)

    for board_order, list_url in enumerate(urls):
        firm_info = FirmInfo(sec_firm_order=SEC_FIRM_ORDER, article_board_order=board_order)
        rows = _fetch_list_rows(session, list_url, board_order)
        logger.info(f"Heungkuk board={board_order}: found {len(rows)} rows from {list_url}")

        for row in rows:
            pdf_url = resolver.resolve_pdf_url(row["ARTICLE_URL"], int(row["VIEW_KEY"]))
            key_url = pdf_url or row["ARTICLE_URL"]

            json_data_list.append(
                {
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": board_order,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": row["REG_DT"],
                    "ATTACH_URL": key_url,
                    "ARTICLE_TITLE": row["ARTICLE_TITLE"],
                    "ARTICLE_URL": row["ARTICLE_URL"],
                    "DOWNLOAD_URL": key_url,
                    "TELEGRAM_URL": key_url,
                    "PDF_URL": key_url,
                    "WRITER": row["WRITER"],
                    "KEY": key_url,
                    "SAVE_TIME": datetime.now().isoformat(),
                }
            )

    gc.collect()
    return json_data_list


if __name__ == "__main__":
    result = Heungkuk_checkNewArticle()
    logger.info(f"Heungkuk total rows: {len(result)}")
    for item in result[:5]:
        logger.info(item)
