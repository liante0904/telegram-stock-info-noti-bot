import os
import sys
from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

def upload(*args):
    # 현재 모듈의 파일 경로를 가져옵니다.
    current_file_path = os.path.abspath(__file__)

    # __main__ 모듈의 경로를 가져옵니다.
    main_module_path = sys.modules['__main__'].__file__

    # 절대 경로로 변환합니다.
    main_module_path = os.path.abspath(main_module_path)
    
    # 프로젝트 경로로 이동 
    main_module_path =os.path.dirname(main_module_path)

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
    else: strFileName = args[0]

    print('********************')
    print(f'FileName: {strFileName}')

    uploadfiles=( (strFileName),)
    folderId = '1jn8tAPBc2OIK3jvDzyOr9NUBghZEn7Nb'
    uploadFileId = ''
    for f in uploadfiles:
        fname = f
        metadata={'name':fname, 'parents': [ folderId ],'mimeType':None}
        res = drive.files().create(body=metadata, media_body=fname).execute()
        if res:
            print('uploadFileName %s'%fname)
            print('uploadFileId %s'%res.get('id'))
            uploadFileId = res.get('id')

    googleDriveUrl  = 'https://drive.google.com/file/d/'
    googleDriveViewerUrl = 'https://drive.google.com/u/0/uc?id='
    googleDriveUrl          += uploadFileId
    googleDriveViewerUrl    += uploadFileId
    # print(f'google drive URL {googleDriveUrl}')
    print(f'google driveViewr URL {googleDriveViewerUrl}')
    return googleDriveViewerUrl
            