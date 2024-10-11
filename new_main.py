import asyncio
import run.scrap_upload_pdf as scrap_upload_pdf
import run.scrap_main as scrap_main
import run.scrap_send_main as scrap_send_main

def main():
    if scrap_main.main():
        scrap_send_main.main()

    await scrap_upload_pdf.main()     


if __name__ == "__main__":
    main()
    # asyncio.run(main())  # 비동기 main 함수 실행
