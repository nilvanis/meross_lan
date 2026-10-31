"""Merge the latest stable upstream Release and maintain one reviewable PR."""

import json
import os
import sys

from home_common import (
    BASE,
    BRANCH,
    FORK,
    GitHub,
    MARKER,
    UPSTREAM,
    git,
    output,
    quote,
    validate_home_tree,
    validate_marker,
    write_json,
)

REPORT_TITLE = "Upstream synchronization needs attention"


def tag_commit(api, tag):
    obj = api.request("GET", f"repos/{UPSTREAM}/git/ref/tags/{quote(tag)}")["object"]
    for _ in range(10):
        if obj["type"] == "commit":
            return obj["sha"]
        if obj["type"] != "tag":
            break
        obj = api.request("GET", f"repos/{UPSTREAM}/git/tags/{obj['sha']}")["object"]
    raise ValueError("Upstream release tag does not resolve to a commit")


def report(api, body):
    issues = api.request("GET", f"repos/{FORK}/issues?state=open&per_page=100")
    issue = next(
        (
            item
            for item in issues
            if item["title"] == REPORT_TITLE and "pull_request" not in item
        ),
        None,
    )
    if issue:
        api.request("PATCH", f"repos/{FORK}/issues/{issue['number']}", {"body": body})
    else:
        api.request(
            "POST", f"repos/{FORK}/issues", {"title": REPORT_TITLE, "body": body}
        )


def dispatch_checks(api, sha):
    # The workflow definition comes from trusted master; candidate code gets read-only jobs.
    api.request(
        "POST",
        f"repos/{FORK}/actions/workflows/pull.yml/dispatches",
        {"ref": BASE, "inputs": {"ref": sha}},
    )


