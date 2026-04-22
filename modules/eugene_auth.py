import asyncio
import json
import os
from pathlib import Path
from contextlib import asynccontextmanager

import aiohttp
from yarl import URL

try:
    from models.ConfigManager import config
except Exception:
    config = None


LOGIN_PAGE = "https://www.eugenefn.com/login/loginPage.do"
LOGIN_CHECK = "https://www.eugenefn.com/login/loginPage/loginCheck.do"
LOGIN_PROCESS = "https://www.eugenefn.com/login/loginProcess.do"
COOKIE_PATH = Path(__file__).resolve().parents[1] / "json" / "eugene_cookies.json"


def get_eugene_credentials():
    userid = os.getenv("EUGENE_USERID", "")
    password = os.getenv("EUGENE_PASSWORD", "")
    cert_password = os.getenv("EUGENE_CERT_PASSWORD", "")
    if config is not None:
        userid = userid or config.get_secret("EUGENE_USERID", "")
        password = password or config.get_secret("EUGENE_PASSWORD", "")
        cert_password = cert_password or config.get_secret("EUGENE_CERT_PASSWORD", "")
    return userid, password, cert_password


def load_cookie_dict(cookie_path: Path = COOKIE_PATH) -> dict:
    if not cookie_path.exists():
        return {}

    try:
        with cookie_path.open("r", encoding="utf-8") as f:
            cookies = json.load(f)
    except Exception:
        return {}

    if isinstance(cookies, dict):
        return {str(k): str(v) for k, v in cookies.items() if v is not None}
    if isinstance(cookies, str):
        cookie_dict = {}
        for part in cookies.split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                cookie_dict[key.strip()] = value.strip()
        return cookie_dict
    return {}


def save_cookie_dict(cookie_dict: dict, cookie_path: Path = COOKIE_PATH) -> None:
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    with cookie_path.open("w", encoding="utf-8") as f:
        json.dump(cookie_dict, f, ensure_ascii=False, indent=2)


def cookie_dict_to_header(cookie_dict: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookie_dict.items() if v is not None and v != "")


def is_login_page(text: str = "", final_url: str = "") -> bool:
    lowered = (text or "").lower()
    normalized_url = (final_url or "").lower()
    if "lo10r.do" in normalized_url or "loginpage.do" in normalized_url:
        return True
    if "로그인" in (text or "") and "로그아웃" not in (text or ""):
        return True
    if "login" in lowered and "logout" not in lowered and "ii30r.do" not in lowered and "ii33r.do" not in lowered:
        return True
    return False


async def login_and_save_cookies(userid: str, password: str, cert_password: str = "", cookie_path: Path = COOKIE_PATH) -> dict:
    timeout = aiohttp.ClientTimeout(total=30)
    cookie_jar = aiohttp.CookieJar(unsafe=True)

    async with aiohttp.ClientSession(cookie_jar=cookie_jar, timeout=timeout) as session:
        await session.get(LOGIN_PAGE)

        login_check_payload = {
            "userid": userid,
            "userPassword": password,
            "autoSignPassword": "0",
            "useSign": "0" if not cert_password else "1",
            "certYn": "N" if not cert_password else "Y",
            "htsUserid": "",
            "htsUserPassword": "",
            "htsCertPassword": "",
            "hts": "",
        }

        async with session.post(LOGIN_CHECK, data=login_check_payload) as resp:
            result = await resp.json(content_type=None)

        if result.get("vFlag") == "user.one":
            raise RuntimeError(result.get("msg", "login failed"))

        if result.get("useSign") == "1":
            raise RuntimeError(
                "This account flow requires certificate login. "
                "Use the browser-based login path or provide certificate credentials."
            )

        form_payload = {
            "pUserId": result.get("signdn", ""),
            "DN": "",
            "plain_data_cert": "",
            "plain_data_cert_length": "",
            "rvalue": "",
            "returnURL": "",
            "htsUserid": "",
            "htsUserPassword": "",
            "htsCertPassword": "",
            "hts": "",
            "goMenu": "",
            "certYn": "N",
            "userConnType": "1234567890",
            "loginTime": "1800",
            "userid": userid,
            "userPassword": password,
            "certPassword": cert_password,
            "idSave": "Y",
            "useSign": "0",
            "autoSignPassword": "0",
            "certType": "A",
        }

        async with session.post(LOGIN_PROCESS, data=form_payload, allow_redirects=True) as resp:
            await resp.text()

        cookie_jar_view = session.cookie_jar.filter_cookies(URL("https://www.eugenefn.com"))
        cookie_dict = {name: morsel.value for name, morsel in cookie_jar_view.items()}
        session.cookie_jar.clear()
        session.cookie_jar.update_cookies(cookie_dict, response_url=URL("https://m.eugenefn.com"))
        save_cookie_dict(cookie_dict, cookie_path=cookie_path)
        return cookie_dict


