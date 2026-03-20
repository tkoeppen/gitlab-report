import csv
import gitlab
import os
import requests
import subprocess
import tempfile
import shutil
import json
import argparse
from datetime import datetime

# this script exports all groups, subgroups, projects, and their members to a CSV file

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

# List to hold all the data for CSV export
group_data = []

# Flag to control LOC counting (set via command line argument)
COUNT_LOC = False

# Cache directory for cloned repositories
CACHE_DIR = os.path.join(os.getcwd(), ".gitlab-repo-cache")

# Function to count lines of code using cloc
def count_lines_of_code(project_url, project_name, project_id):
    """
    Clone or update a repository and count lines of code using cloc.
    Uses a cache directory to avoid re-cloning on subsequent runs.
    Returns a tuple: (total_loc, loc_by_language_str)
    """
    def get_timestamp():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Create cache directory if it doesn't exist
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            print(f"[{get_timestamp()}] Created cache directory: {CACHE_DIR}")

        # Create a safe directory name from project ID (unique identifier)
        safe_name = f"project_{project_id}"
        clone_path = os.path.join(CACHE_DIR, safe_name)

        # Prepare the git clone URL with authentication
        if project_url.startswith("https://"):
            auth_url = project_url.replace("https://", f"https://oauth2:{GITLAB_API_KEY}@")
        else:
            auth_url = project_url

        # Set up environment for git with proxy if needed
        env = os.environ.copy()
        if GITLAB_HTTP_PROXY:
            env['https_proxy'] = GITLAB_HTTP_PROXY
            env['http_proxy'] = GITLAB_HTTP_PROXY

        # Check if repository already exists
        if os.path.exists(clone_path) and os.path.isdir(os.path.join(clone_path, ".git")):
            # Repository exists, update it
            print(f"[{get_timestamp()}] Updating existing clone: {project_name} -> {clone_path}")

            # Git pull to update
            pull_result = subprocess.run(
                ["git", "-C", clone_path, "pull", "--quiet"],
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )

            if pull_result.returncode != 0:
                print(f"[{get_timestamp()}] Warning: Failed to update {project_name}, using existing version: {pull_result.stderr}")
                # Continue with existing version
        else:
            # Repository doesn't exist, clone it
            print(f"[{get_timestamp()}] Cloning new repository: {project_name} -> {clone_path}")

            # Remove directory if it exists but is not a valid git repo
            if os.path.exists(clone_path):
                shutil.rmtree(clone_path, ignore_errors=True)

            clone_result = subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", auth_url, clone_path],
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )

            if clone_result.returncode != 0:
                print(f"[{get_timestamp()}] Failed to clone {project_name}: {clone_result.stderr}")
                return 0, "Clone failed"

        # Run cloc with JSON output
        print(f"[{get_timestamp()}] Counting lines of code for: {project_name}")
        cloc_result = subprocess.run(
            ["cloc", "--json", "--quiet", clone_path],
            capture_output=True,
            text=True,
            timeout=300
        )

        if cloc_result.returncode != 0:
            print(f"[{get_timestamp()}] cloc failed for {project_name}")
            return 0, "cloc failed"

        # Parse cloc JSON output
        cloc_data = json.loads(cloc_result.stdout)

        # Extract total lines of code
        total_loc = cloc_data.get("SUM", {}).get("code", 0)

        # Build a language breakdown string (sorted by LOC)
        languages = []
        for lang, data in cloc_data.items():
            if lang not in ["header", "SUM"] and isinstance(data, dict):
                loc = data.get("code", 0)
                if loc > 0:
                    languages.append((lang, loc))

        # Sort by LOC descending
        languages.sort(key=lambda x: x[1], reverse=True)

        # Format as string
        if languages:
            lang_str = ", ".join([f"{lang} ({loc})" for lang, loc in languages[:5]])  # Top 5 languages
        else:
            lang_str = "None"

        print(f"[{get_timestamp()}] Completed: {project_name} - Total LOC: {total_loc}")
        return total_loc, lang_str

    except subprocess.TimeoutExpired:
        print(f"[{get_timestamp()}] Timeout while processing {project_name}")
        return 0, "Timeout"
    except Exception as e:
        print(f"[{get_timestamp()}] Error counting LOC for {project_name}: {e}")
        return 0, "Error"

