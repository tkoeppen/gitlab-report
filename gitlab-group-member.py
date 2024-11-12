import csv
import gitlab
import os
import requests

# this script read groups and users from 2 csv files and add users with their configured role to the defined groups

# Set up GitLab connection using an access token (replace 'your_gitlab_url' with actual GitLab URL)
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
GITLAB_API_KEY = os.getenv("GITLAB_API_KEY", "your_api_key_here")
GITLAB_HTTP_PROXY = os.getenv("GITLAB_HTTP_PROXY", None)

# Create a requests session and set the proxy
session = requests.Session()
session.proxies = {
    'https': GITLAB_HTTP_PROXY,
}

# Create a GitLab connection
gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_API_KEY, session=session)

# Function to read CSV files
def read_csv(file_name):
    with open(file_name, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

# Read users and groups from CSV files
users = read_csv('users.csv')
#print(users)
groups = read_csv('groups.csv')
#print(groups)

# Function to get group ID by name
def get_group_id_by_name(group_name):
    try:
        group = gl.groups.list(search=group_name)
        #print(group)
        for grp in group:
            if grp.name == group_name:
                return grp.id
        print(f"Group {group_name} not found in GitLab")
        return None
    except Exception as e:
        print(f"An error occurred while fetching group ID for {group_name}: {e}")
        return None

# Function to add or remove users from groups
def manage_users_in_groups(users, groups):
    for group in groups:
        group_name = group['group_name']
        group_id = get_group_id_by_name(group_name)
        if group_id:
            for user in users:
                email = user['email']
                try:
                    # Find the user by email
                    gitlab_user = gl.users.list(search=email)
                    if gitlab_user:
                        user_id = gitlab_user[0].id
                        group_obj = gl.groups.get(group_id)
                        if user['status'].lower() == 'active':
                            access_level = gitlab.const.AccessLevel.DEVELOPER if user['role'].lower() == 'developer' else gitlab.const.AccessLevel.MAINTAINER
                            try:
                                # Add the user to the group
                                group_obj.members.create({'user_id': user_id, 'access_level': access_level})
                                print(f"Added {email} to group {group_name} as {user['role']}")
                            except gitlab.exceptions.GitlabCreateError as e:
                                if e.response_code == 409:
                                    # Member already exists, update access level if necessary
                                    member = group_obj.members.get(user_id)
                                    if member.access_level != access_level:
                                        member.access_level = access_level
                                        member.save()
                                        print(f"Updated {email}'s access level to {user['role']} in group {group_name} ({group_id})")
                                    else:
                                        print(f"{email} already exists in group {group_name} ({group_id}) with the same access level")
                                else:
                                    raise e
                        else:
                            # Remove the user from the group if inactive
                            try:
                                member = group_obj.members.get(user_id)
                                member.delete()
                                print(f"Removed {email} from group {group_name} due to inactive status")
                            except gitlab.exceptions.GitlabGetError:
                                print(f"{email} is not a member of group {group_name}")
                    else:
                        print(f"User {email} not found in GitLab")
                except Exception as e:
                    print(f"An error occurred while managing {email} in group {group_name}: {e}")

# Add users to groups
manage_users_in_groups(users, groups)
