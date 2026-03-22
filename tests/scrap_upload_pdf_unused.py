import os
import asyncio
from models.GoogleDrive import GoogleDrive  # 작성한 GoogleDrive 클래스를 저장한 파일을 import합니다.
from models.SecretKey import SecretKey

SECRET_KEY = SecretKey()
project_dir = SECRET_KEY.PROJECT_DIR

async def upload_all_pdfs(google_drive, directory):
    """지정된 디렉토리에서 모든 PDF 파일을 Google Drive에 업로드하는 함수"""
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found in the directory.")
        return

    for pdf_file in pdf_files:
        file_path = os.path.join(directory, pdf_file)
        print(f"Uploading {file_path}...")
        await google_drive.upload(file_path)

async def main():
    print('=============scrap_upload_pdf=============')
    google_drive = GoogleDrive()
    google_drive.initialize_drive_service()  # Google Drive 인증 및 서비스 초기화
    await upload_all_pdfs(google_drive, project_dir)  # 지정된 디렉토리에서 모든 PDF 파일 업로드


if __name__ == "__main__":
    asyncio.run(main())  # 비동기 main 함수 실행