@asynccontextmanager
async def authenticated_session(userid: str, password: str, cert_password: str = "", headers: dict | None = None):
    timeout = aiohttp.ClientTimeout(total=30)
    cookie_jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(headers=headers or {}, cookie_jar=cookie_jar, timeout=timeout) as session:
        await session.get(LOGIN_PAGE)

        login_check_payload = {
            "userid": userid,
            "userPassword": password,
            "autoSignPassword": "0",
            "useSign": "0" if not cert_password else "1",
            "certYn": "N" if not cert_password else "Y",
            "htsUserid": "",
            "htsUserPassword": "",
            "htsCertPassword": "",
            "hts": "",
        }

        async with session.post(LOGIN_CHECK, data=login_check_payload) as resp:
            result = await resp.json(content_type=None)

        if result.get("vFlag") == "user.one":
            raise RuntimeError(result.get("msg", "login failed"))

        if result.get("useSign") == "1":
            raise RuntimeError(
                "This account flow requires certificate login. "
                "Use the browser-based login path or provide certificate credentials."
            )

        form_payload = {
            "pUserId": result.get("signdn", ""),
            "DN": "",
            "plain_data_cert": "",
            "plain_data_cert_length": "",
            "rvalue": "",
            "returnURL": "",
            "htsUserid": "",
            "htsUserPassword": "",
            "htsCertPassword": "",
            "hts": "",
            "goMenu": "",
            "certYn": "N",
            "userConnType": "1234567890",
            "loginTime": "1800",
            "userid": userid,
            "userPassword": password,
            "certPassword": cert_password,
            "idSave": "Y",
            "useSign": "0",
            "autoSignPassword": "0",
            "certType": "A",
        }

        async with session.post(LOGIN_PROCESS, data=form_payload, allow_redirects=True) as resp:
            await resp.text()

        cookie_jar_view = session.cookie_jar.filter_cookies(URL("https://www.eugenefn.com"))
        cookie_dict = {name: morsel.value for name, morsel in cookie_jar_view.items()}
        session.cookie_jar.clear()
        session.cookie_jar.update_cookies(cookie_dict, response_url=URL("https://m.eugenefn.com"))
        save_cookie_dict(cookie_dict, cookie_path=COOKIE_PATH)
        yield session


async def login_from_env_and_save(cookie_path: Path = COOKIE_PATH) -> dict:
    userid, password, cert_password = get_eugene_credentials()
    if not userid or not password:
        raise RuntimeError("Set EUGENE_USERID and EUGENE_PASSWORD in your environment or secrets.json.")
    return await login_and_save_cookies(userid, password, cert_password, cookie_path=cookie_path)


def load_cookie_header(cookie_path: Path = COOKIE_PATH) -> str:
    return cookie_dict_to_header(load_cookie_dict(cookie_path))


if __name__ == "__main__":
    userid, password, cert_password = get_eugene_credentials()
    if not userid or not password:
        raise SystemExit("Set EUGENE_USERID and EUGENE_PASSWORD first.")
    result = asyncio.run(login_and_save_cookies(userid, password, cert_password))
    print(json.dumps(result, ensure_ascii=False, indent=2))
