import base64
import urllib.parse as urlparse

def extract_and_decode_url(url):
    """
    주어진 URL에서 id와 Base64로 인코딩된 url 값을 추출하고, 인코딩된 url 값을 디코딩하여 반환하는 함수

    Parameters:
    url (str): URL 문자열

    Returns:
    str: 추출된 id 값과 디코딩된 url 값을 포함한 문자열
    """
    # URL 파싱
    parsed_url = urlparse.urlparse(url)
    
    # 쿼리 문자열 파싱
    query_params = urlparse.parse_qs(parsed_url.query)
    
    # id와 url 추출
    id_value = query_params.get('id', [None])[0]
    encoded_url = query_params.get('url', [None])[0]
    
    if id_value is None or encoded_url is None:
        return "Invalid URL: id or url is missing"
    
    # Base64 디코딩
    try:
        decoded_url = base64.b64decode(encoded_url).decode('utf-8')
    except Exception as e:
        return f"Error decoding url: {e}"
    
    return f"Extracted id: {id_value}, Decoded URL: {decoded_url}"

# 예제 사용
url = 'https://rcv.kbsec.com/streamdocs/pdfview?id=B520190322125512762443&url=aHR0cDovL3JkYXRhLmtic2VjLmNvbS9wZGZfZGF0YS8yMDI0MDcxMDEwMDYyMDEwM0sucGRm'
print(extract_and_decode_url(url))
