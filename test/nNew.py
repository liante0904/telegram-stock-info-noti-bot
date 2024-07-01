import json

# 첫 번째 JSON 데이터
json_data1 = [
    {
        "type": 1,
        "subcontent": "연돈볼카츠 점주...",
        "thumbUrl": "https://imgnews.pstatic.net/image/origin/009/2024/06/18/5320430.jpg?type=nf206_146",
        "oid": "009",
        "ohnm": "매일경제",
        "aid": "0005320430",
        "tit": "백종원 ‘4천억 대박’...",
        "dt": "20240618075507"
    },
    {
        "type": 1,
        "subcontent": "현대차가 이틀째...",
        "thumbUrl": "https://imgnews.pstatic.net/image/origin/215/2024/06/18/1166869.jpg?type=nf206_146",
        "oid": "215",
        "ohnm": "한국경제TV",
        "aid": "0001166869",
        "tit": "[속보] 현대차, 천장...",
        "dt": "20240618094527"
    }
]

# 두 번째 JSON 데이터
json_data2 = [
    {
        "type": 1,
        "subcontent": "현대차가 이틀째...",
        "thumbUrl": "https://imgnews.pstatic.net/image/origin/215/2024/06/18/1166869.jpg?type=nf206_146",
        "oid": "215",
        "ohnm": "한국경제TV",
        "aid": "0001166869",
        "tit": "[속보] 현대차, 천장...",
        "dt": "20240618094527"
    },
    {
        "type": 1,
        "subcontent": "방산주가 모처럼...",
        "thumbUrl": "https://imgnews.pstatic.net/image/origin/015/2024/06/18/4998173.jpg?type=nf206_146",
        "oid": "015",
        "ohnm": "한국경제",
        "aid": "0004998173",
        "tit": "\"1200% 먹고...",
        "dt": "20240618090114"
    }
]

# 중복되지 않는 JSON 데이터 추출
def get_unique_json(data1, data2):
    # aid를 기준으로 중복 체크
    aid_set1 = {item['aid'] for item in data1}
    aid_set2 = {item['aid'] for item in data2}
    
    # 중복되지 않는 데이터 추출
    unique_data1 = [item for item in data1 if item['aid'] not in aid_set2]
    unique_data2 = [item for item in data2 if item['aid'] not in aid_set1]
    
    # 두 리스트를 합침
    unique_data = unique_data1 + unique_data2
    
    return unique_data

unique_data = get_unique_json(json_data1, json_data2)

# 결과 출력
print(json.dumps(unique_data, indent=4, ensure_ascii=False))
