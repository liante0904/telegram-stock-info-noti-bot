from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

store = file.Storage('storage.json')
creds = store.get()
drive = build('drive', 'v3', http=creds.authorize(Http()))
uploadfiles=( ('test.pdf'),)
folderId = '1jn8tAPBc2OIK3jvDzyOr9NUBghZEn7Nb'
for f in uploadfiles:
    fname = f
    metadata={'name':fname, 'parents': [ folderId ],'mimeType':None}
    res = drive.files().create(body=metadata, media_body=fname).execute()
    if res:
        print('upload %s'%fname)
        print('upload %s'%res.get('id'))
        