from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

def gd(*args):
    print('********************')
    strFileName = ''

    print(args[0])
    store = file.Storage('storage.json')
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
            