"""Create a yaml to store the tree structure for the given roots from the authed drive.

Sharing permissions are perserved.
"""

from setup_drive_api import get_service, SCOPES
import yaml

FOLDER_TYPE = "application/vnd.google-apps.folder"
QUERY_ADDENDUM = f"mimeType = '{FOLDER_TYPE}' and not trashed"
FIELDS = "nextPageToken, files(id, name, permissions(type, id, emailAddress, role, \
    deleted), kind, mimeType, parents, trashed)"
ROOTS_FILE = "roots.txt"
TREE_FILE = "tree.yaml"


def get_root_folder(service, root_name):
    """Get folder object for the root folder."""

    def get_folder(service, folder_name, parent_id):
        """Get the folder object based on name and parent."""
        parent_string = ""
        if parent_id != "root":
            parent_string = f" and '{parent_id}' in parents"
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
        if not results["files"]:
            raise FileNotFoundError(folder_name)
        return results["files"][0]

    # Get folders from path
    root_name = root_name.replace("\\", "/")
    folders = root_name.split("/")

    # Go down path to obtain the final parent_id
    parent_id = "root"
    for folder_name in folders:
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


def construct_tree(service, root_name, tree=[]):
    """Construct the folder tree from the given list of folders.

    :param tree: A list of subtrees which is altered in-place
    """

    def crop_permission(permission):
        """Crop the permission dict to the relevant fields for storing."""
        email = permission["emailAddress"]
        role = permission["role"]
        return {"role": role, "emailAddress": email}

    def add_folder_dict(service, folder, tree, parent_permissions):
        """Create dict from folder and add to the tree."""

        # Only want relevant fields from permissions for yaml
        permissions = []
        for permission in folder["permissions"]:
            if "deleted" in permission and permission["deleted"]:
                continue

            permission_cropped = crop_permission(permission)
            if permission_cropped not in parent_permissions:
                permissions.append(permission_cropped)
        tree.append(
            {"name": folder["name"], "permissions": permissions, "sub_folders": []}
        )

    def construct_tree_rec(service, tree, parent_id, parent_permissions):
        """Recusively construct the tree."""

        folders = get_sub_folders(service, parent_id)

        for folder in folders:
            folder_id = folder["id"]
            add_folder_dict(service, folder, tree, parent_permissions)

            combined_permissions = []
            cropped_permissions = list(map(crop_permission, folder["permissions"]))
            for permission in cropped_permissions + parent_permissions:
                if permission not in combined_permissions:
                    combined_permissions.append(permission)

            construct_tree_rec(
                service, tree[-1]["sub_folders"], folder_id, combined_permissions
            )

    root_folder = get_root_folder(service, root_name)
    root_id = root_folder["id"]
    root_name = root_folder["name"]

    add_folder_dict(service, root_folder, tree, [])
    root_permissions = list(map(crop_permission, root_folder["permissions"]))

    construct_tree_rec(service, tree[-1]["sub_folders"], root_id, root_permissions)


def get_root_names():
    """Get a list of root names from the roots.txt file."""

    # TODO: Test root.txt = "/" for using actual drive root as root
    # TODO: Test multiple roots

    def is_not_comment(line):
        """Check if the given line is a comment."""
        return not line.startswith("#") and line

    with open(ROOTS_FILE) as f:
        return list(filter(is_not_comment, f.read().split("\n")))


def main():
    """Run the program."""
    # Get drive service
    service = get_service(SCOPES)

    tree = []
    print("Constructing tree from roots on drive ...")
    # Construct tree for each root
    for root in get_root_names():
        # Obtain subfolders in root
        construct_tree(service, root, tree)
    with open(TREE_FILE, "w") as f:
        yaml.dump(tree, f)


if __name__ == "__main__":
    main()
