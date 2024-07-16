import os
import sys
import hashlib
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client import file, client, tools

SCOPES = ['https://www.googleapis.com/auth/drive']

def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def file_exists(drive, file_name, file_md5, folder_id):
    query = f"'{folder_id}' in parents and name='{file_name}' and trashed=false"
    results = drive.files().list(q=query, spaces='drive', fields='files(id, name, md5Checksum)').execute()
    items = results.get('files', [])
    for item in items:
        if item.get('md5Checksum') == file_md5:
            return item['id']
    return None

def delete_duplicate_files(drive, folder_id):
    query = f"'{folder_id}' in parents and trashed=false"
    results = drive.files().list(q=query, spaces='drive', fields='files(id, name, md5Checksum, createdTime, modifiedTime)').execute()
    items = results.get('files', [])
    
    md5_dict = {}
    for item in items:
        file_md5 = item.get('md5Checksum')
        if file_md5:
            if file_md5 in md5_dict:
                existing_item = md5_dict[file_md5]
                existing_time = existing_item['createdTime']
                current_time = item['createdTime']
                # 최신 파일을 삭제하는 조건
                if current_time > existing_time:
                    print(f"Deleting duplicate file: {item['name']} ({item['id']})")
                    drive.files().delete(fileId=item['id']).execute()
                else:
                    print(f"Deleting duplicate file: {existing_item['name']} ({existing_item['id']})")
                    drive.files().delete(fileId=existing_item['id']).execute()
                    md5_dict[file_md5] = item
            else:
                md5_dict[file_md5] = item

def upload(*args):
    # 현재 모듈의 파일 경로를 가져옵니다.
    current_file_path = os.path.abspath(__file__)

    # __main__ 모듈의 경로를 가져옵니다.
    main_module_path = sys.modules['__main__'].__file__

    # 절대 경로로 변환합니다.
    main_module_path = os.path.abspath(main_module_path)
    
    # 프로젝트 경로로 이동 
    main_module_path = os.path.dirname(main_module_path)

    print("메인 파일 경로:", main_module_path)
    print('********************')
    strFileName = ''

    print(args[0])
    print(os.path.join(main_module_path, 'storage.json'))
    store = file.Storage(os.path.join(main_module_path, 'storage.json'))
    creds = store.get()
    drive = build('drive', 'v3', http=creds.authorize(Http()))
    if args[0].isspace(): 
        print('fileName is space')
        return 
    else: 
        strFileName = args[0]

    print('********************')
    print(f'FileName: {strFileName}')

    uploadfiles = (strFileName,)
    folderId = '1jn8tAPBc2OIK3jvDzyOr9NUBghZEn7Nb'
    uploadFileId = ''

    for f in uploadfiles:
        fname = f
        file_md5 = calculate_md5(fname)
        existing_file_id = file_exists(drive, fname, file_md5, folderId)
        if existing_file_id:
            print(f"File '{fname}' already exists in folder ID '{folderId}' with the same content. Upload canceled.")
            continue

        metadata = {'name': fname, 'parents': [folderId], 'mimeType': None}
        media = MediaFileUpload(fname)
        res = drive.files().create(body=metadata, media_body=media).execute()
        if res:
            print('uploadFileName %s' % fname)
            print('uploadFileId %s' % res.get('id'))
            uploadFileId = res.get('id')

    googleDriveUrl = 'https://drive.google.com/file/d/'
    googleDriveViewerUrl = 'https://drive.google.com/u/0/uc?id='
    googleDriveUrl += uploadFileId
    googleDriveViewerUrl += uploadFileId
    # print(f'google drive URL {googleDriveUrl}')
    print(f'google driveViewer URL {googleDriveViewerUrl}')
    return googleDriveViewerUrl

if __name__ == "__main__":
    action = sys.argv[1]  # 'upload' or 'delete_duplicates'
    file_name = sys.argv[2] if len(sys.argv) > 2 else None

    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    drive = build('drive', 'v3', http=creds.authorize(Http()))

    folder_id = '1jn8tAPBc2OIK3jvDzyOr9NUBghZEn7Nb'

    if action == 'upload' and file_name:
        upload(file_name)
    elif action == 'delete_duplicates':
        delete_duplicate_files(drive, folder_id)
    else:
        print("Invalid action or missing file name for upload.")
