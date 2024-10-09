import os
import sys
import hashlib
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client import file, client, tools
from models.SecretKey import SecretKey

SECRET_KEY = SecretKey()

SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = SECRET_KEY.GOOGLE_DRIVE_FOLDER_ID


def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def strip_date_from_filename(filename):
    parts = filename.split('_', 1)
    return parts[1] if len(parts) > 1 else filename

def file_exists(drive, file_name_without_date, folder_id):
    query = f"'{folder_id}' in parents and name contains '{file_name_without_date}' and trashed=false"
    results = drive.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    for item in items:
        if file_name_without_date in item.get('name'):
            return item['id']
    return None

def upload(*args):
    current_file_path = os.path.abspath(__file__)
    main_module_path = sys.modules['__main__'].__file__
    main_module_path = os.path.abspath(main_module_path)
    main_module_path = os.path.dirname(main_module_path)

    print("메인 파일 경로:", main_module_path)
    # print('********************')

    # print(args[0])
    # print(os.path.join(main_module_path, 'storage.json'))

    store = file.Storage(os.path.join(main_module_path, 'storage.json'))
    creds = store.get()
    drive = build('drive', 'v3', http=creds.authorize(Http()))

    strFileName = ''
    if args[0].isspace(): 
        print('fileName is space')
        return 
    else: 
        strFileName = args[0]

    # print('********************')
    print(f'FileName: {strFileName}')

    uploadfiles = (strFileName,)
    
    uploadFileId = ''

    for f in uploadfiles:
        fname = f
        file_md5 = calculate_md5(fname)
        file_name_without_date = strip_date_from_filename(fname)
        existing_file_id = file_exists(drive, file_name_without_date, FOLDER_ID)
        if existing_file_id:
            print(f"File with similar name '{file_name_without_date}' already exists in folder ID '{FOLDER_ID}'. Upload canceled.")
            continue

        metadata = {'name': fname, 'parents': [FOLDER_ID], 'mimeType': None}
        media = MediaFileUpload(fname)
        res = drive.files().create(body=metadata, media_body=media).execute()
        if res:
            print('uploadFileName %s' % fname)
            print('uploadFileId %s' % res.get('id'))
            uploadFileId = res.get('id')

    if uploadFileId:
        # googleDriveUrl = 'https://drive.google.com/file/d/'
        googleDriveViewerUrl = 'https://drive.google.com/u/0/uc?id='
        # googleDriveUrl += uploadFileId
        googleDriveViewerUrl += uploadFileId
        print(f'google driveViewer URL {googleDriveViewerUrl}')
        return googleDriveViewerUrl
    else:
        print('No new file uploaded.')
        return None

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
    else:
        print("Invalid action or missing file name for upload.")
