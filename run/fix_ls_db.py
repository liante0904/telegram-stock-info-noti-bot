"""
LS증권 upload/ fallback URL → CDN(msg.ls-sec.co.kr) 정적 URL 복구 스크립트.

전략 (3단계):
  0순위: upload URL 파일명 직접 파싱 → CDN URL (emp_id_seq_date → K_date_emp_id_seq)
  1순위: LS_detail() 호출 — detail 페이지 재방문 → 첨부파일 파싱 → CDN URL
  2순위: DB 기존 msg URL 기반 writer→emp_id 매핑 → 선형 보간 seq 추정 → HEAD probing

실행:
  uv run python run/fix_ls_db.py
"""
import asyncio
import os
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime, timedelta

urllib3.disable_warnings()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["LS_SEARCH_DAYS"] = "5"

from models.db_factory import get_db
from modules.LS_0 import LS_detail, upload_filename_to_cdn_url

# ── HTTP 설정 ─────────────────────────────────────────────────────────────

SOCKS_PROXY    = os.getenv("SOCKS_PROXY_URL", "socks5h://localhost:9091")
PROXIES        = {'http': SOCKS_PROXY, 'https': SOCKS_PROXY}
MSG_HEADERS    = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://msg.ls-sec.co.kr/",
}
LS_HEADERS     = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.ls-sec.co.kr/",
}
MSG_BASE       = "https://msg.ls-sec.co.kr/eum/K_{date}_{emp_id}_{seq}.pdf"
HEAD_TIMEOUT   = 5
DETAIL_TIMEOUT = 15
PROBE_WORKERS  = 10


# ── HTTP 헬퍼 ─────────────────────────────────────────────────────────────

