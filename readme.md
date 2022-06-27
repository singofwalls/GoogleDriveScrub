## Google Drive Scrub

Save and upload drive tree structures which maintain permissions.  
There are two scripts in this repo, [create_tree.py](create_tree.py) and [upload_tree.py](upload_tree.py), which must be ran by the user.  
[create_tree.py](create_tree.py) scans the Google Drive of the authenticated user and builds a tree structure which is stored in a YAML file.  
[upload_tree.py](upload_tree.py) traverses the YAML file and uploads each folder in the tree to the authenticated user's Google Drive.
# Setup
In order to utilize the Google Drive API, there must be a `credentials.json` file in the directory beside all the other files. This file contains the `client_id` and `client_secret` tokens and must be obtained from [The Google Developer Console](https://console.developers.google.com/apis/dashboard). Create a project and enable the Google Drive API and create and download credentials. Rename the JSON `credentials.json` and place it in the Google Drive Scrub directory.     

Python 3.6 or above required. Get it [here](https://www.python.org/downloads/).  
Install required dependencies with pip:  

`pip install -r requirements.txt`

Running either [create_tree.py](create_tree.py) or [upload_tree.py](upload_tree.py) will prompt the user to sign in and approve the app for authentication. Additionally, running [setup_drive_api.py](setup_drive_api.py) manually will prompt the user to reauthenticate the app.

# Usage
To create a tree YAML file from your Google Drive,  
1. Specify the root folders to scan in the [roots.txt](roots.txt) file
2. Run [create_tree.py](create_tree.py) and wait for it to complete

To upload a tree YAML file to your Google Drive,  
1. Edit [tree.yaml](tree.yaml) however you see fit for your intended use (Place-holder emails can be added which will be automatically swapped with emails from [placeholder_emails.yaml](placeholder_emails.yaml) upon upload)
2. Specify the owner's email in [owner_email.txt](owner_email.txt) (Any folders with this email listed as a permission will have its ownership transferred to this email)
3. Run [upload_tree.py](upload_tree.py) and wait for it to complete

# Extra
- Folders in the [tree.yaml](tree.yaml) which do not have any listed permissions will not be uploaded if a folder of the same name with the same parent already exists. The existing folder will be used instead. 
- Google Drive **does** allow folders of the same name to exist in the same directory. When finding folders with which to create the [tree.yaml](tree.yaml), [create_tree.py](create_tree.py) will take the first file it finds with the correct parent and correct name. Best to ensure only one folder of a given name exists in a given directory.
- While share notifications are disabled, transfer-of-ownership emails cannot be. It is reccomended the intended owner of the tree be the one to upload it lest they receive a separate transfer-of-ownership email for every folder in the tree.

# Contact
Reece Mathews  
Email: reece@pericarpal.com  
