
# Automated Stock News Fetcher

This project fetches the latest stock market articles from various financial institutions' websites and sends them via a bot. Each institution has its own parsing function, and all follow a similar structure.

## How It Works

The script loops through multiple institutions (each with their own website and article structure) and checks for new articles. If any new article is found, the content is processed and sent via a bot (such as a messaging bot like Telegram). If the message exceeds 3500 characters, it sends the content in parts to avoid exceeding message length limits.

### Key Functions

- **Main loop**: The script runs through each financial institution's check function and fetches the latest articles.
- **Article parsing**: Each institution has its own parsing logic to extract new articles from their website.
- **Message Sending**: If new articles are found, the bot sends the articles to a defined recipient or channel. Messages are sent asynchronously.

### Institutions Covered
- LS
- ShinHanInvest
- NHQV
- HANA
- KB
- Samsung
- Sangsanginib (currently commented out)
- Shinyoung
- Miraeasset
- Hmsec
- Kiwoom
- Koreainvestment
- DAOL

### Example Function: NHQV_checkNewArticle

```python
def NHQV_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER
    global firm_info

    SEC_FIRM_ORDER = 2
    ARTICLE_BOARD_ORDER = 0
    requests.packages.urllib3.disable_warnings()

    TARGET_URL = 'https://m.nhqv.com/research/commonTr.json'
    sendMessageText = ''

    try:
        sendMessageText += NHQV_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    except:
        if len(sendMessageText) > 3500:
            print("Partial message sent due to size limit.")
            asyncio.run(sendMessage(GetSendMessageTitle() + sendMessageText))
            sendMessageText = ''

    return sendMessageText
```

Each institution's function follows the same structure:
1. Set global variables for `SEC_FIRM_ORDER` and `ARTICLE_BOARD_ORDER`.
2. Define the target URL.
3. Call the parsing function for that institution.
4. If a message exceeds the length limit, send it in parts.

### Message Sending and Article Download
The bot ensures that the messages are sent in chunks if they are too long, and articles are downloaded as PDFs where applicable.

### Usage
To run the script, ensure all required dependencies are installed, then execute:

```bash
python3 main.py
```

The main function will handle the fetching and message sending automatically.

### Requirements
- Python 3.10.12
- Required libraries: `requests`, `asyncio`, `json`, `selenium`

### Future Enhancements
- Implement error handling for network issues.
- Add more financial institutions.
- Optimize message sending for batch processing.

