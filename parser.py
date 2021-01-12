import requests
from bs4 import BeautifulSoup


# 게시글 url의 경우 
# 1. 앞에 "https://www.ebestsec.co.kr/EtwFrontBoard/" 를 추가
# 2. amp; 를 삭제처리를 해야함

# 게시글 내 첨부파일의 경우 
# 1. 앞에 "https://www.ebestsec.co.kr/_bt_lib/util/download.jsp?dataType=" 를 추가
# 2. 링크에서 알맹이를 붙이면 됨 -> javascript:download("08573D2F59307A57F4FC67A81B8C333A4C884E6D2951A32F4A48B73EF4E6EC22A0E62B351A025A54E20CB47DEF8A0A801BF2F7B5E3E640975E88D7BACE3B4A49F83020ED90019B489B3C036CF8AB930DCF4795CE87DE76454465F0CF7316F47BF3A0BC08364132247378E3AABC8D0981627BD8F94134BF00D27B03D8F04AC8C04369354956052B75415A9585589694B5F63378DFA40C6BA6435302B96D780C3B3EB2BF0C866966D4CE651747574C8B25208B848CBEBB1BE0222821FC75DCE016")


target_url = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=36&left_menu_no=211&front_menu_no=212&parent_menu_no=211'

webpage = requests.get(target_url, verify=False)

soup = BeautifulSoup(webpage.content, "html.parser")
soup = soup.tbody
soup = soup.select('td.subject')
#soup = str(soup).replace("amp;", "")
print(soup)