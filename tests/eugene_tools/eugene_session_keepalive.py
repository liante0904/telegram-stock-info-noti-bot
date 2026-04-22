import argparse
import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from modules.eugene_auth import get_eugene_credentials


LOGIN_URL = "https://www.eugenefn.com/login/loginPage.do"


async def login_and_save_state(
    userid: str,
    password: str,
    cert_password: str = "",
    hts_userid: str = "",
    hts_user_password: str = "",
    hts_cert_password: str = "",
    state_file: Path = Path(".cache/eugene_storage_state.json"),
    headful: bool = True,
):
    state_file.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headful)
        context = await browser.new_context(storage_state=state_file if state_file.exists() else None)
        page = await context.new_page()

        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        await page.goto(LOGIN_URL, wait_until="networkidle")

        if "loginPage" in page.url:
            await page.fill("#userid", userid)
            await page.fill("#userPassword", password)

            if await page.locator("#htsUserid").count() > 0:
                await page.fill("#htsUserid", hts_userid)
            if await page.locator("#htsUserPassword").count() > 0:
                await page.fill("#htsUserPassword", hts_user_password)
            if await page.locator("#htsCertPassword").count() > 0:
                await page.fill("#htsCertPassword", hts_cert_password)

            if cert_password:
                if await page.locator("#certPassword").count() > 0:
                    await page.fill("#certPassword", cert_password)

            await page.get_by_text("로그인", exact=True).click()
            await page.wait_for_load_state("networkidle")

        await context.storage_state(path=str(state_file))
        print(f"saved_state={state_file}")
        print(f"current_url={page.url}")
        print(f"has_logout={await page.locator('text=로그아웃').count() > 0}")

        await browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-file", default=os.getenv("EUGENE_STATE_FILE", ".cache/eugene_storage_state.json"))
    parser.add_argument("--headful", action="store_true", help="Open a visible browser window.")
    args = parser.parse_args()

    userid, password, cert_password = get_eugene_credentials()
    hts_userid = os.getenv("EUGENE_HTS_USERID", "")
    hts_user_password = os.getenv("EUGENE_HTS_USER_PASSWORD", "")
    hts_cert_password = os.getenv("EUGENE_HTS_CERT_PASSWORD", "")

    if not userid or not password:
        raise SystemExit("Set EUGENE_USERID and EUGENE_PASSWORD in your environment or secrets.json.")

    asyncio.run(
        login_and_save_state(
            userid=userid,
            password=password,
            cert_password=cert_password,
            hts_userid=hts_userid,
            hts_user_password=hts_user_password,
            hts_cert_password=hts_cert_password,
            state_file=Path(args.state_file),
            headful=args.headful,
        )
    )


if __name__ == "__main__":
    main()
