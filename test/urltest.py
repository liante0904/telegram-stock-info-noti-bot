import urllib.parse
import requests

# 주어진 URL
url = 'https://www.ls-sec.co.kr/upload/EtwBoardData/B202405/240531_대원강업_탐방노트[0].pdf'

# URL 인코딩 (경로 부분만 인코딩)
parsed_url = urllib.parse.urlsplit(url)
encoded_path = urllib.parse.quote(parsed_url.path)
encoded_url = urllib.parse.urlunsplit((parsed_url.scheme, parsed_url.netloc, encoded_path, parsed_url.query, parsed_url.fragment))

print(encoded_url)

