import asyncio
import os
import sys
from datetime import date as date_cls

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from loguru import logger

from models.db_factory import get_db
from modules.eugenefn_12 import eugene_checkNewArticle


async def run_backfill(full_fetch=True, since_date=None):
    if since_date is None and full_fetch:
        since_date = date_cls.today().replace(month=1, day=1)

    logger.info(f"Eugene backfill start (full_fetch={full_fetch}, since_date={since_date})")
    articles = await eugene_checkNewArticle(full_fetch=full_fetch, since_date=since_date)
    logger.info(f"Eugene backfill scraped {len(articles)} rows")

    if not articles:
        logger.warning("Eugene backfill returned no rows; skipping DB insert")
        return articles

    db = get_db()
    if hasattr(db, "insert_json_data_list"):
        result = db.insert_json_data_list(articles)
        if asyncio.iscoroutine(result):
            result = await result
        logger.info(f"Eugene backfill DB result: {result}")
    else:
        logger.warning("DB adapter does not support insert_json_data_list")

    return articles


def main():
    articles = asyncio.run(run_backfill(full_fetch=True))
    print(f"SCRAPED={len(articles)}")


if __name__ == "__main__":
    main()
