# models/FirmInfo.py

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
    "다올투자증권",   # 14
    "토스증권",        # 15
    "리딩투자증권",        # 16
    "대신증권",        # 17
    "IM증권",        # 18
    "DB금융투자"      # 19
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
    
    # SEC_FIRM_ORDER 15
    ["리서치리포트"], # ARTICLE_BOARD_ORDER 0
    
    # SEC_FIRM_ORDER 16
    ["리서치리포트"], # ARTICLE_BOARD_ORDER 0
    # SEC_FIRM_ORDER 17
    ["리서치리포트"], # ARTICLE_BOARD_ORDER 0
    # SEC_FIRM_ORDER 18
    ["기업분석(국내)",    # ARTICLE_BOARD_ORDER 0,
     "산업분석(국내)",         # ARTICLE_BOARD_ORDER 1,
     "기업분석(해외)",       # ARTICLE_BOARD_ORDER 2,
     "투자전략",      # ARTICLE_BOARD_ORDER 3,
     "경제분석",       # ARTICLE_BOARD_ORDER 4,
     "채권분석"],       # ARTICLE_BOARD_ORDER 5,
    
    # SEC_FIRM_ORDER 19
    ["기업/산업분석(국내)",    # ARTICLE_BOARD_ORDER 0,
     "자산전략(채권)",         # ARTICLE_BOARD_ORDER 1,
     "자산전략(주식)",       # ARTICLE_BOARD_ORDER 2,
    ]       # ARTICLE_BOARD_ORDER 5,
    
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

    # SEC_FIRM_ORDER 14
    [""],              # ARTICLE_BOARD_ORDER 0,

    # SEC_FIRM_ORDER 15
    [""],              # ARTICLE_BOARD_ORDER 0,
    # SEC_FIRM_ORDER 16
    [""],              # ARTICLE_BOARD_ORDER 0,
    # SEC_FIRM_ORDER 17
    [""],              # ARTICLE_BOARD_ORDER 0,
    # SEC_FIRM_ORDER 18
    ["기업분석(국내)",    # ARTICLE_BOARD_ORDER 0,
     "산업분석(국내)",         # ARTICLE_BOARD_ORDER 1,
     "기업분석(해외)",       # ARTICLE_BOARD_ORDER 2,
     "투자전략",      # ARTICLE_BOARD_ORDER 3,
     "경제분석",       # ARTICLE_BOARD_ORDER 4,
     "채권분석"],       # ARTICLE_BOARD_ORDER 5,
    # SEC_FIRM_ORDER 19
    [""],              # ARTICLE_BOARD_ORDER 0,

]

class FirmInfo:
    def __init__(self, sec_firm_order=0, article_board_order=0, firm_info=None):
        """
        FirmInfo 클래스의 생성자.
        - 기존 인스턴스(firm_info)를 받아 복사할 수 있음.
        - 아니면 새로 sec_firm_order와 article_board_order 값을 받아 생성 가능.
        """
        if firm_info:  # 복사 생성자
            self.SEC_FIRM_ORDER = firm_info.SEC_FIRM_ORDER
            self.ARTICLE_BOARD_ORDER = firm_info.ARTICLE_BOARD_ORDER
        else:  # 새로운 인스턴스를 생성
            self.SEC_FIRM_ORDER = sec_firm_order
            self.ARTICLE_BOARD_ORDER = article_board_order
            
    def get_firm_name(self):
        if 0 <= self.SEC_FIRM_ORDER < len(firm_names):
            return firm_names[self.SEC_FIRM_ORDER]
        else:
            return ""
    
    def get_board_name(self):
        if 0 <= self.SEC_FIRM_ORDER < len(board_names) and 0 <= self.ARTICLE_BOARD_ORDER < len(board_names[self.SEC_FIRM_ORDER]):
            return board_names[self.SEC_FIRM_ORDER][self.ARTICLE_BOARD_ORDER]
        else:
            return ""
    
    def get_label_name(self):
        if 0 <= self.SEC_FIRM_ORDER < len(label_names) and 0 <= self.ARTICLE_BOARD_ORDER < len(label_names[self.SEC_FIRM_ORDER]):
            return label_names[self.SEC_FIRM_ORDER][self.ARTICLE_BOARD_ORDER]
        else:
            return ""
    
    def set_sec_firm_order(self, sec_firm_order):
        self.SEC_FIRM_ORDER = sec_firm_order
    
    def set_article_board_order(self, article_board_order):
        self.ARTICLE_BOARD_ORDER = article_board_order
        
    def get_state(self):
        return {
            "SEC_FIRM_ORDER": self.SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER": self.ARTICLE_BOARD_ORDER,
            "FIRM_NAME":firm_names[self.SEC_FIRM_ORDER],
            "BOARD_NAME":board_names[self.SEC_FIRM_ORDER][self.ARTICLE_BOARD_ORDER],
            "LABEL_NAME":label_names[self.SEC_FIRM_ORDER][self.ARTICLE_BOARD_ORDER]
        }
# 테스트 코드
if __name__ == "__main__":
    firm_info = FirmInfo()
    print(firm_info.get_state())
    # # 증권사 이름 출력
    # print(firm_info.get_firm_name())  # LS증권
    
    # # 게시판 이름 출력
    # print(firm_info.get_board_name())  # 이슈브리프
    
    # # 라벨 이름 출력
    # print(firm_info.get_label_name())  # ""
    
    # # 상태값 변경 후 출력
    # firm_info.set_sec_firm_order(1)
    # firm_info.set_article_board_order(2)
    # print(firm_info.get_firm_name())  # 신한증권
    # print(firm_info.get_board_name())  # 스몰캡
    # print(firm_info.get_label_name())  # ""