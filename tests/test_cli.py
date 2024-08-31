from tringa.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_repl_command_can_be_run():
    result = runner.invoke(app, ["repl", "--help"])
    assert result.exit_code == 0


def test_repl_command_cannot_be_run():
    result = runner.invoke(app, ["repl", "--help"])
    assert result.exit_code != 0
