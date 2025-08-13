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


def main():
    gen_dependabot()
    gen_package_json()


if __name__ == "__main__":
    main()
