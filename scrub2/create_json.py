"""Create a json to store tree structure and sharing permissions for the given roots."""

from setup_drive_api import get_service

from anytree import Node, RenderTree

SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]
FOLDER_TYPE = "application/vnd.google-apps.folder"
QUERY_ADDENDUM = f"mimeType = '{FOLDER_TYPE}' and not trashed"
FIELDS = "nextPageToken, files(id, name, permissions, kind, mimeType, parents, trashed)"


def get_root_id(service, root_name):
    """Get the ID for the root folder."""

    def get_folder_id(service, folder_name, parent_id):
        """Get the ID of any given folder."""
        results = (
            service.files()
            .list(
                pageToken=None,
                fields=FIELDS,
                q=f"'{parent_id}' in parents and name = '{folder_name}' \
                    and {QUERY_ADDENDUM}",
                corpora="allDrives",
                includeTeamDriveItems=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        if not results["files"]:
            raise FileNotFoundError(folder_name)
        return results["files"][0]["id"]

    # Get folders from path
    root_name = root_name.replace("\\", "/")
    folders = root_name.split("/")

    # Go down path to obtain the final parent_id
    parent_id = "root"
    for folder in folders:
        parent_id = get_folder_id(service, folder, parent_id)
    return parent_id


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
                includeTeamDriveItems=True,
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


def construct_tree(service, root_name):
    """Construct the folder tree from the given list of folders.

    :param folders: List of folders obtained from get_folders
    """

    def construct_tree_rec(service, nodes, folder_dict):
        """Recusively construct the tree."""

        parent_node = nodes[-1]
        parent_id = parent_node.name

        folders = get_sub_folders(service, parent_id)

        for folder in folders:
            folder_id = folder["id"]
            nodes.append(Node(folder_id, parent=parent_node))
            folder_dict[folder_id] = folder

            construct_tree_rec(service, nodes, folder_dict)

        return nodes, folder_dict

    root_id = get_root_id(service, root_name)

    nodes = [Node(root_id)]
    return construct_tree_rec(service, nodes, {root_id: root_name})


def get_root_names():
    """Get a list of root names from the roots.txt file."""

    # TODO: Test root.txt = "/" for using actual drive root as root

    def is_not_comment(line):
        """Check if the given line is a comment."""
        return not line.startswith("#") and line

    with open("roots.txt") as f:
        return list(filter(is_not_comment, f.read().split("\n")))


def main():
    # Get drive service
    service = get_service(SCOPES)

    # Construct tree for each root
    for root in get_root_names():
        # Obtain subfolders in root
        node_tree, folder_dict = construct_tree(service, root)

        # Render Tree
        tree = str(RenderTree(node_tree[0]))
        for folder in folder_dict:
            folder_obj = folder_dict[folder]
            if isinstance(folder_obj, type("")):
                folder_name = folder_obj
            else:
                folder_name = folder_obj["name"]
            tree = tree.replace(folder, folder_name)
        print(tree)
        # TODO: Create JSON

if __name__ == "__main__":
    main()
