import requests
import csv
from datetime import datetime, timedelta
import os

def fetch_last_commit_date(repo_name, headers):

    REPO_URL = f'https://api.github.com/repos/{repo_name}'
    repo_response = requests.get(REPO_URL, headers=headers)
    if repo_response.status_code != 200:
        return None
    repo_data = repo_response.json()
    default_branch = repo_data.get('default_branch', 'main')
    COMMITS_URL = f'https://api.github.com/repos/{repo_name}/commits?sha={default_branch}&per_page=1'
    commits_response = requests.get(COMMITS_URL, headers=headers)
    if commits_response.status_code == 200:
        commits = commits_response.json()
        if isinstance(commits, list) and len(commits) > 0:
            return commits[0]['commit']['committer']['date']
    return None


def fetch_repository_details(repo_name, headers):

    REPO_URL = f'https://api.github.com/repos/{repo_name}'
    response = requests.get(REPO_URL, headers=headers)

    if response.status_code == 200:
        repo_data = response.json()
        owner_data = repo_data['owner']

        # Extracting owner details
        owner_name = owner_data['login']
        owner_id = owner_data['id']
        owner_url = owner_data['html_url']
        owner_type = owner_data['type']

        # Fetch last commit date
        last_commit_date = fetch_last_commit_date(repo_name, headers)

        # Display owner details
        print(f"\nRepository: {repo_name}")
        print(f"Owner Name: {owner_name}")
        print(f"Owner ID: {owner_id}")
        print(f"Owner URL: {owner_url}")
        print(f"Owner Type: {owner_type}")
        print(f"Last Commit Date: {last_commit_date}")
    else:
        print(f"Error fetching repository details for {repo_name}: {response.status_code}")
        print(response.json())


def fetch_contributors_and_committers(repo_name, headers):

    # Check if the repository is empty
    REPO_URL = f'https://api.github.com/repos/{repo_name}'
    repo_response = requests.get(REPO_URL, headers=headers)
    if repo_response.status_code != 200:
        print(f"Error fetching repository info for {repo_name}: {repo_response.status_code}")
        return None
    repo_data = repo_response.json()
    default_branch = repo_data.get('default_branch', 'main')
    CONTENTS_URL = f'https://api.github.com/repos/{repo_name}/contents?ref={default_branch}'
    contents_response = requests.get(CONTENTS_URL, headers=headers)
    if contents_response.status_code == 200:
        contents = contents_response.json()
        # Check for GitHub's empty repo message
        if isinstance(contents, dict) and contents.get("message") == "This repository is empty.":
            print(f"Repository {repo_name} is empty. No contributors to fetch.")
            return None
        if not (isinstance(contents, list) and len(contents) > 0):
            print(f"Repository {repo_name} is empty. No contributors to fetch.")
            return None
    else:
        print(f"Error fetching contents for {repo_name}: {contents_response.status_code}")
        return None

    CONTRIBUTORS_URL = f'https://api.github.com/repos/{repo_name}/contributors?per_page=5'
    contributors_response = requests.get(CONTRIBUTORS_URL, headers=headers)
    contributors_list = []
    if contributors_response.status_code == 200:
        contributors_data = contributors_response.json()
        print("\nContributors:")
        for contributor in contributors_data[:5]:
            print(f"- {contributor['login']} (Contributions: {contributor['contributions']})")
            contributors_list.append({
                "login": contributor['login'],
                "contributions": contributor['contributions']
            })
    else:
        print(f"Error fetching contributors details for {repo_name}: {contributors_response.status_code}")
        print(contributors_response.json())
    return contributors_list


def repo_has_code(repo_name, headers):

    REPO_URL = f'https://api.github.com/repos/{repo_name}'
    repo_response = requests.get(REPO_URL, headers=headers)
    if repo_response.status_code != 200:
        print(f"Error fetching repository info for {repo_name}: {repo_response.status_code}")
        return False
    repo_data = repo_response.json()
    default_branch = repo_data.get('default_branch', 'main')
    # Check contents of the root directory in the default branch
    CONTENTS_URL = f'https://api.github.com/repos/{repo_name}/contents?ref={default_branch}'
    contents_response = requests.get(CONTENTS_URL, headers=headers)
    if contents_response.status_code == 200:
        contents = contents_response.json()
        if isinstance(contents, list) and len(contents) > 0:
            # List of CI/CD config filenames and directories (case-insensitive)
            cicd_files = {
                '.github', '.github/workflows', '.gitlab-ci.yml', 'jenkinsfile', 'circleci', '.circleci',
                'azure-pipelines.yml', '.travis.yml', '.drone.yml', '.gitlab', 'bitbucket-pipelines.yml'
            }
            non_readme_non_cicd_files = [
                f for f in contents
                if not (
                    f.get('type') == 'file' and (
                        f.get('name', '').lower().startswith('readme') or
                        f.get('name', '').lower() in cicd_files
                    )
                )
                and not (
                    f.get('type') == 'dir' and f.get('name', '').lower() in cicd_files
                )
            ]
            if len(non_readme_non_cicd_files) > 0:
                return True
            else:
                print(f"No code found in {repo_name} (only README and/or CI/CD config files present).")
                return False
        else:
            print(f"No code found in {repo_name} (empty repository).")
            return False
    else:
        print(f"Error fetching contents for {repo_name}: {contents_response.status_code}")
        return False


