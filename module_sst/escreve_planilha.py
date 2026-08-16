import os
import io
import traceback
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import xlrd
from xlutils.copy import copy

def main():
    try:
        token_path = r'D:\Projeto geral\People analytics - GP\core\token.json'
        if not os.path.exists(token_path):
            print(f"Error: {token_path} not found")
            return

        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)
        file_id = '1YLbf5CvB-wzzu3XBkfn730o8F-T4a74t'

        # 1. Download
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        # 2. Modify
        fh.seek(0)
        # Read the workbook
        rb = xlrd.open_workbook(file_contents=fh.read(), formatting_info=True)
        rs = rb.sheet_by_index(0)
        
        # Create a writable copy
        wb = copy(rb)
        ws = wb.get_sheet(0)
        
        # Append "estou aqui" to the next empty row in column A
        next_row = rs.nrows
        ws.write(next_row, 0, "estou aqui")
        
        # Save to a temporary local file
        temp_file = 'temp_update.xls'
        wb.save(temp_file)
        
        # 3. Upload/Update
        media = MediaFileUpload(temp_file, mimetype='application/vnd.ms-excel', resumable=True)
        updated_file = drive_service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        
        print("Success! File updated in Drive.")
        os.remove(temp_file)

    except Exception as e:
        print(f"Failed:\n{traceback.format_exc()}")

if __name__ == '__main__':
    main()
