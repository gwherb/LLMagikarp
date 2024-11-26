from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import json
from datetime import datetime
from collections import defaultdict
from tabulate import tabulate

class LogDiagnostics:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.creds = None
        self.cache_file = 'upload_cache.json'
        self.logs_dir = './logs'
        self.service = self.authenticate()
        self.cache_data = self._load_cache()
        self.drive_data = None
        self.local_data = None
        
    def authenticate(self):
        """Authenticate with Google Drive API with improved token handling"""
        # Try to load existing token
        if os.path.exists('token.pickle'):
            try:
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)
                
                # Test if token is valid
                if self.creds and self.creds.valid:
                    return build('drive', 'v3', credentials=self.creds)
                
                # Try refreshing expired token
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                        return build('drive', 'v3', credentials=self.creds)
                    except Exception as e:
                        print(f"Token refresh failed: {e}")
                        # Token refresh failed, delete the invalid token
                        os.remove('token.pickle')
                        self.creds = None
            except Exception as e:
                print(f"Error loading token: {e}")
                os.remove('token.pickle')
                self.creds = None
        
        # If we get here, we need new credentials
        try:
            print("Initiating new authentication flow...")
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console"
                )
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', self.SCOPES)
            self.creds = flow.run_local_server(port=8080)
            
            # Save the new token
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
                
            return build('drive', 'v3', credentials=self.creds)
            
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {'folders': {}, 'files': {}}
        except json.JSONDecodeError:
            print("Error reading cache file")
            return {'folders': {}, 'files': {}}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache_data, f, indent=2)

    def scan_drive(self):
        """Scan Google Drive for battle logs with pagination."""
        print("Scanning Google Drive...")
        drive_data = defaultdict(dict)
        
        # Find BattleLogs folder
        battle_logs_id = None
        for cache_key, folder_id in self.cache_data['folders'].items():
            if cache_key.endswith(':BattleLogs'):
                battle_logs_id = folder_id
                break
        
        if not battle_logs_id:
            print("BattleLogs folder not found in cache!")
            return drive_data
        
        # Get all timestamp folders with pagination
        page_token = None
        folder_count = 0
        
        while True:
            query = f"'{battle_logs_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            try:
                results = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name)',
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                
                for folder in results.get('files', []):
                    folder_count += 1
                    # Find battle_log.json in each folder
                    file_query = f"name='battle_log.json' and '{folder['id']}' in parents"
                    file_results = self.service.files().list(
                        q=file_query,
                        fields='files(id, name, modifiedTime)'
                    ).execute()
                    
                    files = file_results.get('files', [])
                    if files:
                        drive_data[folder['name']] = {
                            'folder_id': folder['id'],
                            'file_id': files[0]['id'],
                            'modified': files[0]['modifiedTime']
                        }
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                print(f"Error scanning Drive: {e}")
                break
        
        print(f"Found {folder_count} folders in Drive")
        self.drive_data = drive_data
        return drive_data

    def scan_local(self):
        """Scan local logs directory."""
        print("Scanning local files...")
        local_data = defaultdict(dict)
        
        if not os.path.exists(self.logs_dir):
            return local_data
        
        for timestamp_dir in os.listdir(self.logs_dir):
            log_path = os.path.join(self.logs_dir, timestamp_dir, 'battle_log.json')
            if os.path.exists(log_path):
                local_data[timestamp_dir]['path'] = log_path
                local_data[timestamp_dir]['modified'] = datetime.fromtimestamp(
                    os.path.getmtime(log_path)).isoformat()
        
        self.local_data = local_data
        return local_data

    def update_cache_from_drive(self):
        """Update cache to match Drive contents."""
        print("\nUpdating cache to match Drive contents...")
        
        # Get BattleLogs folder ID
        battle_logs_id = None
        for cache_key, folder_id in self.cache_data['folders'].items():
            if cache_key.endswith(':BattleLogs'):
                battle_logs_id = folder_id
                break
        
        if not battle_logs_id:
            print("Error: BattleLogs folder ID not found in cache")
            return
        
        # Create new cache structure
        new_cache = {
            'folders': {'root:BattleLogs': battle_logs_id},
            'files': {}
        }
        
        # Add all folders and files from Drive scan
        for timestamp, data in self.drive_data.items():
            # Add folder to cache
            folder_cache_key = f"{battle_logs_id}:{timestamp}"
            new_cache['folders'][folder_cache_key] = data['folder_id']
            
            # Add file to cache
            file_cache_key = f"{data['folder_id']}:battle_log.json"
            new_cache['files'][file_cache_key] = {
                'id': data['file_id'],
                'uploaded_at': data['modified']
            }
        
        # Update cache
        self.cache_data = new_cache
        self._save_cache()
        print("Cache updated successfully")

    def analyze_discrepancies(self):
        """Analyze discrepancies between Drive, cache, and local files."""
        if not self.drive_data:
            self.scan_drive()
        if not self.local_data:
            self.scan_local()
            
        # Get all unique timestamps
        all_timestamps = set()
        all_timestamps.update(self.drive_data.keys())
        all_timestamps.update(self.local_data.keys())
        
        discrepancies = []
        
        for timestamp in sorted(all_timestamps):
            in_drive = timestamp in self.drive_data
            in_local = timestamp in self.local_data
            
            status = []
            if not (in_drive and in_local):
                if not in_drive:
                    status.append("Missing from Drive")
                if not in_local:
                    status.append("Missing locally")
                
                discrepancies.append([
                    timestamp,
                    "✓" if in_drive else "✗",
                    "✓" if in_local else "✗",
                    " & ".join(status)
                ])
        
        return discrepancies

    def print_report(self):
        """Print a detailed report and update cache."""
        discrepancies = self.analyze_discrepancies()
        
        print("\n=== Log Files Diagnostic Report ===\n")
        
        # Summary counts
        drive_count = len(self.drive_data)
        local_count = len(self.local_data)
        
        print(f"Total files found:")
        print(f"  - In Google Drive: {drive_count}")
        print(f"  - In local directory: {local_count}")
        
        if not discrepancies:
            print("\n✓ No discrepancies found between Drive and local files!")
        else:
            print(f"\nFound {len(discrepancies)} discrepancies:\n")
            headers = ["Timestamp", "Drive", "Local", "Issues"]
            print(tabulate(discrepancies, headers=headers, tablefmt="grid"))
            
            print("\nRecommended actions:")
            print("1. For files missing locally: Run download_logs.py")
            print("2. For files missing from Drive: Run upload_logs.py")
        
        # Update cache to match Drive
        self.update_cache_from_drive()

def main():
    diagnostics = LogDiagnostics()
    diagnostics.print_report()

if __name__ == "__main__":
    main()