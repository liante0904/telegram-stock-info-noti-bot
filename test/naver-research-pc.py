import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_research_data(keyword='', brokerCode='', searchType='writeDate', writeFromDate='', writeToDate='', itemName='', itemCode=''):
    url = 'https://finance.naver.com/research/company_list.naver'
    params = {
        'keyword': keyword,
        'brokerCode': brokerCode,
        'searchType': searchType,
        'writeFromDate': writeFromDate,
        'writeToDate': writeToDate,
        'itemName': itemName,
        'itemCode': itemCode,
        'x': 30,
        'y': 31
    }
    
    response = requests.get(url, params=params)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Define the DataFrame to store the data
    columns = ['종목명', '제목', '브로커', '파일보기', '작성일', '번호']
    data = []

    # Parse the HTML to extract the research data
    table = soup.find('table', class_='type_1')
    
    if table:
        rows = table.find_all('tr')[2:]  # Skip header rows

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 6:  # Skip empty rows and rows with colspan
                continue
            
            item_name = cols[0].text.strip() if cols[0].find('a', class_='stock_item') else ''
            title = cols[1].text.strip() if cols[1].find('a') else ''
            broker = cols[2].text.strip()
            file_view = cols[3].find('a')['href'] if cols[3].find('a') else ''
            write_date = cols[4].text.strip()
            num = cols[5].text.strip()

            data.append([item_name, title, broker, file_view, write_date, num])
    else:
        print("Table not found on the page.")

    df = pd.DataFrame(data, columns=columns)
    
    return df

# Example usage
writeFromDate = '2024-06-10'
writeToDate = '2024-06-23'
df = get_research_data(writeFromDate=writeFromDate, writeToDate=writeToDate)
print(df)
for index, row in df.iterrows():
    print(f"Index: {index}")
    print(f"종목명: {row['종목명']}")
    print(f"제목: {row['제목']}")
    print(f"브로커: {row['브로커']}")
    print(f"파일보기: {row['파일보기']}")
    print(f"작성일: {row['작성일']}")
    print(f"번호: {row['번호']}")