def sync(api):
    automation_api = (
        GitHub(os.environ.get("AUTOMATION_TOKEN"))
        if os.environ.get("AUTOMATION_TOKEN")
        else api
    )
    release = api.request("GET", f"repos/{UPSTREAM}/releases/latest")
    if release["draft"] or release["prerelease"]:
        raise ValueError("The selected upstream Release is not stable")
    marker = validate_marker(
        {
            "repository": UPSTREAM,
            "tag": release["tag_name"],
            "sha": tag_commit(api, release["tag_name"]),
        }
    )
    git(
        "fetch", "--no-tags", "origin", f"+refs/heads/{BASE}:refs/remotes/origin/{BASE}"
    )
    previous = validate_marker(
        json.loads(git("show", f"origin/{BASE}:{MARKER}").stdout)
    )
    if previous["tag"] == marker["tag"]:
        if previous["sha"] != marker["sha"]:
            raise ValueError(
                "Upstream moved an already imported release tag; refusing to replace it"
            )
        output(changed="false")
        print(f"Already tracking {marker['tag']} ({marker['sha']}).")
        return

    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    ref = "refs/remotes/home-upstream/release"
    git(
        "fetch",
        "--no-tags",
        f"https://github.com/{UPSTREAM}.git",
        f"+refs/tags/{marker['tag']}:{ref}",
    )
    if git("rev-parse", f"{ref}^{{commit}}").stdout.strip() != marker["sha"]:
        raise ValueError(
            "Fetched tag differs from the release SHA resolved through GitHub"
        )
    if git(
        "merge-base", "--is-ancestor", previous["sha"], marker["sha"], check=False
    ).returncode:
        raise ValueError(
            "New release is not a descendant of the imported release; manual review required"
        )
    workflows = git(
        "diff", "--name-only", previous["sha"], marker["sha"], "--", ".github/workflows"
    ).stdout
    if workflows and os.environ.get("SYNC_CUSTOM_TOKEN") != "true":
        raise ValueError(
            "Upstream changes Actions workflows. Configure UPSTREAM_SYNC_TOKEN with Contents, "
            "Pull requests and Workflows write permissions before retrying.\n\n"
            + workflows
        )

    old_branch = api.request(
        "GET", f"repos/{FORK}/git/ref/heads/{quote(BRANCH)}", missing_ok=True
    )
    owner = FORK.split("/")[0]
    pulls = api.request(
        "GET",
        f"repos/{FORK}/pulls?state=open&head={quote(owner + ':' + BRANCH)}&base={BASE}",
    )
    if old_branch and pulls:
        git(
            "fetch",
            "--no-tags",
            "origin",
            f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}",
        )
        existing_sha = old_branch["object"]["sha"]
        existing_marker = git("show", f"{existing_sha}:{MARKER}", check=False)
        if (
            existing_marker.returncode == 0
            and json.loads(existing_marker.stdout) == marker
            and git(
                "merge-base",
                "--is-ancestor",
                f"origin/{BASE}",
                existing_sha,
                check=False,
            ).returncode
            == 0
        ):
            dispatch_checks(automation_api, existing_sha)
            output(changed="false", sha=existing_sha, tag=marker["tag"])
            print(
                "Existing PR already contains this release and current master; keeping its commits."
            )
            return
    # Keep any human conflict resolutions already committed to an open update PR.
    # New master commits are merged into that history instead of rebuilding it.
    starting_ref = (
        old_branch["object"]["sha"] if old_branch and pulls else f"origin/{BASE}"
    )
    git("checkout", "-B", BRANCH, starting_ref)
    if old_branch and pulls:
        merged_base = git(
            "merge", "--no-ff", "--no-edit", f"origin/{BASE}", check=False
        )
        if merged_base.returncode:
            paths = git("diff", "--name-only", "--diff-filter=U").stdout
            git("merge", "--abort", check=False)
            raise ValueError(
                f"Merge conflict updating the existing PR with master. No candidate was pushed.\n\n{paths}"
            )
    merged = git("merge", "--no-ff", "--no-edit", marker["sha"], check=False)
    if merged.returncode:
        paths = git("diff", "--name-only", "--diff-filter=U").stdout
        git("merge", "--abort", check=False)
        raise ValueError(
            f"Merge conflict importing {marker['tag']}. No candidate was pushed.\n\n{paths}"
        )
    write_json(MARKER, marker)
    validate_home_tree(marker)
    git("add", str(MARKER))
    if git("diff", "--cached", "--quiet", check=False).returncode:
        git("commit", "-m", f"Track upstream release {marker['tag']}")
    sha = git("rev-parse", "HEAD").stdout.strip()
    expected = old_branch["object"]["sha"] if old_branch else ""
    git(
        "push",
        f"--force-with-lease=refs/heads/{BRANCH}:{expected}",
        "origin",
        f"HEAD:refs/heads/{BRANCH}",
    )

    body = (
        f"Import stable upstream release [{marker['tag']}]({release['html_url']}) "
        f"at `{marker['sha']}` using a Git merge.\n\n"
        "Home changes remain in the merge history. CI protects AUTO HVAC mode, the HACS name, "
        "and the integration. Review and use **Create a merge commit**; do not squash or rebase. "
        "After merging, the tested fork commit is published under the original upstream tag.\n\n"
        "Automatic merging is disabled.\n\n"
        f"Upstream release notes:\n\n{release.get('body') or '(No upstream release notes.)'}"
    )
    values = {"title": f"Update upstream to {marker['tag']}", "body": body}
    if pulls:
        api.request("PATCH", f"repos/{FORK}/pulls/{pulls[0]['number']}", values)
    else:
        api.request(
            "POST", f"repos/{FORK}/pulls", {**values, "head": BRANCH, "base": BASE}
        )
    dispatch_checks(automation_api, sha)
    output(changed="true", sha=sha, tag=marker["tag"])
    print(f"Prepared {marker['tag']} at fork commit {sha}.")


def main():
    api = GitHub()
    try:
        sync(api)
    except Exception as error:
        message = str(error)
        run_url = f"https://github.com/{FORK}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
        try:
            report(
                (
                    GitHub(os.environ.get("AUTOMATION_TOKEN"))
                    if os.environ.get("AUTOMATION_TOKEN")
                    else api
                ),
                f"Synchronization stopped safely.\n\n```text\n{message}\n```\n\n[Workflow log]({run_url})",
            )
        except Exception as report_error:
            print(f"Could not create GitHub issue: {report_error}", file=sys.stderr)
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
