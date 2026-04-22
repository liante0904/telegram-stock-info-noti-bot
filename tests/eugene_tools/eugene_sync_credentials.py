import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


SECRETS_PATH = Path.home() / "secrets" / "ssh-reports-scraper" / "secrets.json"

ENV_KEYS = ("EUGENE_USERID", "EUGENE_PASSWORD", "EUGENE_CERT_PASSWORD")


def read_source_env() -> dict:
    values = {}
    for key in ENV_KEYS:
        value = os.getenv(key, "")
        if value:
            values[key] = value
    return values


def sync_to_secrets_file(values: dict) -> None:
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SECRETS_PATH.exists():
        try:
            data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}

    common = data.get("common", {})
    if not isinstance(common, dict):
        common = {}

    common.update(values)
    data["common"] = common
    SECRETS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Sync Eugene credentials from current shell exports into secrets.json.")
    parser.parse_args()

    values = read_source_env()
    missing = [key for key in ("EUGENE_USERID", "EUGENE_PASSWORD") if key not in values]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    sync_to_secrets_file(values)

    print(f"synced: {', '.join(values.keys())}")
    print(f"secrets_file: {SECRETS_PATH}")


if __name__ == "__main__":
    main()
