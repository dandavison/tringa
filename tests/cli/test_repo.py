import pytest
from typer import BadParameter

from tringa.cli.repo.cli import _validate_repo_arg


@pytest.mark.parametrize(
    ["input", "expected_output"],
    [
        ("dandavison/tringa", "dandavison/tringa"),
        ("https://github.com/dandavison/tringa", "dandavison/tringa"),
        ("https://github.com/dandavison/tringa/", "dandavison/tringa"),
        ("https://github.com/dandavison/tringa/pull/123", "dandavison/tringa"),
        ("git@github.com:dandavison/tringa.git", "dandavison/tringa"),
        ("git@github.com:dandavison/tringa", "dandavison/tringa"),
        ("https://example.com/user/repo/", BadParameter),
        ("user/repo/", BadParameter),
    ],
)
def test_validate_repo_arg(input, expected_output):
    if expected_output is BadParameter:
        with pytest.raises(BadParameter):
            _validate_repo_arg(input)
    else:
        assert _validate_repo_arg(input) == expected_output
