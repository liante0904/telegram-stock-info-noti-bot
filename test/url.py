import urllib.parse

# URL 인코딩할 문자열
string_to_encode = "https://www.ls-sec.co.kr/upload/EtwBoardData/B202406/"

# quote 함수를 사용한 인코딩
encoded_string = urllib.parse.quote('[★LS China Weekly_240612(완)]백관열_120_Weekly_시장.pdf')
print("quote 함수 사용:",string_to_encode+ encoded_string)

# quote_plus 함수를 사용한 인코딩
encoded_string_plus = urllib.parse.quote_plus('[★LS China Weekly_240612(완)]백관열_120_Weekly_시장.pdf')
print("quote_plus 함수 사용:", string_to_encode+encoded_string_plus)

# 인코딩된 URL 디코딩
decoded_string = urllib.parse.unquote(encoded_string)
print("디코딩 (quote):", decoded_string)

decoded_string_plus = urllib.parse.unquote_plus(encoded_string_plus)
print("디코딩 (quote_plus):", decoded_string_plus)
