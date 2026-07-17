import os
import io
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from data_processor import get_credentials

def main():
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    
    # The known file ID for absenteismo
    FILE_ID = '1o92c6a-k0KC4fSAVYiwzvp2vF1nXuZ1y'
    file_info = service.files().get(fileId=FILE_ID, fields='parents').execute()
    parents = file_info.get('parents')
    if parents:
        parent_id = parents[0]
        print(f"Parent folder ID: {parent_id}")
        
        # Search for Headcount file in the same folder
        query = f"'{parent_id}' in parents and name contains 'Headcount' and trashed = false"
        results = service.files().list(q=query, fields='files(id, name, createdTime)', orderBy='createdTime desc').execute()
        files = results.get('files', [])
        
        if files:
            headcount_file = files[0]
            print(f"Found Headcount file: {headcount_file['name']} (ID: {headcount_file['id']})")
            
            # Download it
            output_path = os.path.join(os.path.dirname(__file__), 'downloaded_headcount.xlsx')
            request = service.files().get_media(fileId=headcount_file['id'])
            fh = io.FileIO(output_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.close()
            
            print(f"Downloaded to {output_path}")
            
            # Read and print columns
            try:
                df_hc = pd.read_excel(output_path)
                print("Headcount Columns:")
                print(df_hc.columns.tolist())
                print(df_hc.head(5).to_string())
            except Exception as e:
                print(f"Error reading Headcount: {e}")
        else:
            print("No Headcount file found in the parent folder.")
            # fallback, search everywhere
            query = f"name contains 'Headcount' and trashed = false"
            results = service.files().list(q=query, fields='files(id, name, createdTime)', orderBy='createdTime desc').execute()
            files = results.get('files', [])
            if files:
                print(f"Found outside parent: {files[0]['name']}")
            
    else:
        print("No parent folder found for the Absenteísmo file.")

if __name__ == '__main__':
    main()
