import SetupAPI as GAPI
from googleapiclient import errors as googleErrors


def createFolder(name):
    file = GAPI.driveService.files().create(body={
        'name': name, 'mimeType': 'application/vnd.google-apps.folder'},
        fields='id').execute()


def delete(id):
    GAPI.driveService.files().delete(id).execute()


def listAllFiles():
    results = GAPI.driveService.files().list(
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print('{0} ({1})'.format(item['name'], item['id']))


def main():
    listAllFiles()


if __name__ == "__main__":
    main()
