from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import os
import pickle
import json
from datetime import datetime
import io
from tqdm import tqdm

class DriveDownloader:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.creds = None
        self.logs_dir = './logs'
        self.service = self.authenticate()
        
    def authenticate(self):
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=8080)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
        
        return build('drive', 'v3', credentials=self.creds)

    def find_folder(self, folder_name, parent_id=None):
        """Find a folder in Drive."""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            return None
        except Exception as e:
            print(f'Error finding folder: {e}')
            return None

    def list_timestamp_folders(self, battle_logs_id):
        """List all timestamp folders in the BattleLogs folder."""
        all_folders = []
        page_token = None
        
        while True:
            query = f"'{battle_logs_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            try:
                results = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name)',
                    pageSize=1000,
                    pageToken=page_token,
                    orderBy='name'  # Sort by name for consistent ordering
                ).execute()
                
                all_folders.extend(results.get('files', []))
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                print(f'Error listing folders: {e}')
                break
        
        print(f"Found {len(all_folders)} folders in Drive")
        return all_folders

    def download_file(self, file_id, output_path):
        """Download a file from Drive."""
        try:
            # Get file size for progress bar
            file_metadata = self.service.files().get(fileId=file_id, fields='size').execute()
            total_size = int(file_metadata.get('size', 0))
            
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            # Setup progress bar with known total size
            with tqdm(total=total_size, unit='B', unit_scale=True, 
                     desc=f"Downloading {os.path.basename(output_path)}") as pbar:
                done = False
                last_progress = 0
                
                while done is False:
                    try:
                        status, done = downloader.next_chunk()
                        if status:
                            current = int(status.progress() * total_size)
                            pbar.update(current - last_progress)
                            last_progress = current
                    except Exception as chunk_error:
                        print(f"\nError during chunk download: {chunk_error}")
                        return False
            
            # Save the file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                fh.seek(0)
                f.write(fh.read())
            
            return True
        except Exception as e:
            print(f'Error downloading file: {e}')
            return False

def download_logs():
    print("Initializing Drive downloader...")
    downloader = DriveDownloader()
    
    # Find BattleLogs folder
    battle_logs_id = downloader.find_folder('BattleLogs')
    if not battle_logs_id:
        print("BattleLogs folder not found in Drive")
        return
    
    # List all timestamp folders
    print("Fetching folder list from Drive...")
    timestamp_folders = downloader.list_timestamp_folders(battle_logs_id)
    
    # Create list of files to download by comparing with local files
    download_queue = []
    for folder in timestamp_folders:
        local_path = os.path.join(downloader.logs_dir, folder['name'], 'battle_log.json')
        if not os.path.exists(local_path):
            download_queue.append(folder)
    
    if not download_queue:
        print("No new files to download.")
        return
    
    print(f"Found {len(download_queue)} files to download")
    
    # Download logs
    downloaded_count = 0
    error_count = 0
    
    with tqdm(total=len(download_queue), desc="Overall Progress", unit="file") as pbar:
        for folder in download_queue:
            # Find battle_log.json in the timestamp folder
            query = f"name='battle_log.json' and '{folder['id']}' in parents"
            results = downloader.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                local_path = os.path.join(downloader.logs_dir, folder['name'], 'battle_log.json')
                if downloader.download_file(files[0]['id'], local_path):
                    downloaded_count += 1
                else:
                    error_count += 1
            else:
                print(f"\nWarning: No battle_log.json found in folder {folder['name']}")
                error_count += 1
            
            pbar.update(1)
    
    print(f"\nDownload Summary:")
    print(f"Files downloaded successfully: {downloaded_count}")
    print(f"Files with errors: {error_count}")

if __name__ == '__main__':
    download_logs()