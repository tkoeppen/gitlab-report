# gitlab project reporter

- This tool exports all groups and projects from a self-hosted gitlab.
- It support up to 3 subgroups and sort groups, subgroups and projects alphabetically.
- It creates a gitlab_groups_projects.csv file.

## precondition

- MacOS or Linux with python3
- Access to the gitlab REST API

## preparation

### gitlab personal access token

Open <GITLAB_URL>/-/user_settings/personal_access_tokens in browser and add a personal access token with

- read_api scope

### local environment config

create a .env file with (copy from .env.example) and set your config params

## run

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
source .env
python3 gitlab-groups.py
```

## development (VSCode)

To fix the error message in VSCode "import gitlab could not be resolved":

Select the Virtual Environment in VS Code:

- Open the Command Palette (MacOS: Cmd+Shift+P).
- Type and select Python: Select Interpreter.
- Choose the interpreter located in your .venv directory