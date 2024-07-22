from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ChromeOptions 설정
chrome_options = Options()
# chrome_options.add_argument("--headless")  # 화면에 브라우저가 나타나지 않게 설정
chrome_options.add_argument("--no-sandbox")  # 샌드박스 모드 비활성화

# Chrome 드라이버 초기화
driver = webdriver.Chrome(options=chrome_options)

try:
    # 로그인 페이지 열기
    driver.get('https://www.liivm.com/system/login/login')

    time.sleep(4)

    # 아이디와 비밀번호 입력
    username = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'loginUserId'))  # 아이디 입력 필드의 ID 속성
    )
    password = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'loginUserIdPw'))  # 비밀번호 입력 필드의 ID 속성
    )

    # 실제 사용자명과 비밀번호로 변경
    username.send_keys('liante0904')
    password.send_keys('2*@z1z@1G*zD')

    # 로그인 버튼 클릭
    login_submit_button = driver.find_element(By.XPATH, '//*[@id="btnIdLogin"]')  # 실제 로그인 버튼의 XPATH로 변경
    login_submit_button.click()

    time.sleep(3)

    driver.get('https://www.liivm.com/mypage/bill/bill/billPayment')

    # 첫 번째 버튼 로딩을 기다린 다음 클릭
    btn_payment_self_layer = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="btn_paymentSelfLayer"]'))
    )
    btn_payment_self_layer.click()

    # 두 번째 버튼 로딩을 기다린 다음 클릭
    pym01_layer_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="pym01Layer"]/div/div[2]/button[2]'))
    )
    pym01_layer_btn.click()

    # 세 번째 버튼 로딩을 기다린 다음 클릭
    pym01_1_layer_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="pym01_1Layer"]/div/div[2]/button[2]'))
    )
    pym01_1_layer_btn.click()


    # 작업 완료 후 대기 (필요한 경우)
    time.sleep(3)

    # 금액 입력
    bill_amount = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="selfBillAmt"]'))
    )
    bill_amount.send_keys('5999')

    # 카드 변경 버튼 클릭
    card_change_btn = driver.find_element(By.XPATH, '//*[@id="cardChangeBtn"]')
    card_change_btn.click()

    # 카드번호 입력
    card_no_1 = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="cardNo_1"]'))
    )
    card_no_2 = driver.find_element(By.XPATH, '//*[@id="cardNo_2"]')
    card_no_3 = driver.find_element(By.XPATH, '//*[@id="cardNo_3"]')
    card_no_4 = driver.find_element(By.XPATH, '//*[@id="cardNo_4"]')

    card_no_1.send_keys('1234')
    card_no_2.send_keys('5678')
    card_no_3.send_keys('1234')
    card_no_4.send_keys('5678')

    # 유효기간 입력
    card_expiry = driver.find_element(By.XPATH, '//*[@id="cardEffcprd"]')
    card_expiry.send_keys('1212')

    # 이름 입력
    customer_name = driver.find_element(By.XPATH, '//*[@id="payCustNm"]')
    customer_name.send_keys('신승훈')

    # 생년월일 및 성별 입력
    birth_gender = driver.find_element(By.XPATH, '//*[@id="birthGender"]')
    birth_gender.send_keys('19900904')

    # 마지막 버튼 클릭
    final_button = driver.find_element(By.XPATH, '//*[@id="layerCardReg"]/div/div[2]/div/div[3]/ul/li[2]/button')
    final_button.click()

    # 작업 완료 후 대기 (필요한 경우)
    time.sleep(100)

finally:
    # 브라우저 닫기
    driver.quit()
