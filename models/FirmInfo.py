# models/FirmInfo.py


class FirmInfo:
        
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
        "DS투자증권",    # 11
        "유진투자증권",  # 12
        "한국투자증권",  # 13
        "다올투자증권",   # 14
        "토스증권",        # 15
        "리딩투자증권",        # 16
        "대신증권",        # 17
        "IM증권",        # 18
        "DB금융투자",      # 19
        "메리츠증권",      # 20
        "한화투자증권",      # 21
        "한양증권",      # 22
        "BNK투자증권",      # 23
        "교보증권",      # 24
        "IBK투자증권",      # 25
        "SK증권",      # 26 => 유안타는 26에서 변경할것
        
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
        "Commodity",     # ARTICLE_BOARD_ORDER 7
        "정기자료",
        "해외리서치"],    
        
        # SEC_FIRM_ORDER 1
        ["산업분석",      # ARTICLE_BOARD_ORDER 0
        "기업분석",      # ARTICLE_BOARD_ORDER 1
        "스몰캡",        # ARTICLE_BOARD_ORDER 2
        "해외주식",     # ARTICLE_BOARD_ORDER 3
        "대체투자",      # ARTICLE_BOARD_ORDER 4
        "해외 채권",    # ARTICLE_BOARD_ORDER 5
        "채권/신용분석", # ARTICLE_BOARD_ORDER 6
        "주식전략/시황", # ARTICLE_BOARD_ORDER 7
        "경제",          # ARTICLE_BOARD_ORDER 8
        "기술적분석/파생시황", # ARTICLE_BOARD_ORDER 9
        "주식 포트폴리오", # ARTICLE_BOARD_ORDER 10
        "Daily 신한생각", # ARTICLE_BOARD_ORDER 11
        "의무리포트",    # ARTICLE_BOARD_ORDER 12
        "신한 속보"],    # ARTICLE_BOARD_ORDER 13
        
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
        ["기엽분석",          # ARTICLE_BOARD_ORDER 0
        "투자전략/경제분석"], # ARTICLE_BOARD_ORDER 1
        
        # SEC_FIRM_ORDER 12
        ["글로벌전략",      # ARTICLE_BOARD_ORDER 0
        "국내기업분석",      # ARTICLE_BOARD_ORDER 1
        "국내산업분석",      # ARTICLE_BOARD_ORDER 2
        "해외기업분석"],  # ARTICLE_BOARD_ORDER 3        
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
        ],
        
        # SEC_FIRM_ORDER 20
        ["투자전략",    # ARTICLE_BOARD_ORDER 0,
        "산업분석",         # ARTICLE_BOARD_ORDER 1,
        "기업분석",       # ARTICLE_BOARD_ORDER 2,
        "주요 지표 및 뉴스"       # ARTICLE_BOARD_ORDER 3,
        ],
        # SEC_FIRM_ORDER 21
        ["",    # ARTICLE_BOARD_ORDER 0,
        ],
        # SEC_FIRM_ORDER 22
        ["기업분석",    # ARTICLE_BOARD_ORDER 0,
        "산업 및 이슈 분석",    # ARTICLE_BOARD_ORDER 1,
        "채권/크레딧 분석",    # ARTICLE_BOARD_ORDER 2,
        ],
        # SEC_FIRM_ORDER 23
        ["기업분석",    # ARTICLE_BOARD_ORDER 0,
        "산업분석",    # ARTICLE_BOARD_ORDER 1,
        "금융시장",    # ARTICLE_BOARD_ORDER 2,
        "Quant분석",    # ARTICLE_BOARD_ORDER 3,
        ],
        # SEC_FIRM_ORDER 24
        ["기업분석",    # ARTICLE_BOARD_ORDER 0,
        "산업분석",    # ARTICLE_BOARD_ORDER 1,
        "투자전략",    # ARTICLE_BOARD_ORDER 2,
        "채권전략",    # ARTICLE_BOARD_ORDER 3,
        "기타분석",    # ARTICLE_BOARD_ORDER 4,
        ],
        # SEC_FIRM_ORDER 25
        ["전략/시황",    # ARTICLE_BOARD_ORDER 0,
        "기업분석",    # ARTICLE_BOARD_ORDER 1,
        "산업분석",    # ARTICLE_BOARD_ORDER 2,
        "경제/채권",      # ARTICLE_BOARD_ORDER 3,
        "해외리서치"     # ARTICLE_BOARD_ORDER 4
        ],
        # SEC_FIRM_ORDER 26
        ["",    # ARTICLE_BOARD_ORDER 0,
        "",    # ARTICLE_BOARD_ORDER 1,
        "",    # ARTICLE_BOARD_ORDER 2,
        "기업분석",    # ARTICLE_BOARD_ORDER 3,
        "기업분석",    # ARTICLE_BOARD_ORDER 4,
        "",    # ARTICLE_BOARD_ORDER 5,
        "산업분석",    # ARTICLE_BOARD_ORDER 6,
        "아침에 슼",    # ARTICLE_BOARD_ORDER 7,
        "산업분석",    # ARTICLE_BOARD_ORDER 8,
        ]
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
            
        # telegram_url 업데이트가 필요한 회사인지 여부
        self.telegram_update_required = self.SEC_FIRM_ORDER in {0, 19}
        
    def get_firm_name(self):
        if 0 <= self.SEC_FIRM_ORDER < len(self.firm_names):
            return self.firm_names[self.SEC_FIRM_ORDER]
        else:
            return ""
    
    def get_board_name(self):
        if 0 <= self.SEC_FIRM_ORDER < len(self.board_names) and 0 <= self.ARTICLE_BOARD_ORDER < len(self.board_names[self.SEC_FIRM_ORDER]):
            return self.board_names[self.SEC_FIRM_ORDER][self.ARTICLE_BOARD_ORDER]
        else:
            return ""
    
    def get_label_name(self):
        if 0 <= self.SEC_FIRM_ORDER < len(self.label_names) and 0 <= self.ARTICLE_BOARD_ORDER < len(self.label_names[self.SEC_FIRM_ORDER]):
            return self.label_names[self.SEC_FIRM_ORDER][self.ARTICLE_BOARD_ORDER]
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
            "FIRM_NAME": self.get_firm_name(),
            "BOARD_NAME": self.get_board_name(),
            "LABEL_NAME": self.get_label_name(),
            "TELEGRAM_UPDATE_REQUIRED": self.telegram_update_required
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