# Fetch all root groups (groups without a parent) and recursively handle subgroups and projects
def get_root_groups_and_projects():
    try:
        # Get all groups the user has access to
        groups = gl.groups.list(all=True)

        for group in groups:
            if group.parent_id is None:
                print(f"... Fetching groups, projects and members for root group: {group.name}")
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
        projects = group.projects.list(all=True, statistics=True)
        for project in projects:
            # Append the root group, subgroup1, subgroup2, subgroup3, and project data to the list
            try:
                # Fetch the full project details to access members
                full_project = gl.projects.get(project.id, statistics=True)
                admins = [member.username for member in full_project.members_all.list(all=True) if member.access_level == gitlab.const.AccessLevel.OWNER]
                maintainers = [member.username for member in full_project.members_all.list(all=True) if member.access_level >= gitlab.const.AccessLevel.MAINTAINER]
                developers = [member.username for member in full_project.members_all.list(all=True) if member.access_level == gitlab.const.AccessLevel.DEVELOPER]
                members = [member.username for member in full_project.members_all.list(all=True)]

                # to debug API response
                #print(f"... project: {project}")
                #print(f"Members: project.name: {project.name}, project.id: {project.id}, members: {members}")

                # Fetch the project size
                project_size_bytes = full_project.statistics['storage_size']
                # convert bytes to MB, round to 1 decimal, and replace '.' with ',' to match European number format (for Excel)
                project_size_mb = f"{round(project_size_bytes / (1024 ** 2), 1):.1f}".replace('.', ',')

                # Fetch programming languages used in the project
                try:
                    languages = full_project.languages()
                    # Sort languages by usage (descending) and format as comma-separated list with percentages
                    if languages:
                        total_bytes = sum(languages.values())
                        languages_list = [f"{lang} ({round(bytes/total_bytes*100, 1)}%)" for lang, bytes in sorted(languages.items(), key=lambda x: x[1], reverse=True)]
                        languages_str = ', '.join(languages_list)
                    else:
                        languages_str = "None"
                except Exception as e:
                    print(f"Could not fetch languages for project {project.name}: {e}")
                    languages_str = "Unknown"

                # Count lines of code using cloc (if enabled)
                if COUNT_LOC:
                    total_loc, loc_breakdown = count_lines_of_code(full_project.http_url_to_repo, project.name, project.id)
                else:
                    total_loc, loc_breakdown = "N/A", "N/A"

                # Build data dictionary
                project_data = {
                    'Group': root_group_name,
                    'Subgroup1': subgroup1 if subgroup1 else "None",
                    'Subgroup2': subgroup2 if subgroup2 else "None",
                    'Subgroup3': subgroup3 if subgroup3 else "None",
                    'Project': project.name,
                    'Admins': ', '.join(admins),
                    'Maintainers': ', '.join(maintainers),
                    'Developers': ', '.join(developers),
                    'Members': ', '.join(members),
                    'Project Size (MB)': project_size_mb,
                    'Languages': languages_str
                }

                # Add LOC data if counting is enabled
                if COUNT_LOC:
                    project_data['Lines of Code'] = total_loc
                    project_data['LOC Breakdown'] = loc_breakdown

                group_data.append(project_data)
            except Exception as e:
                print(f"An error occurred while fetching project members: {e}")


    except Exception as e:
        print(f"An error occurred while fetching subgroups/projects: {e}")

# Function to export the data to CSV
def export_to_csv(file_name="gitlab_groups_projects.csv"):
    try:
        # Define the CSV file headers (conditional based on LOC counting)
        headers = ['Group', 'Subgroup1', 'Subgroup2', 'Subgroup3', 'Project', 'Admins', 'Maintainers', 'Developers', 'Members', 'Project Size (MB)', 'Languages']

        if COUNT_LOC:
            headers.extend(['Lines of Code', 'LOC Breakdown'])

        # Sort group_data by 'Group', 'Subgroup1', 'Subgroup2', 'Subgroup3', and 'Project'
        sorted_data = sorted(group_data, key=lambda x: (x['Group'], x['Subgroup1'], x['Subgroup2'], x['Subgroup3'], x['Project']))

        # Write the collected data to a CSV file
        with open(file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers, delimiter=';')
            writer.writeheader()
            writer.writerows(sorted_data)

        print(f"Data successfully exported to {file_name}")

    except Exception as e:
        print(f"An error occurred while writing to CSV: {e}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Export GitLab groups, projects, and their members to CSV')
    parser.add_argument('--count-loc', action='store_true',
                        help='Count lines of code for each project using cloc (requires cloc to be installed, slower)')
    parser.add_argument('--output', type=str, default='gitlab_groups_projects.csv',
                        help='Output CSV file name (default: gitlab_groups_projects.csv)')
    args = parser.parse_args()

    # Set the global flag
    COUNT_LOC = args.count_loc

    print(f"Exporting groups and projects from {gl.url} to CSV...")
    if COUNT_LOC:
        print("LOC counting is ENABLED - this will clone/update repositories and count lines of code")
        print(f"Cache directory: {CACHE_DIR}")
        print("Repositories will be cached for faster subsequent runs")
    else:
        print("LOC counting is DISABLED - use --count-loc to enable")

    get_root_groups_and_projects()  # Fetch all root groups, subgroups, and projects
    export_to_csv(args.output)  # Export the collected data to a CSV file

    if COUNT_LOC:
        print(f"\nNote: Cloned repositories are cached in: {CACHE_DIR}")
        print("You can safely delete this directory to free up disk space")
