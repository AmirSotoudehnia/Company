import pytest

from app.build_profiles import get_profile


@pytest.mark.parametrize("stack,command", [
    ("python", "python -m pytest -q"),
    ("node", "npm test -- --runInBand"),
    ("flutter", "flutter test"),
    ("dotnet", "dotnet test"),
    ("kotlin", "./gradlew test"),
])
def test_supported_profiles(stack, command):
    assert get_profile(stack).test_command == command


def test_unknown_profile_fails_closed():
    with pytest.raises(ValueError, match="Unsupported stack"):
        get_profile("unknown")
