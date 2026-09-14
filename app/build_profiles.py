from dataclasses import dataclass


@dataclass(frozen=True)
class BuildProfile:
    stack: str
    test_command: str
    manifest: str


PROFILES = {
    "python": BuildProfile("python", "python -m pytest -q", "pyproject.toml"),
    "node": BuildProfile("node", "npm test -- --runInBand", "package.json"),
    "flutter": BuildProfile("flutter", "flutter test", "pubspec.yaml"),
    "dotnet": BuildProfile("dotnet", "dotnet test", "*.sln"),
    "kotlin": BuildProfile("kotlin", "./gradlew test", "build.gradle.kts"),
}


def get_profile(stack: str) -> BuildProfile:
    try:
        return PROFILES[stack.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported stack: {stack}") from exc
