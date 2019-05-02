"""Load a tree with sharing permissions from a yaml into the drive."""

from googleapiclient.errors import HttpError
from setup_drive_api import (
    get_service,
    SCOPES,
    get_file_contents,
    get_folder,
    handle_error,
    get_error_details,
)
import yaml
from tqdm import tqdm

FOLDER_TYPE = "application/vnd.google-apps.folder"
TREE_FILE = "tree.yaml"
OWNER_FILE = "owner_email.txt"

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


def add_folder(service, folder, parent_id=None, owner=None):
    """Recursively upload all folders."""

    def upload_folder(service, folder, parent_id):
        """Upload a given folder and return the upload's id."""
        try:
            if parent_id == None:
                existing_parent = "root"
            else:
                existing_parent = parent_id
            existing_folder = get_folder(service, folder["name"], existing_parent)
        except FileNotFoundError:
            existing_folder = None

        if not isinstance(existing_folder, type(None)) and not folder["permissions"]:
            # Use existing folder if no permissions to be uploaded
            uploaded_folder_id = existing_folder["id"]
        else:
            # Upload new folder
            file_metadata = {"name": folder["name"], "mimeType": FOLDER_TYPE}
            if not isinstance(parent_id, type(None)):
                file_metadata["parents"] = [parent_id]
            uploaded_folder = (
                service.files().create(body=file_metadata, fields="id").execute()
            )
            uploaded_folder_id = uploaded_folder["id"]

        update_progress()
        return uploaded_folder_id

    def set_permissions(service, folder, uploaded_folder_id, owner=None):
        """Copy permissions from a given folder to the uploaded folder from id."""
        # Set permissions
        for permission in folder["permissions"]:
            email = permission["emailAddress"]

            transferOwner = email == owner
            if transferOwner:
                permission_role = "owner"
            else:
                permission_role = "writer"

            body = {"role": permission_role, "emailAddress": email, "type": "user"}
            # Notification required to be sent for transfer of ownership

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

                except HttpError as e:
                    handle_error(e, output)
    progress_bar.set_description(folder["name"])
    uploaded_folder_id = upload_folder(service, folder, parent_id)
    set_permissions(service, folder, uploaded_folder_id, owner=owner)

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

    total_operations = calculate_operations(tree) + 1
    update_progress()

    owner_email = get_file_contents(OWNER_FILE)[0]

    output("Uploading tree ...")
    for folder in tree:
        add_folder(service, folder, owner=owner_email)

    progress_bar.clear()
    print("Complete.")


if __name__ == "__main__":
    main()
