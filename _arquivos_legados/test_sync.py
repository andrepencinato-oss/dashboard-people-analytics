import drive_sync
import excel_reader
import json

try:
    print("Fetching file from Google Drive...")
    file_path = drive_sync.fetch_latest_excel()
    print(f"File fetched successfully: {file_path}")
    print("Processing excel file...")
    data = excel_reader.process_excel_files(file_path)
    print(f"Success! Extracted {len(data)} records.")
    print("Sample data:", json.dumps(data[:2], indent=2, ensure_ascii=False))
except Exception as e:
    import traceback
    traceback.print_exc()
