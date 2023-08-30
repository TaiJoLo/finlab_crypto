from __future__ import print_function
import os
import zipfile
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
        folder_path = "/Users/luodairou/Desktop/finlab_crypto_course/history"
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

        # Remove the existing history.zip file if it exists
        zip_filename = "history.zip"
        existing_zip_files = service.files().list(
            q=f"name='{zip_filename}' and 'root' in parents",
            fields="files(id)"
        ).execute()

        for file in existing_zip_files.get('files', []):
            try:
                service.files().delete(fileId=file['id']).execute()
                print("Deleted existing history.zip file:", file['id'])
            except HttpError as error:
                print(f"An error occurred while deleting: {error}")

        # Create a new zip file of the history folder
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for root, _, files in os.walk(folder_path):
                # Exclude .ipynb_checkpoint folder
                if not root.endswith(".ipynb_checkpoint"):
                    for file in files:
                        if file.lower().endswith('.csv'):
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, os.path.relpath(
                                file_path, folder_path))

        print("History folder zipped successfully.")

        # Upload the history.zip file
        media = MediaFileUpload(
            zip_filename, mimetype='application/zip', resumable=True)
        file_metadata = {
            'name': zip_filename,
            'parents': []  # No parent specified, uploading to root folder
        }

        try:
            create_request = service.files().create(
                body=file_metadata,
                media_body=media
            )
            response = None
            while response is None:
                status, response = create_request.next_chunk()
                if status:
                    print("Uploaded %d%%." % int(status.progress() * 100))
            print("Zip File uploaded:", zip_filename)

        except HttpError as error:
            print(f'An error occurred: {error}')

        # Upload the files
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith('.csv'):
                file_path = os.path.join(folder_path, file_name)
                mime_type = 'application/octet-stream'
                # Exclude .ipynb_checkpoint folder
                if not file_path.endswith(".ipynb_checkpoint"):
                    file_metadata = {
                        'name': file_name,
                        # Upload .csv files to the history folder
                        'parents': [folder_id]
                    }

                    # Remove existing CSV files with the same name
                    existing_files = service.files().list(
                        q=f"name='{file_name}' and '{folder_id}' in parents",
                        fields="files(id)"
                    ).execute()
                    for existing_file in existing_files.get('files', []):
                        try:
                            service.files().delete(
                                fileId=existing_file['id']).execute()
                            print("Deleted existing CSV file:",
                                  existing_file['id'])
                        except HttpError as error:
                            print(f"An error occurred while deleting: {error}")

                    media = MediaFileUpload(
                        file_path, mimetype=mime_type, resumable=True)

                    try:
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
                        print("File uploaded:", file_name)

                    except HttpError as error:
                        print(f'An error occurred: {error}')
        print("All CSV files Uploaded!")

    except HttpError as error:
        print(f'An error occurred2: {error}')

    print("All Uploading is done!")


if __name__ == '__main__':
    main()
