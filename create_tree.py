"""Create a yaml to store the tree structure for the given roots from the authed drive.

Sharing permissions are perserved.
"""

from setup_drive_api import (
    get_service,
    SCOPES,
    get_file_contents,
    get_folder,
    FIELDS,
    QUERY_ADDENDUM,
)
import yaml

ROOTS_FILE = "roots.txt"
TREE_FILE = "tree.yaml"


def split_path(path):
    """Split a path into a list of subfolders."""
    path = path.replace("\\", "/")
    folders = path.split("/")
    return folders


def get_root_folder(service, root_name):
    """Get folder object for the root folder."""

    # Go down path to obtain the final parent_id
    parent_id = "root"
    for folder_name in split_path(root_name):
        folder = get_folder(service, folder_name, parent_id)
        parent_id = folder["id"]
    return folder


def get_sub_folders(service, parent_id):
    """Collate all subfolders to parent folder."""

    def get_items(page_token, parent_id):
        """Get items from service for given page."""
        return (
            service.files()
            .list(
                pageToken=page_token,
                fields=FIELDS,
                q=f"'{parent_id}' in parents and {QUERY_ADDENDUM}",
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )

    folders = []

    page_token = None
    has_results = True
    # Iterate over every page and collate folders
    while has_results:
        # Request folders
        results = get_items(page_token, parent_id)
        folders += results["files"]

        # Check for further results
        has_results = "nextPageToken" in results
        if has_results:
            page_token = results["nextPageToken"]

    return folders


def crop_permission(permission):
    """Crop the permission dict to the relevant fields for storing."""
    # Only need email now, Can easily add more fields if needed later
    email = permission["emailAddress"]
    return {"emailAddress": email}


def add_folder_dict_to_tree(folder, tree, parent_permissions=[]):
    """Create dict from folder and add to the tree."""

    # Only want relevant fields from permissions for yaml
    permissions = []
    for permission in folder["permissions"]:
        if "deleted" in permission and permission["deleted"]:
            continue

        permission_cropped = crop_permission(permission)
        if permission_cropped not in parent_permissions:
            permissions.append(permission_cropped)
    tree.append({"name": folder["name"], "permissions": permissions, "sub_folders": []})


def construct_tree(service, full_root_name, tree=[]):
    """Construct the folder tree from the given list of folders.

    :param tree: A list of subtrees which is altered in-place
    """

    def construct_tree_rec(service, tree, parent_id, parent_permissions):
        """Recusively construct the tree."""

        folders = get_sub_folders(service, parent_id)

        for folder in folders:
            folder_id = folder["id"]
            add_folder_dict_to_tree(folder, tree, parent_permissions)

            combined_permissions = []
            cropped_permissions = list(map(crop_permission, folder["permissions"]))
            for permission in cropped_permissions + parent_permissions:
                if permission not in combined_permissions:
                    combined_permissions.append(permission)

            construct_tree_rec(
                service, tree[-1]["sub_folders"], folder_id, combined_permissions
            )

    root_folder = get_root_folder(service, full_root_name)
    root_id = root_folder["id"]

    add_folder_dict_to_tree(root_folder, tree)
    root_permissions = list(map(crop_permission, root_folder["permissions"]))

    construct_tree_rec(service, tree[-1]["sub_folders"], root_id, root_permissions)


def get_sub_tree(path, tree):
    """Return the sub tree for the given path."""

    def find_folder(folder_name, tree):
        """Find the folder in the tree."""
        for folder in tree:
            if folder["name"] == folder_name:
                return folder
        return None

    for folder_name in split_path(path)[:-1]:
        # Last folder in path is a root and is added later when pulling from drive
        found_folder = find_folder(folder_name, tree)
        if isinstance(found_folder, type(None)):
            folder = {"name": folder_name, "permissions": []}
            add_folder_dict_to_tree(folder, tree)
            found_folder = tree[-1]
        tree = found_folder["sub_folders"]
    return tree


def main():
    """Run the program."""
    # Get drive service
    service = get_service(SCOPES)

    tree = []
    # Construct tree for each root
    for root in get_file_contents(ROOTS_FILE):
        print("Constructing " + root + " folder tree from drive ...")
        # Obtain subfolders in root
        sub_tree = get_sub_tree(root, tree)
        construct_tree(service, root, sub_tree)
    with open(TREE_FILE, "w") as f:
        yaml.dump(tree, f)


if __name__ == "__main__":
    main()
