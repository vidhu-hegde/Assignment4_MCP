# API contract: https://docs.github.com/en/rest/pulls/pulls

import re
from pathlib import Path

import httpx
from dotenv import dotenv_values


ENV_FILE = Path(__file__).resolve().parent / ".env"
PATCH_LIMIT = 6000
BODY_LIMIT = 6000
OWNER_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,100}")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def validate_repository(owner: str, repo: str) -> None:
    if not isinstance(owner, str) or OWNER_PATTERN.fullmatch(owner) is None:
        raise ValueError("owner must be a GitHub account name, not a URL.")
    if (
        not isinstance(repo, str)
        or REPOSITORY_PATTERN.fullmatch(repo) is None
        or repo in {".", ".."}
    ):
        raise ValueError("repo must be a repository name, not a path or URL.")


def validate_positive_integer(value: int, name: str, maximum: int | None = None) -> None:
    if type(value) is not int or value < 1 or (maximum is not None and value > maximum):
        bound = f" between 1 and {maximum}" if maximum is not None else " greater than zero"
        raise ValueError(f"{name} must be an integer{bound}.")


def _get(path: str, params: dict | None = None) -> httpx.Response:
    token = (dotenv_values(ENV_FILE, interpolate=False).get("GITHUB_TOKEN") or "").strip()
    if not token:
        raise ValueError("Set GITHUB_TOKEN in the project's .env file before calling GitHub tools.")
    if TOKEN_PATTERN.fullmatch(token) is None:
        raise ValueError("GITHUB_TOKEN in .env has an invalid format.")
    try:
        response = httpx.get(
            f"https://api.github.com{path}",
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
            follow_redirects=False,
        )
    except httpx.TimeoutException:
        raise ValueError("GitHub timed out. Try again later.") from None
    except httpx.RequestError:
        raise ValueError("Could not connect to GitHub. Check your network connection.") from None
    if response.status_code == 401:
        raise ValueError("GitHub authentication failed. Check the token in .env.")
    if response.status_code == 429 or (
        response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
    ):
        raise ValueError("GitHub's rate limit was reached. Wait before retrying.")
    if response.status_code == 403:
        raise ValueError("GitHub denied access. Check token permissions or retry later.")
    if response.status_code == 404:
        raise ValueError("Repository or pull request not found, or the token has no access.")
    if response.status_code != 200:
        raise ValueError(f"GitHub could not complete the request (HTTP {response.status_code}).")
    return response


def _json(response: httpx.Response) -> dict | list:
    try:
        data = response.json()
    except ValueError:
        raise ValueError("GitHub returned an invalid JSON response.") from None
    if not isinstance(data, (dict, list)):
        raise ValueError("GitHub returned an unexpected response format.")
    return data


def list_pull_requests(owner: str, repo: str, page: int = 1, per_page: int = 10) -> dict:
    validate_repository(owner, repo)
    validate_positive_integer(page, "page")
    validate_positive_integer(per_page, "per_page", 30)
    response = _get(
        f"/repos/{owner}/{repo}/pulls",
        {
            "state": "open",
            "sort": "updated",
            "direction": "desc",
            "page": page,
            "per_page": per_page,
        },
    )
    pulls = _json(response)
    if not isinstance(pulls, list):
        raise ValueError("GitHub returned an unexpected pull-request list.")
    return {
        "repository": f"{owner}/{repo}",
        "page": page,
        "has_next_page": "next" in response.links,
        "pull_requests": [
            {
                "number": pull["number"],
                "title": pull["title"],
                "author": (pull.get("user") or {}).get("login"),
                "draft": pull.get("draft", False),
                "updated_at": pull["updated_at"],
                "url": pull["html_url"],
            }
            for pull in pulls
        ],
    }


def get_pull_request(owner: str, repo: str, pull_number: int, file_page: int = 1) -> dict:
    validate_repository(owner, repo)
    validate_positive_integer(pull_number, "pull_number")
    validate_positive_integer(file_page, "file_page")
    path = f"/repos/{owner}/{repo}/pulls/{pull_number}"
    pull = _json(_get(path))
    response = _get(f"{path}/files", {"page": file_page, "per_page": 10})
    files = _json(response)
    if not isinstance(pull, dict) or not isinstance(files, list):
        raise ValueError("GitHub returned unexpected pull-request details.")
    description = pull.get("body") or ""
    return {
        "repository": f"{owner}/{repo}",
        "number": pull["number"],
        "title": pull["title"],
        "description": description[:BODY_LIMIT],
        "description_truncated": len(description) > BODY_LIMIT,
        "state": pull["state"],
        "draft": pull.get("draft", False),
        "merged": pull.get("merged", False),
        "url": pull["html_url"],
        "base_branch": pull["base"]["ref"],
        "head_branch": pull["head"]["ref"],
        "head_sha": pull["head"]["sha"],
        "changed_files": pull["changed_files"],
        "additions": pull["additions"],
        "deletions": pull["deletions"],
        "file_page": file_page,
        "has_next_file_page": "next" in response.links,
        "files": [
            {
                "filename": file["filename"],
                "previous_filename": file.get("previous_filename"),
                "status": file["status"],
                "additions": file["additions"],
                "deletions": file["deletions"],
                "patch": (file.get("patch") or "")[:PATCH_LIMIT],
                "patch_available": bool(file.get("patch")),
                "patch_truncated": len(file.get("patch") or "") > PATCH_LIMIT,
            }
            for file in files
        ],
    }
