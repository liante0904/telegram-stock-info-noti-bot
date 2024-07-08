import json

testjres = '''{
    "result": {
        "newsList": [
            {"type":1,"subcontent":"...","thumbUrl":"...","oid":"016","ohnm":"헤럴드경제","aid":"0002328998","tit":"임영웅까지...","dt":"20240701085911"},
            {"type":1,"subcontent":"...","thumbUrl":"...","oid":"014","ohnm":"파이낸셜뉴스","aid":"0005206655","tit":"어제 남자친구와...","dt":"20240701110419"},
            {"type":1,"subcontent":"...","thumbUrl":"...","oid":"011","ohnm":"서울경제","aid":"0004360233","tit":"무턱대고 병원갔다...","dt":"20240701134215"},
            {"type":1,"subcontent":"...","thumbUrl":"...","oid":"215","ohnm":"한국경제TV","aid":"0001168812","tit":"코스피, 2,800선...","dt":"20240701153110"}
        ]
    },
    "resultCode": "success"
}'''

json_b = '''[
    {"type":1,"subcontent":"...","thumbUrl":"...","oid":"014","ohnm":"파이낸셜뉴스","aid":"0005206655","tit":"어제 남자친구와...","dt":"20240701110419"},
    {"type":1,"subcontent":"...","thumbUrl":"...","oid":"011","ohnm":"서울경제","aid":"0004360233","tit":"무턱대고 병원갔다...","dt":"20240701134215"}
]'''

# JSON 데이터를 Python 딕셔너리로 변환
data_a = json.loads(testjres)
data_b = json.loads(json_b)

# 중복 데이터 제거 로직
def remove_duplicates(data_a, data_b):
    b_set = {(item['oid'], item['aid']) for item in data_b}
    
    filtered_news_list = [item for item in data_a['result']['newsList'] if (item['oid'], item['aid']) not in b_set]
    
    return filtered_news_list

# 중복 제거 후 남은 testjres의 값
filtered_news = remove_duplicates(data_a, data_b)

# 결과 출력
print(json.dumps(filtered_news, indent=4, ensure_ascii=False))
