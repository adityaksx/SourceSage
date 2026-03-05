import os
import subprocess
import requests


REPO_DIR = "storage/repos"


# -------------------------
# Extract repo info
# -------------------------

def parse_repo_url(url):

    parts = url.strip("/").split("/")

    owner = parts[-2]
    repo = parts[-1]

    return owner, repo


# -------------------------
# Clone repository
# -------------------------

def clone_repo(url):

    os.makedirs(REPO_DIR, exist_ok=True)

    repo_name = url.split("/")[-1]

    path = os.path.join(REPO_DIR, repo_name)

    if os.path.exists(path):
        return path

    subprocess.run(
        ["git", "clone", "--depth", "1", url, path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return path


# -------------------------
# Read README
# -------------------------

def read_readme(path):

    files = ["README.md", "readme.md", "README.txt"]

    for f in files:

        readme_path = os.path.join(path, f)

        if os.path.exists(readme_path):

            with open(readme_path, "r", encoding="utf-8", errors="ignore") as file:
                return file.read()

    return ""


# -------------------------
# Extract overview section
# -------------------------

def extract_overview(text, max_chars=2000):
    """
    Only return the beginning of README
    which usually explains the project
    """

    if not text:
        return ""

    return text[:max_chars]


# -------------------------
# GitHub API metadata
# -------------------------

def get_repo_metadata(url):

    owner, repo = parse_repo_url(url)

    api = f"https://api.github.com/repos/{owner}/{repo}"

    try:

        r = requests.get(api, timeout=10)

        data = r.json()

        return {
            "name": data.get("name"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count"),
            "language": data.get("language")
        }

    except:
        return {}


# -------------------------
# Main processor
# -------------------------

def process_github(url):

    metadata = get_repo_metadata(url)

    repo_path = clone_repo(url)

    readme = read_readme(repo_path)

    overview = extract_overview(readme)

    return {
        "repo": metadata.get("name"),
        "description": metadata.get("description"),
        "language": metadata.get("language"),
        "stars": metadata.get("stars"),
        "overview": overview
    }