# package/firm_info.py

# 증권사 이름만 담긴 배열 (100 미만)
firm_names = [
    "LS증권",        # 0
    "신한증권",      # 1
    "NH투자증권",    # 2
    "하나증권",      # 3
    "KB증권",        # 4
    "삼성증권",      # 5
    "상상인증권",    # 6
    "신영증권",      # 7
    "미래에셋증권",  # 8
    "현대차증권",    # 9
    "키움증권",      # 10
    "",              # 11
    "",              # 12
    "한국투자증권",  # 13
    "다올투자증권"   # 14
]

# 게시판 이름을 담은 2차원 배열
board_names = [
    # SEC_FIRM_ORDER 0
    ["이슈브리프",    # ARTICLE_BOARD_ORDER 0
     "기업분석",      # ARTICLE_BOARD_ORDER 1
     "산업분석",      # ARTICLE_BOARD_ORDER 2
     "투자전략",      # ARTICLE_BOARD_ORDER 3
     "Quant",         # ARTICLE_BOARD_ORDER 4
     "Macro",         # ARTICLE_BOARD_ORDER 5
     "FI/ Credit",    # ARTICLE_BOARD_ORDER 6
     "Commodity"],    # ARTICLE_BOARD_ORDER 7
    
    # SEC_FIRM_ORDER 1
    ["산업분석",      # ARTICLE_BOARD_ORDER 0
     "기업분석",      # ARTICLE_BOARD_ORDER 1
     "스몰캡",        # ARTICLE_BOARD_ORDER 2
     "해외주식"],     # ARTICLE_BOARD_ORDER 3
    
    # SEC_FIRM_ORDER 2
    ["오늘의레포트"], # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 3
    ["Daily",         # ARTICLE_BOARD_ORDER 0
     "산업분석",      # ARTICLE_BOARD_ORDER 1
     "기업분석",      # ARTICLE_BOARD_ORDER 2
     "주식 전략",     # ARTICLE_BOARD_ORDER 3
     "Small Cap",     # ARTICLE_BOARD_ORDER 4
     "기업 메모",     # ARTICLE_BOARD_ORDER 5
     "Quant",         # ARTICLE_BOARD_ORDER 6
     "포트폴리오",    # ARTICLE_BOARD_ORDER 7
     "투자정보"],     # ARTICLE_BOARD_ORDER 8
    
    # SEC_FIRM_ORDER 4
    ["오늘의레포트"], # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 5
    ["기업분석",      # ARTICLE_BOARD_ORDER 0
     "산업분석",      # ARTICLE_BOARD_ORDER 1
     "해외 분석"],    # ARTICLE_BOARD_ORDER 2
    
    # SEC_FIRM_ORDER 6
    ["투자전략",      # ARTICLE_BOARD_ORDER 0
     "산업리포트",    # ARTICLE_BOARD_ORDER 1
     "기업리포트"],   # ARTICLE_BOARD_ORDER 2
    
    # SEC_FIRM_ORDER 7
    [""],             # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 8
    ["오늘의레포트"], # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 9
    ["투자전략",      # ARTICLE_BOARD_ORDER 0
     "Report&Note",   # ARTICLE_BOARD_ORDER 1
     "해외주식"],     # ARTICLE_BOARD_ORDER 2
    
    # SEC_FIRM_ORDER 10
    ["기업분석",      # ARTICLE_BOARD_ORDER 0
     "산업분석",      # ARTICLE_BOARD_ORDER 1
     "스팟노트",      # ARTICLE_BOARD_ORDER 2
     "미국/선진국"],  # ARTICLE_BOARD_ORDER 3
    
    # SEC_FIRM_ORDER 11
    [""],             # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 12
    [""],             # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 13
    ["오늘의레포트"], # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 14
    ["기업분석",      # ARTICLE_BOARD_ORDER 0
     "기업분석",      # ARTICLE_BOARD_ORDER 1
     "기업분석",      # ARTICLE_BOARD_ORDER 2
     "기업분석",      # ARTICLE_BOARD_ORDER 3
     "기업분석",      # ARTICLE_BOARD_ORDER 4
     "기업분석",      # ARTICLE_BOARD_ORDER 5
     "기업분석",      # ARTICLE_BOARD_ORDER 6
     "기업분석",      # ARTICLE_BOARD_ORDER 7
     "산업분석",      # ARTICLE_BOARD_ORDER 8
     "산업분석",      # ARTICLE_BOARD_ORDER 9
     "산업분석",      # ARTICLE_BOARD_ORDER 10
     "산업분석",      # ARTICLE_BOARD_ORDER 11
     "산업분석",      # ARTICLE_BOARD_ORDER 12
     "산업분석"],     # ARTICLE_BOARD_ORDER 13
]

