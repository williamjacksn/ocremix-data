import json
import pathlib

THIS_FILE = pathlib.PurePosixPath(
    pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
)


def gen(content: dict, target: str) -> None:
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target).write_text(
        json.dumps(content, indent=2, sort_keys=True), newline="\n"
    )


def gen_dependabot() -> None:
    target = ".github/dependabot.yaml"
    content = {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": e,
                "allow": [{"dependency-type": "all"}],
                "directory": "/",
                "schedule": {"interval": "weekly"},
            }
            for e in ["github-actions", "npm", "uv"]
        ],
    }
    gen(content, target)


def gen_package_json() -> None:
    target = "package.json"
    content = {
        "description": f"This file ({target}) was generated from {THIS_FILE}",
        "name": "ocremix-data",
        "version": "1.0.0",
        "license": "UNLICENSED",
        "private": True,
        "dependencies": {"swagger-ui-dist": "5.29.5"},
    }
    gen(content, target)


def main() -> None:
    gen_dependabot()
    gen_package_json()


if __name__ == "__main__":
    main()
