import sys
import os

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
import GitHubManager from github_automation

if __name__ == "__main__":
    ghm = GitHubManager()
