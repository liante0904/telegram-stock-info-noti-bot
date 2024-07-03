from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

options = webdriver.ChromeOptions()
# options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# options.add_argument("window-size=1920x1080")
options.add_argument("window-size=500x500")
options.add_argument(
    "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
)
options.add_argument("lang=ko_KR")

driver = webdriver.Chrome(
   options=options
)
# URL로 이동
url = 'https://money2.creontrade.com/E5/m_net/ResearchCenter/Work/mre_DM_Mobile_Research.aspx?&category=#22_54868'
driver.get(url)


# 페이지가 로드될 때까지 대기
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'title1')))

# 페이지 소스 가져오기
page_source = driver.page_source

# BeautifulSoup을 사용하여 페이지 파싱
soup = BeautifulSoup(page_source, 'html.parser')

# li > a 태그를 한 번에 선택하여 href 속성값 가져오기
links = soup.select('#ContentPlaceHolder1_UpdatePanel1 > li > a')

base_url = "https://money2.creontrade.com/E5/m_net/ResearchCenter/Work/"
# a 태그의 href 속성값과 그 내부의 p 태그 텍스트를 리스트에 저장
hrefs = [base_url+link.get('href') for link in links]
p_texts = [link.find('p').text.strip() if link.find('p') else '' for link in links]

# href와 p 태그 텍스트를 zip으로 묶어서 출력
for link, p_text in zip(links, p_texts):
    print(f"Link: {base_url+link.get('href')}, Text: {p_text}{link.get('href')}")
    break
 
# 원하는 데이터 추출 (예: 제목들)
titles = soup.find_all('strong', class_='title1')
# 원하는 데이터 추출
items_p = soup.find_all('p')
# 원하는 데이터 추출
items = soup.find_all('a')


print('p_len', len(items_p))

print('items_len', len(items))

print('titles_len', len(titles))
# # 데이터 출력
# for title in titles:
#     print(title.text.strip())

# 데이터 출력
# for a in items:
#     print(a.get_text(),a.get('href'))


# zip 함수를 사용하여 병렬 처리
for title, a in zip(titles, items):
    break
    articleUrl = f"https://money2.creontrade.com/E5/m_net/ResearchCenter/Work/{a.get('href')}"
    print(f"{title.text}: https://money2.creontrade.com/E5/m_net/ResearchCenter/Work/{a.get('href')}")
    # URL로 이동
    driver.get(articleUrl)

    # 페이지가 로드될 때까지 대기
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'btnPdfLoad')))
    # 페이지 소스 가져오기
    page_source = driver.page_source

    # BeautifulSoup을 사용하여 페이지 파싱
    soup = BeautifulSoup(page_source, 'html.parser')

    # 원하는 데이터 추출 (예: 제목들)
    pdf = soup.select('#btnPdfLoad')
    print(pdf[0].attrs['href'])
    break



# 드라이버 종료
driver.quit()