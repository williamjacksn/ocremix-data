import json
import pathlib

THIS_FILE = pathlib.PurePosixPath(
    pathlib.Path(__file__).relative_to(pathlib.Path().resolve())
)
ACTIONS_CHECKOUT = {"name": "Check out repository", "uses": "actions/checkout@v5"}
DISPATCH_BUILD_STEP = {
    "name": "Dispatch workflow to build pages",
    "if": "steps.commit.outputs.pushed == 'true'",
    "run": "gh workflow run github-pages.yaml",
    "env": {"GH_TOKEN": "${{ github.token }}"},
}
CRON_DAILY_0000 = {"cron": "0 0 * * *"}
CRON_HOURLY_30 = {"cron": "30 * * * *"}


def _commit_and_push_step(commit_message: str) -> dict:
    return {
        "name": "Commit and push if changes",
        "id": "commit",
        "run": "sh ci/commit-and-push.sh",
        "env": {"COMMIT_MESSAGE": commit_message},
    }


def gen(content: dict, target: str):
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target).write_text(
        json.dumps(content, indent=2, sort_keys=True), newline="\n"
    )


def gen_dependabot():
    target = ".github/dependabot.yaml"
    content = {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": e,
                "allow": [{"dependency-type": "all"}],
                "directory": "/",
                "schedule": {"interval": "daily"},
            }
            for e in ["github-actions", "npm", "uv"]
        ],
    }
    gen(content, target)


def gen_import_workflow():
    target = ".github/workflows/import-missing.yaml"
    content = {
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}"
        },
        "name": "Import missing ReMix info",
        "on": {"schedule": [CRON_DAILY_0000], "workflow_dispatch": {}},
        "jobs": {
            "import-missing": {
                "name": "Import missing ReMix info",
                "runs-on": "ubuntu-latest",
                "permissions": {"actions": "write", "contents": "write"},
                "steps": [
                    ACTIONS_CHECKOUT,
                    {
                        "name": "Import missing ReMix info",
                        "run": "sh ci/import-missing.sh",
                    },
                    _commit_and_push_step("Import missing ReMix info"),
                    DISPATCH_BUILD_STEP,
                ],
            }
        },
    }
    gen(content, target)


def gen_package_json():
    target = "package.json"
    content = {
        "description": f"This file ({target}) was generated from {THIS_FILE}",
        "name": "ocremix-data",
        "version": "1.0.0",
        "license": "UNLICENSED",
        "private": True,
        "dependencies": {"swagger-ui-dist": "5.29.3"},
    }
    gen(content, target)


def gen_publish_workflow():
    target = ".github/workflows/github-pages.yaml"
    content = {
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}"
        },
        "name": "Deploy to GitHub Pages",
        "on": {"push": {"branches": ["main"]}, "workflow_dispatch": {}},
        "concurrency": {"cancel-in-progress": True, "group": "github-pages"},
        "jobs": {
            "deploy": {
                "name": "Deploy to GitHub Pages",
                "runs-on": "ubuntu-latest",
                "environment": {
                    "name": "github-pages",
                    "url": "${{ steps.deployment.outputs.page_url }}",
                },
                "permissions": {
                    "contents": "read",
                    "pages": "write",
                    "id-token": "write",
                },
                "steps": [
                    ACTIONS_CHECKOUT,
                    {
                        "name": "Configure GitHub Pages",
                        "uses": "actions/configure-pages@v5",
                    },
                    {"name": "Build content", "run": "sh ci/build-pages.sh"},
                    {
                        "name": "Upload artifact",
                        "uses": "actions/upload-pages-artifact@v3",
                        "with": {"path": "output"},
                    },
                    {
                        "name": "Deploy to GitHub Pages",
                        "id": "deployment",
                        "uses": "actions/deploy-pages@v4",
                    },
                ],
            }
        },
    }
    gen(content, target)


def gen_ruff_workflow():
    target = ".github/workflows/ruff.yaml"
    content = {
        "name": "Ruff",
        "on": {"pull_request": {"branches": ["main"]}, "push": {"branches": ["main"]}},
        "permissions": {"contents": "read"},
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}"
        },
        "jobs": {
            "ruff-check": {
                "name": "Run ruff check",
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {"name": "Run ruff check", "run": "sh ci/ruff-check.sh"},
                ],
            },
            "ruff-format": {
                "name": "Run ruff format",
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {"name": "Run ruff format", "run": "sh ci/ruff-format.sh"},
                ],
            },
        },
    }
    gen(content, target)


def gen_update_workflow():
    target = ".github/workflows/update.yaml"
    content = {
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}",
        },
        "name": "Update ReMix info",
        "on": {
            "schedule": [CRON_HOURLY_30],
            "workflow_dispatch": {
                "inputs": {
                    "limit": {
                        "default": 10,
                        "description": "Number of ReMixes to update",
                        "required": True,
                        "type": "number",
                    }
                }
            },
        },
        "jobs": {
            "update-remix-info": {
                "name": "Update ReMix info",
                "runs-on": "ubuntu-latest",
                "permissions": {"actions": "write", "contents": "write"},
                "steps": [
                    ACTIONS_CHECKOUT,
                    {"name": "Install uv", "run": "sh ci/install-uv.sh"},
                    {
                        "name": "Update ReMix info (on schedule)",
                        "if": "github.event_name == 'schedule'",
                        "run": "uv run ocremixdata.py update",
                    },
                    {
                        "name": "Update ReMix info (on workflow_dispatch)",
                        "if": "github.event_name == 'workflow_dispatch'",
                        "run": "uv run ocremixdata.py update --limit ${{ inputs.limit }}",
                    },
                    _commit_and_push_step("Update ReMix info"),
                    DISPATCH_BUILD_STEP,
                ],
            },
        },
    }
    gen(content, target)


def main():
    gen_dependabot()
    gen_import_workflow()
    gen_package_json()
    gen_publish_workflow()
    gen_ruff_workflow()
    gen_update_workflow()


if __name__ == "__main__":
    main()
