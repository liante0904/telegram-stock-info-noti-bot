import os
import sys
import asyncio
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client import file, client, tools
from models.SecretKey import SecretKey

SECRET_KEY = SecretKey()

SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = SECRET_KEY.GOOGLE_DRIVE_FOLDER_ID
PROJECT_DIR = SECRET_KEY.PROJECT_DIR
class GoogleDrive:
    def __init__(self):
        self.folder_id = FOLDER_ID
        self.scopes = SCOPES
        self.store = None
        self.creds = None
        self.drive_service = None
        self.main_module_path = PROJECT_DIR

    def initialize_drive_service(self):
        """Google Drive 인증 및 서비스 객체 초기화"""
        self.store = file.Storage(os.path.join(self.main_module_path, 'storage.json'))
        self.creds = self.store.get()
        if not self.creds or self.creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', self.scopes)
            self.creds = tools.run_flow(flow, self.store)
        self.drive_service = build('drive', 'v3', http=self.creds.authorize(Http()))

    def strip_date_from_filename(self, filename):
        parts = filename.split('_', 1)
        return parts[1] if len(parts) > 1 else filename

    def file_exists(self, file_name_without_date):
        print(f"Checking for files with name: {file_name_without_date} in folder ID: {self.folder_id}")  # 추가된 디버깅 로그
        if self.folder_id is None:
            print("Error: Folder ID is None.")  # 추가된 디버깅 로그
            return None
        query = f"'{self.folder_id}' in parents and name contains '{file_name_without_date}' and trashed=false"
        results = self.drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        for item in items:
            if file_name_without_date in item.get('name'):
                return item['id']
        return None

    async def upload(self, file_name):
        """파일을 업로드하는 비동기 함수"""
        if not file_name.strip():  # 파일명이 비어 있는지 체크
            print('FileName is empty or space.')
            return None

        print(f'Uploading FileName: {file_name}')
        
        # 비슷한 이름의 파일이 이미 존재하는지 확인
        file_name_without_date = self.strip_date_from_filename(file_name)
        
        # 특수 문자 제거
        sanitized_name = re.sub(r"[^\w\s]", "", file_name_without_date)
        
        existing_file_id = self.file_exists(sanitized_name)
        if existing_file_id:
            print(f"File with similar name '{sanitized_name}' already exists in folder ID '{self.folder_id}'. Upload canceled.")
            return None

        # 파일 업로드
        metadata = {'name': file_name, 'parents': [self.folder_id], 'mimeType': None}
        media = MediaFileUpload(file_name)
        res = self.drive_service.files().create(body=metadata, media_body=media).execute()
        
        if res:
            upload_file_id = res.get('id')
            print(f'Uploaded FileName: {file_name}')
            print(f'Uploaded FileId: {upload_file_id}')
            google_drive_viewer_url = f'https://drive.google.com/u/0/uc?id={upload_file_id}'
            print(f'Google Drive Viewer URL: {google_drive_viewer_url}')
            return google_drive_viewer_url
        else:
            print('Upload failed.')
            return None


async def main(action, file_name):
    google_drive = GoogleDrive()
    google_drive.initialize_drive_service()

    if action == 'upload' and file_name:
        await google_drive.upload(file_name)
    else:
        print("Invalid action or missing file name for upload.")

if __name__ == "__main__":
    action = sys.argv[1]  # 'upload' 또는 'delete_duplicates'
    file_name = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(main(action, file_name))
