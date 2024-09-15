import json
import os

from typer.testing import CliRunner

from tringa.cli.cli import app
from tringa.msg import error

runner = CliRunner(mix_stderr=False)


def test_sql_query():
    env = {}
    if test_dir := os.getenv("TRINGA_TEST_DIR"):
        env["PWD"] = test_dir
        os.chdir(test_dir)
    result = runner.invoke(
        app,
        [
            "sql",
            "--json",
            "select name from test where passed = false and repo='dandavison/tringa-test'",
        ],
        env=env,
    )
    if result.stderr:
        error("stderr: ", result.stderr)
    assert result.exit_code == 0
    assert json.loads(result.output) == [{"name": "test_failing"}]
