import json
import pathlib

THIS_FILE = pathlib.PurePosixPath(
    pathlib.Path(__file__).relative_to(pathlib.Path().resolve())
)
ACTIONS_CHECKOUT = {"name": "Check out repository", "uses": "actions/checkout@v5"}


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


def gen_package_json():
    target = "package.json"
    content = {
        "name": "ocremix-data",
        "version": "1.0.0",
        "license": "UNLICENSED",
        "private": True,
        "dependencies": {"swagger-ui-dist": "5.27.1"},
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


def main():
    gen_dependabot()
    gen_package_json()
    gen_publish_workflow()


if __name__ == "__main__":
    main()
