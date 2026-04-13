from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']
MAP_FILE = 'nemt_war_room.html'
TOKEN_FILE = 'drive_token.json'
CREDENTIALS_FILE = 'drive_credentials.json'
DRIVE_FILE_ID_CACHE = 'drive_file_id.txt'

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, SCOPES)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        auth_url, _ = flow.authorization_url(prompt='consent')
        print(f'\nOpen this URL in Chrome:\n{auth_url}\n')
        code = input('Paste the authorization code here: ').strip()
        flow.fetch_token(code=code)
        creds = flow.credentials
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def publish_map():
    """Upload/update nemt_war_room.html to Drive and return shareable link."""
    if not os.path.exists(MAP_FILE):
        return None

    service = get_drive_service()

    # Check if we already have a file ID cached
    file_id = None
    if os.path.exists(DRIVE_FILE_ID_CACHE):
        with open(DRIVE_FILE_ID_CACHE) as f:
            file_id = f.read().strip()

    media = MediaFileUpload(MAP_FILE,
                            mimetype='text/html',
                            resumable=True)

    if file_id:
        # Update existing file
        try:
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        except Exception:
            file_id = None

    if not file_id:
        # Create new file
        file_metadata = {'name': 'NEMT War Room Map'}
        result = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        file_id = result.get('id')
        with open(DRIVE_FILE_ID_CACHE, 'w') as f:
            f.write(file_id)

    # Make publicly readable
    service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    link = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"   🗺️  Map published: {link}")
    return link

if __name__ == "__main__":
    link = publish_map()
    print(f"Map link: {link}")
