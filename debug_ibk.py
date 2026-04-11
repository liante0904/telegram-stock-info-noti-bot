import asyncio
import aiohttp
import json
import sys
import os

# 모듈 경로 추가
sys.path.append(os.getcwd())

async def debug_ibk():
    url = "https://m.ibks.com/iko/IKO010101/getInvReportList.do"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://m.ibks.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://m.ibks.com/iko/IKO010101.do"
    }
    payload = {
        "screen": "IKO010101",
        "data": {
            "start_row": 1,
            "end_row": 50,
            "row_size": 50,
            "pageNo": 1,
            "search_value": ""
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()
            report_list = data.get("data", {}).get("list", [])
            print(f"Total reports found: {len(report_list)}")
            for r in report_list[:20]:
                print(f"TITLE: {r.get('TITLE')}")
                print(f"GUBUN: {r.get('GUBUN')}")
                print(f"ATTATCH1: {r.get('ATTATCH1')}")
                print(f"REG_DATE: {r.get('REG_DATE')}")
                print("-" * 20)

if __name__ == "__main__":
    asyncio.run(debug_ibk())
