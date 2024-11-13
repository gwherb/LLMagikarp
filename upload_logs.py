from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import os
import pickle
import json
from datetime import datetime
import io
from tqdm import tqdm

class ProgressMediaUpload(MediaFileUpload):
    def __init__(self, filename, pbar, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self._pbar = pbar
        self._file = None
        self._size = os.path.getsize(filename)
        
    def __len__(self):
        return self._size
        
    def read(self, chunk_size=None):
        chunk = super().read(chunk_size)
        if chunk is not None and self._pbar is not None:
            self._pbar.update(len(chunk))
        return chunk

class DriveUploader:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.creds = None
        self.cache_file = 'upload_cache.json'
        self.cache_folder_name = 'cache'
        self.cache_folder_id = None
        self.service = self.authenticate()
        print("Initializing cache from Drive...")
        self.upload_cache = self._initialize_cache()
        
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

    def _get_or_create_cache_folder(self):
        """Find or create the cache folder in Drive."""
        # Check if we already found the cache folder
        if self.cache_folder_id:
            return self.cache_folder_id

        # Look for existing cache folder
        query = f"name='{self.cache_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = results.get('files', [])
        
        if files:
            self.cache_folder_id = files[0]['id']
        else:
            # Create cache folder if it doesn't exist
            folder_metadata = {
                'name': self.cache_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            self.cache_folder_id = folder.get('id')
            print(f"Created cache folder in Drive")
        
        return self.cache_folder_id

    def _download_drive_cache(self):
        """Download cache file from Drive if it exists."""
        cache_folder_id = self._get_or_create_cache_folder()
        query = f"name='{self.cache_file}' and '{cache_folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields='files(id)').execute()
        files = results.get('files', [])
        
        if files:
            file_id = files[0]['id']
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()
            
            fh.seek(0)
            try:
                return json.loads(fh.read().decode())
            except json.JSONDecodeError:
                print("Error reading Drive cache, creating new one")
                return {'folders': {}, 'files': {}}
        return {'folders': {}, 'files': {}}

    def _initialize_cache(self):
        """Initialize cache by merging local and Drive caches."""
        drive_cache = self._download_drive_cache()
        
        # Load local cache if it exists
        local_cache = {'folders': {}, 'files': {}}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    local_cache = json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Merge caches, preferring the most recent entries
        merged_cache = {'folders': {}, 'files': {}}
        
        # Merge folders
        all_folder_keys = set(drive_cache['folders'].keys()) | set(local_cache['folders'].keys())
        for key in all_folder_keys:
            merged_cache['folders'][key] = (
                drive_cache['folders'].get(key) or local_cache['folders'].get(key)
            )
        
        # Merge files, comparing timestamps if available
        all_file_keys = set(drive_cache['files'].keys()) | set(local_cache['files'].keys())
        for key in all_file_keys:
            drive_file = drive_cache['files'].get(key, {})
            local_file = local_cache['files'].get(key, {})
            
            if not drive_file:
                merged_cache['files'][key] = local_file
            elif not local_file:
                merged_cache['files'][key] = drive_file
            else:
                # Compare timestamps if available
                drive_time = drive_file.get('uploaded_at', '')
                local_time = local_file.get('uploaded_at', '')
                merged_cache['files'][key] = (
                    drive_file if drive_time >= local_time else local_file
                )
        
        return merged_cache

    def _save_cache(self):
        """Save cache both locally and to Drive."""
        # Save locally
        with open(self.cache_file, 'w') as f:
            json.dump(self.upload_cache, f, indent=2)
        
        # Save to Drive
        cache_folder_id = self._get_or_create_cache_folder()
        
        # Check if cache file already exists in Drive
        query = f"name='{self.cache_file}' and '{cache_folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields='files(id)').execute()
        files = results.get('files', [])
        
        # Prepare file metadata and media
        file_metadata = {
            'name': self.cache_file,
            'parents': [cache_folder_id]
        }
        
        media = MediaFileUpload(
            self.cache_file,
            mimetype='application/json',
            resumable=True
        )
        
        if files:
            # Update existing file
            file_id = files[0]['id']
            self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Create new file
            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

    def create_folder(self, folder_name, parent_id=None):
        # Check cache first
        cache_key = f"{parent_id or 'root'}:{folder_name}"
        if cache_key in self.upload_cache['folders']:
            return self.upload_cache['folders'][cache_key]
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            folder_id = file.get('id')
            # Update cache
            self.upload_cache['folders'][cache_key] = folder_id
            self._save_cache()
            return folder_id
        except Exception as e:
            print(f'Error creating folder: {e}')
            return None

    def find_folder(self, folder_name, parent_id=None):
        # Check cache first
        cache_key = f"{parent_id or 'root'}:{folder_name}"
        if cache_key in self.upload_cache['folders']:
            return self.upload_cache['folders'][cache_key]
        
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
                # Update cache
                self.upload_cache['folders'][cache_key] = folder_id
                self._save_cache()
                return folder_id
            return None
        except Exception as e:
            print(f'Error finding folder: {e}')
            return None

    def file_exists(self, filename, parent_id):
        """Check if a file exists using local cache first, then API if needed."""
        cache_key = f"{parent_id}:{filename}"
        
        # Check cache first
        if cache_key in self.upload_cache['files']:
            return True
            
        # If not in cache, check Drive API
        query = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
        
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, modifiedTime)'
            ).execute()
            files = results.get('files', [])
            
            if files:
                # Update cache with the found file
                self.upload_cache['files'][cache_key] = {
                    'id': files[0]['id'],
                    'uploaded_at': files[0]['modifiedTime']
                }
                self._save_cache()
                return True
            return False
        except Exception as e:
            print(f'Error checking file existence: {e}')
            return False

    def upload_file(self, filepath, parent_id):
        """Upload a file to Google Drive and update the cache."""
        filename = os.path.basename(filepath)
        cache_key = f"{parent_id}:{filename}"
        
        # Check existence (this will also update cache if file exists)
        if self.file_exists(filename, parent_id):
            print(f'File {filename} already exists in Drive, skipping...')
            return None
        
        file_metadata = {
            'name': filename,
            'parents': [parent_id]
        }
        
        file_size = os.path.getsize(filepath)
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=f'Uploading {filename}') as pbar:
            media = ProgressMediaUpload(
                filepath,
                pbar=pbar,
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            try:
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                file_id = file.get('id')
                
                # Update cache
                self.upload_cache['files'][cache_key] = {
                    'id': file_id,
                    'uploaded_at': datetime.now().isoformat()
                }
                self._save_cache()
                
                return file_id
            except Exception as e:
                print(f'\nError uploading file: {e}')
                return None

def count_pending_uploads(logs_dir, uploader):
    """Count how many files need to be uploaded."""
    count = 0
    battle_logs_id = uploader.find_folder('BattleLogs')
    if not battle_logs_id:
        return 0
        
    for timestamp_dir in os.listdir(logs_dir):
        if not os.path.isdir(os.path.join(logs_dir, timestamp_dir)):
            continue
            
        timestamp_folder_id = uploader.find_folder(timestamp_dir, battle_logs_id)
        if not timestamp_folder_id:
            count += 1  # Need to create folder
            
        log_path = os.path.join(logs_dir, timestamp_dir, 'battle_log.json')
        if os.path.exists(log_path):
            if timestamp_folder_id and not uploader.file_exists('battle_log.json', timestamp_folder_id):
                count += 1
            elif not timestamp_folder_id:
                count += 1
    
    return count

def upload_logs():
    print("Initializing Drive uploader...")
    uploader = DriveUploader()
    
    # Find or create main BattleLogs folder
    battle_logs_id = uploader.find_folder('BattleLogs')
    if not battle_logs_id:
        battle_logs_id = uploader.create_folder('BattleLogs')
        print("Created BattleLogs folder")
    
    # Process local logs
    logs_dir = './logs'
    uploaded_count = 0
    skipped_count = 0
    
    # Count total operations needed
    print("Analyzing logs directory...")
    total_operations = count_pending_uploads(logs_dir, uploader)
    
    if total_operations == 0:
        print("No new files to upload.")
    else:
        print(f"Found {total_operations} pending upload operations")
        
        # Create progress bar for overall progress
        with tqdm(total=total_operations, desc="Overall Progress", unit="file") as pbar:
            for timestamp_dir in os.listdir(logs_dir):
                if not os.path.isdir(os.path.join(logs_dir, timestamp_dir)):
                    continue
                    
                # Create or find timestamp folder in Drive
                timestamp_folder_id = uploader.find_folder(timestamp_dir, battle_logs_id)
                if not timestamp_folder_id:
                    timestamp_folder_id = uploader.create_folder(timestamp_dir, battle_logs_id)
                    pbar.update(1)
                    
                # Upload battle_log.json
                log_path = os.path.join(logs_dir, timestamp_dir, 'battle_log.json')
                if os.path.exists(log_path):
                    if not uploader.file_exists('battle_log.json', timestamp_folder_id):
                        uploader.upload_file(log_path, timestamp_folder_id)
                        uploaded_count += 1
                        pbar.update(1)
                    else:
                        skipped_count += 1
    
        print(f"\nUpload Summary:")
        print(f"Files uploaded: {uploaded_count}")
        print(f"Files skipped (already existed): {skipped_count}")
    
    # Always update cache in Drive at the end, regardless of changes
    print("Updating cache in Drive...")
    uploader._save_cache()
    print("Cache update complete")

if __name__ == '__main__':
    upload_logs()