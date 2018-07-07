"""
Shows basic usage of the Drive v3 API.

Creates a Drive v3 API service and prints the names and ids of the last 10 files
the user has access to.
"""

# TODO: recreate folders with permissions obtained from given dict
# TODO:     if not in dict, do not add permission

from __future__ import print_function
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

REVERSE_CONSTRUCTION = False  # Probably never necessary, wouldn't reccomend changing
ROOT_FOLDER_NAME = input("Enter the root folder name: ")


def get_folder_at_path(tree, path):
    _folders = tree["children"]
    _last_folder = None
    for part in path:
        if len(_folders) > part:
            _last_folder = _folders[part]
        else:
            return None
        _folders = _folders[part]["children"]
    return _last_folder


def insert_in_tree(folder_to_insert_object, tree, last_folder):
    folder_to_insert = folder_to_insert_object["folder"]
    parent_id = folder_to_insert["parents"][0]
    path = [0]
    while True:
        folder_at_path = get_folder_at_path(tree, path)
        if isinstance(folder_at_path, type(None)):
            # No folder at path
            if len(path) == 1:  # back at root, no folder found
                return False
            print("reached end of branch, moving back")
            path.pop()
            path[-1] += 1
        elif folder_at_path["folder"]["id"] == parent_id:
            print("parent found:", folder_at_path["folder"]["name"])
            folder_at_path["children"].append(folder_to_insert_object)
            break
        else:
            path.append(0)
        print("                                         ", path)
    return True


def construct_tree(folders):
    tree = {"children": []}
    remaining_folders = folders[:]
    if REVERSE_CONSTRUCTION:
        remaining_folders = folders[::-1]
    last_folder = None
    while len(remaining_folders) > 0:
        folder_to_insert = remaining_folders.pop()
        print("Handling", folder_to_insert["name"])
        folder_to_insert_object = {"folder": folder_to_insert, "children": []}
        if "parents" not in folder_to_insert or len(
                folder_to_insert["parents"]) == 0 or \
                folder_to_insert["parents"][0] == root_id:
            print("Added to root")

            # Only add to root if folder is the one specified, otherwise: skip
            if folder_to_insert["name"] == ROOT_FOLDER_NAME:
                tree["children"].append(folder_to_insert_object)
                last_folder = None
        else:
            if len(tree["children"]) == 0:
                could_not_insert = True
            else:
                could_not_insert = not insert_in_tree(folder_to_insert_object,
                                                      tree, last_folder)
            if could_not_insert:
                # Readd folder to bottom of queue
                if last_folder == folder_to_insert:
                    print("Remaining files have no parents")
                    break
                print("No parent found, pushed to bottom of stack")
                remaining_folders.insert(0, folder_to_insert)
                if isinstance(last_folder, type(None)):
                    last_folder = folder_to_insert
            else:
                last_folder = None
    return tree


def reconstruct_tree(tree):
    path = [0]
    done = False
    parent_id = None
    while not done:
        folder_at_path = get_folder_at_path(tree, path)
        if isinstance(folder_at_path, type(None)):
            if path[-1] == 0:
                while isinstance(get_folder_at_path(tree, path), type(None)):
                    if len(path) == 1:
                        done = True
                        break
                    path.pop()
                if done:
                    break
                path[-1] += 1
                path.append(0)
            else:
                path[-1] = 0
                path.append(0)
        else:
            if len(path) > 1:
                parent_id = get_folder_at_path(tree, path[:-1])["new_id"]
            file_metadata = {
                'name': folder_at_path["folder"]["name"],
                'mimeType': 'application/vnd.google-apps.folder',
            }
            if not isinstance(parent_id, type(None)):
                file_metadata['parents'] = [parent_id]
                parent_id = None
            file = service.files().create(body=file_metadata,
                                          fields='id').execute()
            print(path, "Adding", file_metadata["name"])
            folder_at_path["new_id"] = file["id"]
            path[-1] += 1


# Setup the Drive v3 API
SCOPES = 'https://www.googleapis.com/auth/drive'
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('drive', 'v3', http=creds.authorize(Http()))

# Call the Drive v3 API
attributes = set()
token = None
folders = []
while True:
    print("Checking page token for folders:", token)
    results = service.files().list(pageToken=token,
                                   fields="nextPageToken, files(id, name, "
                                          "permissions, mimeType, kind, "
                                          "parents, trashed)").execute()
    items = results["files"]
    for item in items:
        if "folder" in item["mimeType"]:
            if not item["trashed"]:
                folders.append(item)
                if item["name"] == ROOT_FOLDER_NAME:
                    if "parents" in item and len(item["parents"]) > 0:
                        root_id = item["parents"][0]
    if "nextPageToken" not in results:
        break
    token = results["nextPageToken"]

print("Found all folders:", folders)

folder_tree = construct_tree(folders)
print(folder_tree)
if len(folder_tree["children"]) == 0:
    raise SystemExit("No Folders Found")

# TODO: delete all root folders
root_folder = folder_tree["children"][0]["folder"]
if input("Are you sure you want to DELETE: " + root_folder[
    "name"] + " and all its contained content? ").lower().startswith("y"):
    result = service.files().delete(fileId=root_folder["id"]).execute()
else:
    print("Cancelling")
    raise SystemExit(0)

if not input("Are you sure you want to RECREATE: " + root_folder[
    "name"] + " and all its contained folders? ").lower().startswith("y"):
    print("Cancelling")
    raise SystemExit(0)

reconstruct_tree(folder_tree)
