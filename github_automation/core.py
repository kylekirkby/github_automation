import sys
from git import Repo
import vault_auth
import os
import subprocess
from datetime import datetime, timezone
import requests
class GitHubManager:

    def __init__(self, repo_url, working_directory, path_to_ssh_key, auth_token, reviewers):

        self.github_repo = repo_url
        self.github_repo_key = self.github_repo.lstrip("https://github.com/")
        self.working_dir = working_directory
        self.ssh_key_path = path_to_ssh_key
        self.auth_token = auth_token
        self.error = False
        self.reviewers = reviewers
        self.repo_output_name = "website"
        self.repo_dir = "{}/{}".format(self.working_dir, self.repo_output_name)
        self.repo = self.setup_repo()

    def run_command(self, command):
        result = subprocess.run(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            self.error = True
            print("ERROR: '%s'" % command)
            print(result.stdout.decode("utf-8"))
            print(result.stderr.decode("utf-8"))
            sys.exit(result.returncode)

    def run_repo_command(self, command):
        """Runs a command inside the repo directory"""
        os.chdir(self.repo_dir)
        self.run_command(command)
        os.chdir(self.working_dir)

    def run_git_command(self, command, in_repo_directory=True):
        """ Run a git command on the repo """
        if in_repo_directory:
            os.chdir(self.repo_dir)
        git_cmd = 'ssh-add "{}"; {}'.format(self.ssh_key_path, command)
        full_cmd = "ssh-agent bash -c '{}'".format(git_cmd)
        print("running {}".format(full_cmd))
        self.run_command(full_cmd)
        if in_repo_directory:
            os.chdir(self.working_dir)

    def setup_repo(self):
        """Clones or pulls the repo specified in the constructor"""
        if os.path.isdir(self.repo_dir):
            print("Pulling repository...")
            # Ensure we are on the master branch first
            self.run_git_command("git checkout master")
            self.run_git_command("git pull")
        else:
            # Make sure we are in the working directory
            os.chdir(self.working_dir)
            print("Cloning website repository")
            print("Running git clone {}".format(self.github_repo))
            self.run_git_command(
                "git clone git@github.com:{}.git website".format(
                    self.github_repo_key), in_repo_directory=False)
            os.chdir(self.working_dir)

        self.run_git_command("git checkout master")

        return Repo(self.repo_dir)

    def create_github_pull_request(self, branch_name, title, body):
        """ Create a GitHub pull request with the latest Connect Jekyll posts"""

        self.run_git_command("git checkout -b {}".format(branch_name))
        print("Checked out {}".format(branch_name))

        # Only use run_git_command when we need the SSH key involved.
        self.run_repo_command("git add --all")
        self.run_repo_command(
            "git commit -m 'Session update for {}'".format(self.repo.active_branch.name))
        self.run_git_command(
            "git push --set-upstream origin {}".format(self.repo.active_branch.name))

        data = {
            "title": title,
            "body": body,
            "head": self.repo.active_branch.name,
            "base": "master"
        }

        headers = {'Authorization': 'token {}'.format(self.auth_token)}
        url = "https://api.github.com/repos/{}/pulls".format(
            self.github_repo_key)
        result = requests.post(url, json=data, headers=headers)

        if result.status_code != 201:
            print("ERROR: Failed to create pull request")
            print(result.text)
            self.error = True
            return False
        else:
            json = result.json()
            print("Pull request created: {}".format(json["html_url"]))
            data = {
                "reviewers": self.reviewers
            }
            url = "https://api.github.com/repos/{0}/pulls/{1}/requested_reviewers".format(
                self.github_repo_key, json["number"])

            result = requests.post(url, json=data, headers=headers)

            if result.status_code != 201:
                print("ERROR: Failed to add reviewers to the pull request")
                print(result.text)
                self.error = True
                return False
        self.run_git_command("git checkout master")
        self.run_git_command("git branch -D {}".format(branch_name))

        return True
