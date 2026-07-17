import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # 1. Update the Excel file on Google Drive
    print("Updating Excel file on Google Drive...")
    folder_id = '1KPwdqfXdiwdhDMftM6VfVEY-xTyjG6x1'
    query = f"'{folder_id}' in parents and name contains 'Extrato' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)", orderBy="createdTime desc", pageSize=1).execute()
    items = results.get('files', [])
    if items:
        file_id = items[0]['id']
        media = MediaFileUpload('DP_-_Colaboradores_-_Extrato_Diário.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        drive_service.files().update(fileId=file_id, media_body=media).execute()
        print("Excel file updated successfully.")
    else:
        print("Excel file not found.")

    # 2. Append text to Google Doc
    print("Appending text to Google Doc...")
    DOCUMENT_ID = '1X7E-BD8cGCHY3HNzTs7PN4LIr0nfUJwOJIO5YFzonB4'
    doc = docs_service.documents().get(documentId=DOCUMENT_ID).execute()
    content = doc.get('body').get('content')
    end_index = content[-1].get('endIndex') - 1
    
    requests = [
        {
            'insertText': {
                'location': {
                    'index': end_index,
                },
                'text': '\n\neu estou aqui\n'
            }
        }
    ]
    docs_service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': requests}).execute()
    print("Google Doc updated successfully.")

if __name__ == '__main__':
    main()
