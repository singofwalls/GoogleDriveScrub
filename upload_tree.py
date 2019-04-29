"""Load a tree with sharing permissions from a yaml into the drive."""

from setup_drive_api import get_service, SCOPES, HttpError
import yaml
from tqdm import tqdm
import time

FOLDER_TYPE = "application/vnd.google-apps.folder"
TREE_FILE = "tree.yaml"

# Progress globals
total_operations = 0
progress_bar = None


def get_tree():
    """Load the tree from the yaml file."""
    with open(TREE_FILE) as f:
        try:
            return yaml.load(f, Loader=yaml.SafeLoader)
        except FileNotFoundError as e:
            output(
                "tree.yaml should be in the same dir as this file. \
                Run create_tree.py to create a tree.yaml"
            )
            raise e


def add_folder(service, folder, parent_id=None):
    """Recursively upload all folders."""

    def upload_folder(service, folder, parent_id):
        """Upload a given folder and return the upload's id."""
        file_metadata = {"name": folder["name"], "mimeType": FOLDER_TYPE}
        if not isinstance(parent_id, type(None)):
            file_metadata["parents"] = [parent_id]
        uploaded_folder = (
            service.files().create(body=file_metadata, fields="id").execute()
        )
        update_progress()
        uploaded_folder_id = uploaded_folder["id"]
        return uploaded_folder_id

    def set_permissions(service, folder, uploaded_folder_id):
        """Copy permissions from a given folder to the uploaded folder from id."""
        sleep_time = 1

        # Set permissions
        for permission in folder["permissions"]:
            email = permission["emailAddress"]
            permission_role = permission["role"]
            body = {"role": permission_role, "emailAddress": email, "type": "user"}
            # Notification required to be sent for transfer of ownership
            transferOwner = permission_role == "owner"

            uploaded = False
            while not uploaded:
                try:
                    service.permissions().create(
                        fileId=uploaded_folder_id,
                        supportsAllDrives=True,
                        transferOwnership=transferOwner,
                        sendNotificationEmail=transferOwner,
                        body=body,
                    ).execute()
                    update_progress()
                    uploaded = True
                except HttpError:
                    # File not done uploading, perform exponential backoff
                    output(
                        folder["name"]
                        + " not ready to set permissions. Waiting "
                        + sleep_time
                        + " seconds."
                    )
                    time.sleep(sleep_time)
                    sleep_time *= 2

    uploaded_folder_id = upload_folder(service, folder, parent_id)
    set_permissions(service, folder, uploaded_folder_id)

    # Recurse to upload sub_folders
    for sub_folder in folder["sub_folders"]:
        add_folder(service, sub_folder, uploaded_folder_id)


def calculate_operations(tree):
    """Calculate the total number of upload operations necessary."""
    total = 0
    for folder in tree:
        total += len(folder["permissions"]) + 1
        total += calculate_operations(folder["sub_folders"])
    return total


def output(message):
    """Print to console while accounting for progess bar."""
    if isinstance(progress_bar, type(None)):
        print(message)
    else:
        progress_bar.write(message)


def update_progress():
    """Display the current progress."""
    global progress_bar
    if isinstance(progress_bar, type(None)):
        progress_bar = tqdm(total=total_operations)
    progress_bar.update(1)


def main():
    """Run the program."""
    global total_operations
    service = get_service(SCOPES)
    tree = get_tree()
    total_operations = calculate_operations(tree)
    for folder in tree:
        add_folder(service, folder)


if __name__ == "__main__":
    main()
