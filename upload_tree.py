"""Load a tree with sharing permissions from a yaml into the drive."""

from setup_drive_api import get_service, SCOPES
import yaml

FOLDER_TYPE = "application/vnd.google-apps.folder"
TREE_FILE = "tree.yaml"


def get_tree():
    """Load the tree from the yaml file."""
    with open(TREE_FILE) as f:
        try:
            return yaml.load(f, Loader=yaml.SafeLoader)
        except FileNotFoundError as e:
            print(
                "tree.yaml should be in the same dir as this file. \
                Run create_tree.py to create a tree.yaml"
            )
            raise e


def add_folder(service, folder, parent_id=None):
    """Recursively upload all folders."""
    # Upload folder
    file_metadata = {"name": folder["name"], "mimeType": FOLDER_TYPE}
    if not isinstance(parent_id, type(None)):
        file_metadata["parents"] = [parent_id]
    uploaded_folder = service.files().create(body=file_metadata, fields="id").execute()
    uploaded_folder_id = uploaded_folder["id"]

    # Set permissions
    for permission in folder["permissions"]:
        email = permission["emailAddress"]
        permission_role = permission["role"]
        body = {"role": permission_role, "emailAddress": email, "type": "user"}
        # Notification required to be sent for transfer of ownership
        transferOwner = permission_role == "owner"

        service.permissions().create(
            fileId=uploaded_folder_id,
            supportsAllDrives=True,
            transferOwnership=transferOwner,
            sendNotificationEmail=transferOwner,
            body=body,
        ).execute()

    # Recurse to upload sub_folders
    for sub_folder in folder["sub_folders"]:
        add_folder(service, sub_folder, uploaded_folder["id"])


def main():
    """Run the program."""
    service = get_service(SCOPES)
    tree = get_tree()
    for folder in tree:
        add_folder(service, folder)


if __name__ == "__main__":
    main()

# TODO: Add progress bar
# TODO: Document better
# TODO: Implement inherited permissions