def repo_code_category(repo_name, headers):

    REPO_URL = f'https://api.github.com/repos/{repo_name}'
    repo_response = requests.get(REPO_URL, headers=headers)
    if repo_response.status_code != 200:
        print(f"Error fetching repository info for {repo_name}: {repo_response.status_code}")
        return "error"
    repo_data = repo_response.json()
    default_branch = repo_data.get('default_branch', 'main')
    CONTENTS_URL = f'https://api.github.com/repos/{repo_name}/contents?ref={default_branch}'
    contents_response = requests.get(CONTENTS_URL, headers=headers)
    if contents_response.status_code == 200:
        contents = contents_response.json()
        if not (isinstance(contents, list) and len(contents) > 0):
            print(f"No code found in {repo_name} (empty repository).")
            return "empty"
        cicd_files = {
            '.github', '.github/workflows', '.gitlab-ci.yml', 'jenkinsfile', 'circleci', '.circleci',
            'azure-pipelines.yml', '.travis.yml', '.drone.yml', '.gitlab', 'bitbucket-pipelines.yml'
        }
        files = [f for f in contents if f.get('type') == 'file']
        dirs = [f for f in contents if f.get('type') == 'dir']
        non_readme_non_cicd = [
            f for f in files
            if not (
                f.get('name', '').lower().startswith('readme') or
                f.get('name', '').lower() in cicd_files
            )
        ] + [
            d for d in dirs
            if d.get('name', '').lower() not in cicd_files
        ]
        only_readme = (
            all(
                f.get('name', '').lower().startswith('readme')
                for f in files
            ) and len(files) > 0 and len(dirs) == 0
        )
        only_cicd = (
            all(
                (f.get('name', '').lower() in cicd_files or f.get('name', '').lower().startswith('readme'))
                for f in files
            ) and all(
                d.get('name', '').lower() in cicd_files
                for d in dirs
            ) and len(files) + len(dirs) > 0 and len(non_readme_non_cicd) == 0 and not only_readme
        )
        if len(non_readme_non_cicd) > 0:
            return "has code"
        elif only_readme:
            print(f"No code found in {repo_name} (only README files present).")
            return "readme only"
        elif only_cicd:
            print(f"No code found in {repo_name} (only CI/CD config files present).")
            return "cicd configs only"
        else:
            print(f"No code found in {repo_name} (empty repository).")
            return "empty"
    else:
        print(f"Error fetching contents for {repo_name}: {contents_response.status_code}")
        return "error"


def lambda_handler(event, context):

    # Get GitHub token from event or environment variable
    token = event.get("token") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"status": "error", "message": "GitHub token is required (set GITHUB_TOKEN env variable or pass in event)."}

    repo_names = event.get("repo_names")
    if not repo_names or not isinstance(repo_names, list):
        return {"status": "error", "message": "repo_names (list) is required in the event."}

    # S3 bucket name
    s3_bucket = "contributortest"
    # Add system time to output file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"output_{timestamp}.csv"

    headers = {
        'Authorization': f'token {token}'
    }

    # Write to a temporary file before uploading to S3
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8', delete=False) as tmpfile:
        output_file = tmpfile.name
        try:
            combined_writer = csv.writer(tmpfile)
            # Write header for the combined file
            combined_writer.writerow(["Repository", "Login", "Contributions", "Finding", "Last Commit Date", "Status"])

            for repo_name in repo_names:
                repo_name = repo_name.strip()
                if repo_name:
                    category = repo_code_category(repo_name, headers)
                    fetch_repository_details(repo_name, headers)
                    contributors = fetch_contributors_and_committers(repo_name, headers)
                    last_commit_date = fetch_last_commit_date(repo_name, headers)

                    # Determine status based on last commit date
                    status = ""
                    if last_commit_date:
                        try:
                            commit_dt = datetime.strptime(last_commit_date, "%Y-%m-%dT%H:%M:%SZ")
                            if commit_dt < datetime.utcnow() - timedelta(days=18 * 30):  # Approx 18 months
                                status = "no commits in 18 months"
                        except Exception:
                            status = ""

                    # Mark as 'repo is empty' in output for empty repos (no files)
                    if contributors is None and category == "error":
                        combined_writer.writerow([repo_name, "", "", "Repo is empty", last_commit_date, status])
                    elif contributors:
                        for contributor in contributors:
                            combined_writer.writerow([
                                repo_name,
                                contributor['login'],
                                contributor['contributions'],
                                category,
                                last_commit_date,
                                status
                            ])
                    else:
                        combined_writer.writerow([repo_name, "", "", category, last_commit_date, status])
        except Exception as e:
            return {"status": "error", "message": f"An error occurred: {e}"}

    # Upload to S3 with timestamped filename
    try:
        s3 = s3.upload_file(output_file, s3_bucket, output_filename)
        s3_url = f"s3://{s3_bucket}/{output_filename}"
        return {"status": "success", "s3_url": s3_url}
    except Exception as e:
        return {"status": "error", "message": f"Failed to upload to S3: {e}"}

