import time
import os
import sys
import json
from urllib.request import Request, urlopen


OWNER = "bikininjas"
REPO = "newbuild-scraper"
BRANCH = os.environ.get("CI_BRANCH", "alternative_components")
POLL_SECONDS = int(os.environ.get("CI_POLL_SECONDS", "60"))
MAX_MINUTES = int(os.environ.get("CI_MAX_MINUTES", "15"))


def gh_api(path: str):
    url = f"https://api.github.com{path}"
    req = Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_latest_push_run(owner: str, repo: str, branch: str):
    runs = gh_api(f"/repos/{owner}/{repo}/actions/runs?branch={branch}&event=push&per_page=1")
    items = runs.get("workflow_runs", [])
    return items[0] if items else None


def get_jobs(owner: str, repo: str, run_id: int):
    data = gh_api(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs")
    return data.get("jobs", [])


def main():
    start = time.time()
    print(f"Monitoring latest push workflow on {OWNER}/{REPO}@{BRANCH}...")
    while True:
        run = get_latest_push_run(OWNER, REPO, BRANCH)
        if not run:
            print("No runs found yet. Waiting...")
            time.sleep(POLL_SECONDS)
            continue
        run_id = run["id"]
        status = run.get("status")
        conclusion = run.get("conclusion")
        print(f"Run {run_id}: status={status}, conclusion={conclusion}")
        if status == "completed":
            break
        if (time.time() - start) / 60.0 > MAX_MINUTES:
            print("Timeout waiting for workflow to complete.")
            sys.exit(1)
        time.sleep(POLL_SECONDS)

    if conclusion == "success":
        print("Workflow succeeded.")
        sys.exit(0)

    print("Workflow failed; fetching job details...")
    jobs = get_jobs(OWNER, REPO, run_id)
    for job in jobs:
        print(f"Job: {job['name']} status={job['status']} conclusion={job['conclusion']}")
        if job.get("conclusion") != "success":
            for step in job.get("steps", []):
                print(f"  - Step: {step['name']} => {step['conclusion']}")
    sys.exit(1)


if __name__ == "__main__":
    main()
