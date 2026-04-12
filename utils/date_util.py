# -*- coding:utf-8 -*- 
import datetime
from pytz import timezone

# 전용 현재일자 (주말인 경우 월요일)
def GetCurrentDate_NH():
    # 한국 표준시(KST) 시간대를 설정합니다.
    tz_kst = timezone('Asia/Seoul')
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_kst = now_utc.astimezone(tz_kst)

    # 현재 요일을 구합니다. (월요일=0, 일요일=6)
    current_weekday = now_kst.weekday()

    if current_weekday == 5:  # 오늘이 토요일인 경우
        next_monday = now_kst + datetime.timedelta(days=2)
    elif current_weekday == 6:  # 오늘이 일요일인 경우
        next_monday = now_kst + datetime.timedelta(days=1)
    else:
        next_monday = now_kst  # 오늘이 월요일~금요일인 경우 현재 일자 반환

    return next_monday.strftime('%Y%m%d')

# 한국 시간 (timezone('Asia/Seoul')) 날짜 정보를 구합니다.
# 'yyyymmdd'
def GetCurrentDate(*args):

    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    DATE = time_now[:10].strip()
    DATE_SPLIT = DATE.split("-")

    pattern = ''
    # r = ['y','m','d','Y','M','D']    
    if not args:
        pattern= ''.join(DATE_SPLIT) 
    else: pattern = args[0]
    # if ['y','m','d','Y','M','D'] not in pattern :  return ''.join(DATE_SPLIT)

    pattern= pattern.replace('yyyy', DATE_SPLIT[0])
    pattern= pattern.replace('YYYY', DATE_SPLIT[0])
    pattern= pattern.replace('mm', DATE_SPLIT[1])
    pattern= pattern.replace('MM', DATE_SPLIT[1])
    pattern= pattern.replace('dd', DATE_SPLIT[2])
    pattern= pattern.replace('DD', DATE_SPLIT[2])


    # print('입력', args[0], '최종', pattern)
    return pattern