def head_ok(url: str) -> bool:
    """HEAD 200이면 True"""
    try:
        r = requests.head(url, headers=MSG_HEADERS, proxies=PROXIES,
                          verify=False, timeout=HEAD_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def parallel_head(urls: list[str]) -> list[str]:
    """HEAD 200인 URL만 반환"""
    with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as pool:
        futs = {pool.submit(head_ok, u): u for u in urls}
        return [futs[f] for f in as_completed(futs) if f.result()]


def fetch_writer_from_detail(key_url: str) -> str | None:
    """detail 페이지에서 '필명' 파싱."""
    try:
        r = requests.get(key_url, headers=LS_HEADERS, proxies=PROXIES,
                         verify=False, timeout=DETAIL_TIMEOUT)
        soup = BeautifulSoup(r.content, "html.parser")
        for tr in soup.select("tr"):
            th = tr.select_one("th")
            td = tr.select_one("td")
            if th and td and th.get_text(strip=True) == "필명":
                writer = td.get_text(strip=True)
                return writer if writer else None
    except Exception:
        pass
    return None


# ── 보조 함수 (emp_id probing) ───────────────────────────────────────────

def date_diff_days(dt1: str, dt2: str) -> int:
    try:
        return abs((datetime.strptime(dt1, "%Y%m%d") -
                    datetime.strptime(dt2, "%Y%m%d")).days)
    except Exception:
        return 999


def estimate_seq(reg_dt: str, history: list) -> tuple[int, int]:
    """
    history = [(reg_dt, emp_id, seq), ...] 에서 target reg_dt의 예상 seq와 spread 반환.
    """
    sorted_h = sorted(history, key=lambda x: x[0])
    before = [(dt, sq) for dt, _, sq in sorted_h if dt <= reg_dt]
    after  = [(dt, sq) for dt, _, sq in sorted_h if dt >  reg_dt]

    if before and after:
        dt1, sq1 = before[-1]
        dt2, sq2 = after[0]
        d1 = date_diff_days(reg_dt, dt1)
        d2 = date_diff_days(reg_dt, dt2)
        total = max(d1 + d2, 1)
        est = int(sq1 + (sq2 - sq1) * d1 / total)
        daily = abs(sq2 - sq1) / total
        spread = max(8, int(daily * max(d1, d2) * 0.2) + 10)
    elif before:
        dt1, sq1 = before[-1]
        d = date_diff_days(reg_dt, dt1)
        if len(before) >= 2:
            dt0, sq0 = before[-2]
            daily = abs(sq1 - sq0) / max(date_diff_days(dt1, dt0), 1)
        else:
            daily = 3
        est    = int(sq1 + daily * d)
        spread = max(8, int(daily * d * 0.2) + 10)
    elif after:
        dt2, sq2 = after[0]
        d = date_diff_days(reg_dt, dt2)
        if len(after) >= 2:
            dt3, sq3 = after[1]
            daily = abs(sq3 - sq2) / max(date_diff_days(dt3, dt2), 1)
        else:
            daily = 3
        est    = max(1, int(sq2 - daily * d))
        spread = max(8, int(daily * d * 0.2) + 10)
    else:
        est, spread = history[0][2], 15

    return est, spread


def build_probe_urls(reg_dt: str, emp_id: str, history: list) -> list[str]:
    """예상 seq 기준 probe URL 목록 생성."""
    est_seq, spread = estimate_seq(reg_dt, history)
    seqs = sorted(range(max(1, est_seq - spread), est_seq + spread + 1),
                  key=lambda x: abs(x - est_seq))
    urls = []
    for delta in (0, -1, 1):
        try:
            d = (datetime.strptime(reg_dt, "%Y%m%d") +
                 timedelta(days=delta)).strftime("%Y%m%d")
        except Exception:
            continue
        urls += [MSG_BASE.format(date=d, emp_id=emp_id, seq=s) for s in seqs]
    return urls


# ── 메인 ──────────────────────────────────────────────────────────────────

async def fix_ls_urls():
    db = get_db()

    # 1. 복구 대상 조회
    records = await db.execute_query("""
        SELECT report_id, "article_title", "writer", "telegram_url", "article_url",
               "reg_dt", "key"
        FROM "tbl_sec_reports"
        WHERE "firm_nm" = 'LS증권'
          AND ("telegram_url" LIKE 'https://www.ls-sec.co.kr/upload/%'
               OR "telegram_url" IS NULL OR "telegram_url" = '')
          AND "key" IS NOT NULL AND "key" != ''
        ORDER BY "save_time" DESC
        LIMIT 500
    """)
    total = len(records)
    upload_count = sum(1 for r in records if r.get('telegram_url', '').startswith('https://www.ls-sec.co.kr/upload/'))
    empty_count = total - upload_count
    logger.info(f"복구 대상: {total}건 (upload/ fallback {upload_count}건, 빈 문자열 {empty_count}건)")

    if total == 0:
        logger.info("복구할 데이터가 없습니다.")
        return

    # 2. writer→사번 매핑 구축 (DB 기존 msg URL 기준)
    emp_rows = await db.execute_query("""
        SELECT writer,
               regexp_replace(telegram_url, '.*K_\\d{8}_([^_]+)_(\\d+)\\.pdf.*', '\\1') AS emp_id,
               regexp_replace(telegram_url, '.*K_\\d{8}_([^_]+)_(\\d+)\\.pdf.*', '\\2')::int AS seq,
               reg_dt
        FROM tbl_sec_reports
        WHERE firm_nm = 'LS증권'
          AND telegram_url ~ 'K_\\d{8}_[^_]+_\\d+\\.pdf'
          AND writer IS NOT NULL AND writer <> ''
        ORDER BY writer, reg_dt
    """)
    raw_history: dict[str, list] = defaultdict(list)
    for r in emp_rows:
        raw_history[r["writer"]].append((r["reg_dt"], r["emp_id"], r["seq"]))
    logger.info(f"writer→사번 매핑: {len(raw_history)}명")

    # 3. 건별 처리
    updated = no_emp = probe_fail = 0
    detail_cache: dict[str, str | None] = {}

    for idx, art in enumerate(records, 1):
        writer  = art.get("writer") or ""
        reg_dt  = art["reg_dt"]
        rid     = art["report_id"]
        old_url = art["telegram_url"] or art["article_url"] or ""
        key_url = art.get("key") or ""

        logger.info(f"[{idx}/{total}] 처리 중: {art['article_title'][:50]}")

        # ── 0순위: upload URL 파일명 직접 파싱 (가장 빠름) ──
        if old_url and "upload" in old_url:
            direct_url = upload_filename_to_cdn_url(old_url)
            if direct_url and head_ok(direct_url):
                ok = await db.update_telegram_url(
                    record_id=rid,
                    telegram_url=direct_url,
                    article_title=art["article_title"],
                    pdf_url=direct_url,
                )
                if ok:
                    updated += 1
                    logger.success(f"  ✓ [0순위-직접파싱] {direct_url}")
                else:
                    logger.error(f"  DB 실패: report_id={rid}")
                continue

        # ── 1순위: detail 페이지 재방문 (LS_detail) ──
        try:
            result = await LS_detail([art])
            if result and result[0].get('telegram_url', '').startswith('https://msg.ls-sec.co.kr/'):
                new_url = result[0]['telegram_url']
                ok = await db.update_telegram_url(
                    record_id=rid,
                    telegram_url=new_url,
                    article_title=art["article_title"],
                    pdf_url=new_url,
                )
                if ok:
                    updated += 1
                    logger.success(f"  ✓ [1순위-LS_detail] {new_url}")
                    continue
                else:
                    logger.error(f"  DB 실패: report_id={rid}")
                    continue
        except Exception as e:
            logger.debug(f"  LS_detail 실패: {e}")

        # ── 2순위: DB emp_id probing ──
        history = raw_history.get(writer, [])

        if not history and key_url:
            if key_url not in detail_cache:
                fetched = fetch_writer_from_detail(key_url)
                detail_cache[key_url] = fetched
                if fetched:
                    logger.debug(f"  detail 파싱 writer: {fetched}")
                time.sleep(0.5)
            fetched_writer = detail_cache.get(key_url)
            if fetched_writer:
                history = raw_history.get(fetched_writer, [])

        if not history:
            logger.debug(f"  SKIP-no-emp: {writer or '(없음)'}")
            no_emp += 1
            continue

        emp_id = history[0][1]
        probe_urls = build_probe_urls(reg_dt, emp_id, history)
        logger.info(f"  [2순위-probe] {writer}({emp_id}) HEAD {len(probe_urls)}개")
        hit_urls = parallel_head(probe_urls)

        if not hit_urls:
            logger.warning(f"  [FAIL-2순위] 200 없음")
            probe_fail += 1
            continue

        # seq 추정치에 가장 가까운 hit 선택 (PNG→PDF 해시 비교 불필요)
        def seq_of(u):
            m = re.search(r'_(\d+)\.pdf$', u)
            return int(m.group(1)) if m else 0
        est_seq, _ = estimate_seq(reg_dt, history)
        hit_urls.sort(key=lambda u: abs(seq_of(u) - est_seq))
        found_url = hit_urls[0]

        ok = await db.update_telegram_url(
            record_id=rid,
            telegram_url=found_url,
            article_title=art["article_title"],
            pdf_url=found_url,
        )
        if ok:
            updated += 1
            logger.info(f"  ✓ [2순위-DB업데이트] est_seq≈{est_seq} → {found_url}")
        else:
            logger.error(f"  DB 실패: report_id={rid}")

        await asyncio.sleep(0.1)

    # 4. 결과 요약
    logger.info("=" * 60)
    logger.info(f"LS URL 복구 완료")
    logger.info(f"  전체 대상:  {total}건")
    logger.info(f"  복구 성공:  {updated}건")
    logger.info(f"  사번없음:   {no_emp}건")
    logger.info(f"  탐색실패:   {probe_fail}건")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(fix_ls_urls())
