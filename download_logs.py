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
        self.cache_file = 'upload_cache.json'
        self.cache_folder_name = 'cache'
        self.cache_folder_id = None
        self.service = self.authenticate()
        print("Initializing cache from Drive...")
        self.download_cache = self._initialize_cache()
        
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

    def _initialize_cache(self):
        """Initialize cache from Drive."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Error reading local cache, creating new one")
        return {'folders': {}, 'files': {}}

    def find_folder(self, folder_name, parent_id=None):
        """Find a folder in Drive using cache first."""
        cache_key = f"{parent_id or 'root'}:{folder_name}"
        if cache_key in self.download_cache['folders']:
            return self.download_cache['folders'][cache_key]
        
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
                folder_id = files[0]['id']
                self.download_cache['folders'][cache_key] = folder_id
                return folder_id
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
                    pageSize=1000,  # Maximum page size
                    pageToken=page_token
                ).execute()
                
                all_folders.extend(results.get('files', []))
                
                # Get the next page token
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                print(f'Error listing folders: {e}')
                break
        
        print(f"Found {len(all_folders)} folders in Drive")
        return all_folders

    def download_file(self, file_id, output_path, force=False):
        """Download a file from Drive. If force is True, download regardless of cache."""
        if os.path.exists(output_path) and not force:
            # Check if we need to update the file
            cache_key = f"{os.path.dirname(output_path)}:{os.path.basename(output_path)}"
            if cache_key in self.download_cache['files']:
                return False  # File exists and is in cache, skip download
        
        try:
            # First get the file metadata to get the size
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
                            pbar.update(current - last_progress)  # Update only the difference
                            last_progress = current
                    except Exception as chunk_error:
                        print(f"\nError during chunk download: {chunk_error}")
                        return False
            
            # Save the file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                fh.seek(0)
                f.write(fh.read())
            
            # Update cache
            cache_key = f"{os.path.dirname(output_path)}:{os.path.basename(output_path)}"
            self.download_cache['files'][cache_key] = {
                'id': file_id,
                'downloaded_at': datetime.now().isoformat()
            }
            
            return True
        except Exception as e:
            print(f'Error downloading file: {e}')
            return False

def count_pending_downloads(battle_logs_id, timestamp_folders, downloader):
    """Count how many files need to be downloaded."""
    count = 0
    logs_dir = './logs'
    
    for folder in timestamp_folders:
        local_path = os.path.join(logs_dir, folder['name'], 'battle_log.json')
        if not os.path.exists(local_path):
            count += 1
    
    return count

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
    
    # Count total operations needed
    total_operations = count_pending_downloads(battle_logs_id, timestamp_folders, downloader)
    
    if total_operations == 0:
        print("No new files to download.")
        return
    
    print(f"Found {total_operations} pending download operations")
    
    # Download logs
    downloaded_count = 0
    skipped_count = 0
    
    with tqdm(total=total_operations, desc="Overall Progress", unit="file") as pbar:
        for folder in timestamp_folders:
            # Construct local path
            local_folder_path = os.path.join('./logs', folder['name'])
            local_file_path = os.path.join(local_folder_path, 'battle_log.json')
            
            # Find battle_log.json in the timestamp folder
            query = f"name='battle_log.json' and '{folder['id']}' in parents"
            results = downloader.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                if downloader.download_file(files[0]['id'], local_file_path):
                    downloaded_count += 1
                    pbar.update(1)
                else:
                    skipped_count += 1
    
    print(f"\nDownload Summary:")
    print(f"Files downloaded: {downloaded_count}")
    print(f"Files skipped (already existed): {skipped_count}")
    
    # Save cache
    with open(downloader.cache_file, 'w') as f:
        json.dump(downloader.download_cache, f, indent=2)
    print("Cache updated")

if __name__ == '__main__':
    download_logs()