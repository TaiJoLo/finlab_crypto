from __future__ import print_function
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file']


def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)

        # Call the Drive v3 API
        results = service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            print('No files found.')
            return
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

        # Upload and update logic
        folder_path = "/Users/luodairou/Desktop/finlab_crypto/history"
        folder_name = os.path.basename(folder_path)
        folder_id = None

        # Check if the folder already exists
        existing_folders = service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
            pageSize=1,
            fields="files(id)"
        ).execute()

        if existing_folders.get('files'):
            folder_id = existing_folders['files'][0]['id']
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            created_folder = service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            folder_id = created_folder['id']

        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            mime_type = 'application/octet-stream'  # Adjust MIME type as needed

            # Add this line for debugging
            print("Uploading file:", file_path, file_name)

            file_metadata = {
                'name': file_name,

            }

            media = MediaFileUpload(
                file_path, mimetype=mime_type, resumable=True)

            existing_files = service.files().list(
                q=f"name='{file_name}' and '{folder_id}' in parents",
                fields="files(id)"
            ).execute()

            if existing_files.get('files'):
                file_id = existing_files['files'][0]['id']
                update_request = service.files().update(
                    fileId=file_id,
                    addParents=folder_id,
                    body=file_metadata,
                    media_body=media
                )
                response = None
                while response is None:
                    status, response = update_request.next_chunk()
                    if status:
                        print("Updated %d%%." %
                              int(status.progress() * 100))
                print("File updated1:", file_name)
            else:
                create_request = service.files().create(
                    body=file_metadata,
                    media_body=media
                )
                response = None
                while response is None:
                    status, response = create_request.next_chunk()
                    if status:
                        print("Uploaded %d%%." %
                              int(status.progress() * 100))
                print("File uploaded2:", file_name)

    except HttpError as error:
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()
