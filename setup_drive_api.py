"""Setup the drive api."""

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import json
import time

# Delete token.pickle if scopes changed
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]
TOKEN_FILE = "token.pickle"
FOLDER_TYPE = "application/vnd.google-apps.folder"
QUERY_ADDENDUM = f"mimeType = '{FOLDER_TYPE}' and not trashed"
FIELDS = "nextPageToken, files(id, name, permissions(type, id, emailAddress, role, \
    deleted), kind, mimeType, parents, trashed)"
RATE_ERRORS = ["userRateLimitExceeded", "rateLimitExceeded", "backendError"]


# Exponential Backoff globals
sleep_time = 1


def get_error_details(error):
    """Get the reason for an HTTP error."""
    error = json.loads(error.content)["error"]["errors"][0]
    return error["reason"], error["message"]


def handle_error(error, output_method=print):
    """Handle HTTP errors."""
    global sleep_time

    reason, message = get_error_details(error)
    if reason in RATE_ERRORS:
        # Rate limit exceeded, perform exponential backoff
        output_method(
            "Could not perform drive request. Waiting " + str(sleep_time) + " seconds."
        )
        output_method("Reason: " + reason + ": " + message)
        time.sleep(sleep_time)
        sleep_time *= 2
    else:
        raise error


def sanitize_folder_name(folder_name):
    """Sanitize the name of a folder for upload."""

    return folder_name.replace("'", "\\'")


def get_folder(service, folder_name, parent_id):
    """Get the folder object based on name and parent."""
    parent_string = ""
    if parent_id != "root":
        parent_string = f" and '{parent_id}' in parents"

    folder_name = sanitize_folder_name(folder_name)

    uploaded = False
    while not uploaded:
        try:
            results = (
                service.files()
                .list(
                    pageToken=None,
                    fields=FIELDS,
                    q=f"name = '{folder_name}' and {QUERY_ADDENDUM}" + parent_string,
                    corpora="allDrives",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )
            uploaded = True
        except HttpError as e:
            try:
                handle_error(e)
            except HttpError as e:
                reason, message = get_error_details(e)
                if reason == "notFound":
                    raise FileNotFoundError(folder_name)
                else:
                    print("Error " + reason + ": " + message)
                    raise e

    if not results["files"]:
        raise FileNotFoundError(folder_name)
    return results["files"][0]


def get_file_contents(file):
    """Get the contents of a file ignoring comments and new-line delimited."""

    def is_not_comment(line):
        """Check if the given line is a comment."""
        return not line.startswith("#") and line

    with open(file) as f:
        return list(filter(is_not_comment, f.read().split("\n")))


def get_service(scopes):
    """Set-up the drive api and return the obtained service object."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    service = build("drive", "v3", credentials=creds)
    return service
