import gitlab
import os
import csv

# Set up GitLab connection using an access token (replace 'your_gitlab_url' with actual GitLab URL)
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
GITLAB_API_KEY = os.getenv("GITLAB_API_KEY", "your_api_key_here")

# Create a GitLab connection
gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_API_KEY)

# List to hold all the data for CSV export
group_data = []

# Fetch all root groups (groups without a parent) and recursively handle subgroups and projects
def get_root_groups_and_projects():
    try:
        # Get all groups the user has access to
        groups = gl.groups.list(all=True)

        for group in groups:
            if group.parent_id is None:
                print(f"... Fetching groups and projects for root group: {group.name}")
                # This is a root group, so start the recursive process
                get_subgroups_and_projects(group.id, group.name, None, None, None)

    except gitlab.exceptions.GitlabAuthenticationError:
        print("Authentication failed. Check your access token.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Recursively fetch subgroups and projects (with subgroup levels)
def get_subgroups_and_projects(group_id, root_group_name, subgroup1, subgroup2, subgroup3):
    try:
        # Fetch the group object by ID
        group = gl.groups.get(group_id)

        # Get all subgroups within the current group
        subgroups = group.subgroups.list(all=True)

        for subgroup in subgroups:
            if not subgroup1:
                # First level subgroup
                get_subgroups_and_projects(subgroup.id, root_group_name, subgroup.name, None, None)
            elif not subgroup2:
                # Second level subgroup
                get_subgroups_and_projects(subgroup.id, root_group_name, subgroup1, subgroup.name, None)
            elif not subgroup3:
                # Third level subgroup
                get_subgroups_and_projects(subgroup.id, root_group_name, subgroup1, subgroup2, subgroup.name)

        # Get all projects within the current group or subgroup
        projects = group.projects.list(all=True)
        for project in projects:
            # Append the root group, subgroup1, subgroup2, subgroup3, and project data to the list
            group_data.append({
                'Group': root_group_name,
                'Subgroup1': subgroup1 if subgroup1 else "None",
                'Subgroup2': subgroup2 if subgroup2 else "None",
                'Subgroup3': subgroup3 if subgroup3 else "None",
                'Project': project.name
            })

    except Exception as e:
        print(f"An error occurred while fetching subgroups/projects: {e}")

# Function to export the data to CSV
def export_to_csv(file_name="gitlab_groups_projects.csv"):
    try:
        # Define the CSV file headers
        headers = ['Group', 'Subgroup1', 'Subgroup2', 'Subgroup3', 'Project']

        # Sort group_data by 'Group', 'Subgroup1', 'Subgroup2', 'Subgroup3', and 'Project'
        sorted_data = sorted(group_data, key=lambda x: (x['Group'], x['Subgroup1'], x['Subgroup2'], x['Subgroup3'], x['Project']))

        # Write the collected data to a CSV file
        with open(file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(sorted_data)

        print(f"Data successfully exported to {file_name}")

    except Exception as e:
        print(f"An error occurred while writing to CSV: {e}")

if __name__ == "__main__":
    print(f"Exporting groups and projects from {gl.url} to CSV...")
    get_root_groups_and_projects()  # Fetch all root groups, subgroups, and projects
    export_to_csv()  # Export the collected data to a CSV file
