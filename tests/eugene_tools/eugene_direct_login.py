import argparse
import asyncio
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from modules.eugene_auth import get_eugene_credentials, login_and_save_cookies


async def login_and_fetch(userid: str, password: str, target_url: str, cert_password: str = ""):
    import aiohttp

    timeout = aiohttp.ClientTimeout(total=30)
    cookie_jar = aiohttp.CookieJar(unsafe=True)

    async with aiohttp.ClientSession(cookie_jar=cookie_jar, timeout=timeout) as session:
        cookie_dict = await login_and_save_cookies(userid, password, cert_password)
        session.cookie_jar.update_cookies(cookie_dict)

        async with session.get(target_url) as resp:
            text = await resp.text()
            logged_in = ("로그아웃" in text) or ("logout" in text.lower())

        print(json.dumps({
            "logged_in": logged_in,
            "target_status": resp.status,
            "target_url": target_url,
            "response_preview": text[:300],
        }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Authenticated page to fetch after login")
    args = parser.parse_args()

    userid, password, cert_password = get_eugene_credentials()

    if not userid or not password:
        raise SystemExit("Set EUGENE_USERID and EUGENE_PASSWORD in your environment or secrets.json.")

    asyncio.run(login_and_fetch(userid, password, args.url, cert_password=cert_password))


if __name__ == "__main__":
    main()