# 라벨 이름을 담은 2차원 배열
label_names = [
    # SEC_FIRM_ORDER 0
    ["",               # ARTICLE_BOARD_ORDER 0
     "",               # ARTICLE_BOARD_ORDER 1
     "",               # ARTICLE_BOARD_ORDER 2
     "",               # ARTICLE_BOARD_ORDER 3
     "",               # ARTICLE_BOARD_ORDER 4
     "",               # ARTICLE_BOARD_ORDER 5
     "",               # ARTICLE_BOARD_ORDER 6
     ""],              # ARTICLE_BOARD_ORDER 7
    
    # SEC_FIRM_ORDER 1
    ["",               # ARTICLE_BOARD_ORDER 0
     "",               # ARTICLE_BOARD_ORDER 1
     "",               # ARTICLE_BOARD_ORDER 2
     ""],              # ARTICLE_BOARD_ORDER 3
    
    # SEC_FIRM_ORDER 2
    [""],              # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 3
    ["",               # ARTICLE_BOARD_ORDER 0
     "",               # ARTICLE_BOARD_ORDER 1
     "",               # ARTICLE_BOARD_ORDER 2
     "",               # ARTICLE_BOARD_ORDER 3
     "",               # ARTICLE_BOARD_ORDER 4
     "",               # ARTICLE_BOARD_ORDER 5
     "",               # ARTICLE_BOARD_ORDER 6
     "",               # ARTICLE_BOARD_ORDER 7
     ""],              # ARTICLE_BOARD_ORDER 8
    
    # SEC_FIRM_ORDER 4
    [""],              # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 5
    ["",               # ARTICLE_BOARD_ORDER 0,
     "",               # ARTICLE_BOARD_ORDER 1,
     ""],               # ARTICLE_BOARD_ORDER 2
    
    
    # SEC_FIRM_ORDER 6
    ["",               # ARTICLE_BOARD_ORDER 0,
     "",               # ARTICLE_BOARD_ORDER 1,
     ""],               # ARTICLE_BOARD_ORDER 2
    
    
    # SEC_FIRM_ORDER 7
    [""],              # ARTICLE_BOARD_ORDER 0,
    
    # SEC_FIRM_ORDER 8
    [""],              # ARTICLE_BOARD_ORDER 0,
    
    # SEC_FIRM_ORDER 9
    ["",               # ARTICLE_BOARD_ORDER 0,
     "",               # ARTICLE_BOARD_ORDER 1,
     ""],               # ARTICLE_BOARD_ORDER 2
    
    
    # SEC_FIRM_ORDER 10
    ["",               # ARTICLE_BOARD_ORDER 0,
     "",               # ARTICLE_BOARD_ORDER 1,
     "",               # ARTICLE_BOARD_ORDER 2,
     ""],               # ARTICLE_BOARD_ORDER 3,
    
    # SEC_FIRM_ORDER 11
    [""],              # ARTICLE_BOARD_ORDER 0,
    
    # SEC_FIRM_ORDER 12
    [""],              # ARTICLE_BOARD_ORDER 0,
    
    # SEC_FIRM_ORDER 13
    [""],              # ARTICLE_BOARD_ORDER 0,
    
    # SEC_FIRM_ORDER 14
    ["통신/미디어",    # ARTICLE_BOARD_ORDER 0,
     "IT",             # ARTICLE_BOARD_ORDER 1,
     "소재",           # ARTICLE_BOARD_ORDER 2,
     "산업재",         # ARTICLE_BOARD_ORDER 3,
     "금융",           # ARTICLE_BOARD_ORDER 4,
     "내수",           # ARTICLE_BOARD_ORDER 5,
     "스몰캡",         # ARTICLE_BOARD_ORDER 6,
     "해외기업",       # ARTICLE_BOARD_ORDER 7,
     "통신/미디어",    # ARTICLE_BOARD_ORDER 8,
     "IT",             # ARTICLE_BOARD_ORDER 9,
     "소재",           # ARTICLE_BOARD_ORDER 10,
     "산업재",         # ARTICLE_BOARD_ORDER 11,
     "금융",           # ARTICLE_BOARD_ORDER 12,
     "내수"],          # ARTICLE_BOARD_ORDER 13,
]

# 증권사 이름을 반환하는 함수
def get_firm_name(sec_firm_order):
    try:
        return firm_names[sec_firm_order]
    except IndexError:
        print(f"Invalid SEC_FIRM_ORDER: {sec_firm_order}")
        return "Unknown Firm"

# 게시판 이름을 반환하는 함수
def get_board_name(sec_firm_order, article_board_order):
    try:
        return board_names[sec_firm_order][article_board_order]
    except IndexError:
        print(f"Invalid SEC_FIRM_ORDER: {sec_firm_order}, ARTICLE_BOARD_ORDER: {article_board_order}")
        return "Unknown Board"

# 라벨 이름을 반환하는 함수
def get_label_name(sec_firm_order, article_board_order):
    try:
        return label_names[sec_firm_order][article_board_order]
    except IndexError:
        print(f"Invalid SEC_FIRM_ORDER: {sec_firm_order}, ARTICLE_BOARD_ORDER: {article_board_order}")
        return "Unknown Label"

# 통합 정보를 반환하는 함수
def get_firm_info(sec_firm_order, article_board_order):
    firm_name = get_firm_name(sec_firm_order)
    board_name = get_board_name(sec_firm_order, article_board_order)
    label_name = get_label_name(sec_firm_order, article_board_order)
    return {
        "firm_name": firm_name,
        "board_name": board_name,
        "label_name": label_name
    }
