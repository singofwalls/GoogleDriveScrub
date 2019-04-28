"""Load a tree from a yaml into the drive."""

from setup_drive_api import get_service, SCOPES
from permissions import get_permission_id
import yaml
from apiclient import errors

FOLDER_TYPE = "application/vnd.google-apps.folder"


def get_tree():
    """Load the tree from the yaml file."""
    with open("tree.yaml") as f:
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
    file_metadata = {"name": folder["name"], "mimeType": FOLDER_TYPE}
    if not isinstance(parent_id, type(None)):
        file_metadata["parents"] = [parent_id]
    uploaded_folder = service.files().create(body=file_metadata, fields="id").execute()
    uploaded_folder_id = uploaded_folder["id"]
    folder_name = folder["name"]
    for permission in folder["permissions"]:
        email = permission["emailAddress"]
        permission_role = permission["role"]
        permission_id = get_permission_id(email)
        try:
            service.permissions().update(
                fileId=uploaded_folder_id,
                permissionId=permission_id,
                supportsAllDrives=True,
                body={"role": permission_role},
            ).execute()
            print(
                "Added permission",
                permission_role,
                "for email",
                email,
                "to folder",
                folder_name,
            )
        except errors.HttpError as e:
            print(
                "Could not add permission",
                permission_role,
                "for email",
                email,
                "to folder",
                folder_name,
            )
    for sub_folder in folder["sub_folders"]:
        add_folder(service, sub_folder, uploaded_folder["id"])


if __name__ == "__main__":
    service = get_service(SCOPES)
    tree = get_tree()
    for folder in tree:
        add_folder(service, folder)
