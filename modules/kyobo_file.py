import requests

def getfilename(seqno):
    # 요청 URL (기본 URL에서 seqno만 다르게 변경)
    url = "https://www.iprovest.com/weblogic/RSDownloadServlet"
    full_url = f"{url}?mode=today&seqno={seqno}"

    # 요청 헤더
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }

    # 요청 쿠키
    cookies = {
        "JSESSIONID": "a00ipPEVKRszDpy9U-i1rTXl150BsAUkQwsidVBV96ofps6y4RYJ\u0021375194933",
    }

    # 요청 보내기
    response = requests.get(full_url, headers=headers, cookies=cookies)

    # Content-Disposition 헤더 확인
    content_disposition = response.headers.get("Content-Disposition")
    
    if content_disposition:
        # 파일명 추출
        filename = content_disposition.split("filename=")[-1].strip('"')
        return filename
    else:
        return None

# seqno를 파라미터로 전달
seqno = "0002052083"

# 파일명 얻기
filename = getfilename(seqno)
if filename:
    print("다운로드 파일명:", filename)
else:
    print("파일 이름 정보가 Content-Disposition 헤더에 없습니다.")
