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
import sys

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
        """Authenticate with Google Drive."""
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

    def _load_cache(self):
        """Load the cache file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {'folders': {}, 'files': {}}
        except json.JSONDecodeError:
            print("Error reading cache file")
            return {'folders': {}, 'files': {}}

    def scan_drive(self):
        """Scan Google Drive for battle logs."""
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
        
        # Get all timestamp folders
        query = f"'{battle_logs_id}' in parents and mimeType='application/vnd.google-apps.folder'"
        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1000
            ).execute()
            
            # For each timestamp folder, look for battle_log.json
            for folder in results.get('files', []):
                file_query = f"name='battle_log.json' and '{folder['id']}' in parents"
                file_results = self.service.files().list(
                    q=file_query,
                    fields='files(id, name, modifiedTime)'
                ).execute()
                
                files = file_results.get('files', [])
                if files:
                    drive_data[folder['name']]['file_id'] = files[0]['id']
                    drive_data[folder['name']]['modified'] = files[0]['modifiedTime']
        
        except Exception as e:
            print(f"Error scanning Drive: {e}")
        
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
        all_timestamps.update(folder_name for _, folder_name in 
                            [key.split(':') for key in self.cache_data['folders'].keys() 
                             if key.startswith('1MG7hC406ZBcE2WQPhFY0TiJqXOoUNti2:')])
        
        discrepancies = []
        
        for timestamp in sorted(all_timestamps):
            in_drive = timestamp in self.drive_data
            in_local = timestamp in self.local_data
            in_cache = any(key.endswith(f":{timestamp}") for key in self.cache_data['folders'].keys())
            
            status = []
            if not (in_drive and in_local and in_cache):
                if not in_drive:
                    status.append("Missing from Drive")
                if not in_local:
                    status.append("Missing locally")
                if not in_cache:
                    status.append("Missing from cache")
                
                discrepancies.append([
                    timestamp,
                    "✓" if in_drive else "✗",
                    "✓" if in_local else "✗",
                    "✓" if in_cache else "✗",
                    " & ".join(status)
                ])
        
        return discrepancies

    def print_report(self):
        """Print a detailed report of the analysis."""
        discrepancies = self.analyze_discrepancies()
        
        print("\n=== Log Files Diagnostic Report ===\n")
        
        # Summary counts
        drive_count = len(self.drive_data)
        local_count = len(self.local_data)
        cache_count = len([k for k in self.cache_data['folders'].keys() 
                         if k.startswith('1MG7hC406ZBcE2WQPhFY0TiJqXOoUNti2:')])
        
        print(f"Total files found:")
        print(f"  - In Google Drive: {drive_count}")
        print(f"  - In local directory: {local_count}")
        print(f"  - In cache: {cache_count}\n")
        
        if not discrepancies:
            print("✓ No discrepancies found! All systems are in sync.")
        else:
            print(f"Found {len(discrepancies)} discrepancies:\n")
            headers = ["Timestamp", "Drive", "Local", "Cache", "Issues"]
            print(tabulate(discrepancies, headers=headers, tablefmt="grid"))
            
            print("\nRecommended actions:")
            print("1. For files missing locally: Run download_logs.py")
            print("2. For files missing from Drive: Run upload_logs.py")
            print("3. For cache mismatches: The cache will be updated automatically when running either script")

def main():
    diagnostics = LogDiagnostics()
    diagnostics.print_report()

if __name__ == "__main__":
    main()