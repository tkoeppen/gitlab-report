# gitlab project reporter

- This project contains 2 tools

Tool 1:

- `gitlab-groups.py`
- exports all groups and projects from a self-hosted gitlab.
- It support up to 3 subgroups and sort groups, subgroups and projects alphabetically.
- It creates a `gitlab_groups_projects.csv` file. This file is overwritten with each run.
- The CSV file contains the list of projects with their members and repository size.

Tool 2:

- `gitlab-group-member.py`
- reads a list of Groups from groups.csv
- reads a list of users from users.csv
- add or remove the user with role developer or maintainer to the defined group depending on users.csv status `active` or `inactive`
- we used this to manage the permissions of gitlab users at one place instead via gitlab UI

## precondition

- MacOS or Linux with python3
- Access to the gitlab REST API

## preparation

### gitlab personal access token

Open <GITLAB_URL>/-/user_settings/personal_access_tokens in browser and add a personal access token with

- read_api scope for tool 1 (groups and projects report)
- write_api scopt for tool 2 (manage users)

### local environment config

create a .env file with (copy from .env.example) and set your config params.
In some corporate environments you want to access gitlab via your custom http proxy server, then set HTTP_PROXY.

```sh
# the personal access token for the GitLab API (need read_api scope)
export GITLAB_API_KEY=
# the URL of the GitLab instance
export GITLAB_URL=
# (optional) the URL of the HTTP proxy
export GITLAB_HTTP_PROXY=
```

## run tool 1 (groups and projects report)

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
source .env
python3 gitlab-groups.py
```

or in 2 steps

```sh
./setup.sh
./run-report.sh
```

## run tool 2 (manage gitlab user permissions)

- Before running the script, prepare both groups.csv and users.csv (copy example files).

```sh
./setup.sh
python3 gitlab-group-member.py
```

## development (VSCode)

To fix the error message in VSCode "import gitlab could not be resolved":

Select the Virtual Environment in VS Code:

- Open the Command Palette (MacOS: Cmd+Shift+P).
- Type and select Python: Select Interpreter.
- Choose the interpreter located in your .venv directory
