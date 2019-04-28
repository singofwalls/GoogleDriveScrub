"""Determine the permission ID for a user and add to permissionId list."""

from setup_drive_api import get_service, SCOPES
import yaml


def get_user(service):
    """Obtain the permission ID for the authenticated user."""
    return service.about().get(fields="user(permissionId, emailAddress)").execute()


def get_permissions():
    """Read the permissions file."""
    with open("permissions.yaml", "r") as f:
        permissions = yaml.load(f.read(), Loader=yaml.SafeLoader)
        if isinstance(permissions, type(None)):
            return {}
        return permissions


def update_permissions_file(service, email, permission_id):
    """Update the permissions yaml file with given user's id."""

    def set_permissions(permissions):
        """Write to the permissions file."""
        with open("permissions.yaml", "w") as f:
            yaml.dump(permissions, f)

    permissions = get_permissions()
    permissions[email] = permission_id
    set_permissions(permissions)


def get_permission_id(email):
    """Get a permission id from an email."""
    try:
        return get_permissions()[email]
    except KeyError as e:
        print(
            email
            + " not in permissions file. Run permissions.py while authed as "
            + email
        )
        raise e


if __name__ == "__main__":
    # Set permissions for currently authed user
    service = get_service(SCOPES)
    user = get_user(service)["user"]
    email = user["emailAddress"]
    permission_id = user["permissionId"]
    update_permissions_file(service, email, permission_id)
