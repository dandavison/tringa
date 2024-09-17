`tringa` is a tool for querying test output across multiple CI builds on GitHub.
It is in early development and not ready for use.

### Install
```
uv tool install git+https://github.com/dandavison/tringa
```

### Example usage

Some commands print to the terminal, 
By default the database is `duckdb` and persists across invocations.
The REPL can be a traditional SQL REPL, or a Python session using the [DuckDB Python API](https://duckdb.org/docs/api/python/overview.html).
The DB has one table, named `test`.

```
$ tringa --help
```
<img width="856" alt="image" src="https://github.com/user-attachments/assets/e763b96a-f879-4d3a-985a-11b37db949cb">


### Required changes to GitHub Actions workflows

For `tringa` to find output from a CI workflow run, at least one job in the run must upload an artifact containing a directory of junit-xml format files (named uniquely for that job).
For example, the following fragment of GitHub Actions workflow yaml creates a directory containing junit-xml output from two different test suite runs, and uploads the directory as an artifact.
- The artifact name must start `junit-xml--`.
- You must ensure that the artifact name is unique within the repository (so you'll probably want to use `${{github.run_id}}` at least)

```yaml
- run: my-test-command --test-suite-variant=something --junit-xml=junit-xml/${{ matrix.python }}-${{ matrix.os }}-something.xml
- run: my-test-command --test-suite-variant=something-else --junit-xml=junit-xml/${{ matrix.python }}-${{ matrix.os }}-something-else.xml
- name: "Upload junit-xml artifacts"
uses: actions/upload-artifact@v4
if: always()
with:
    name: junit-xml--${{github.run_id}}--${{github.run_attempt}}--${{ matrix.python }}--${{ matrix.os }}
    path: junit-xml
    retention-days: 30
```

### TUI

`tringa --tui pr` brings up a TUI interface. This is under development: currently you can reveal individual test failures.

<img width="1295" alt="image" src="https://github.com/user-attachments/assets/765bd3f3-f333-4c23-8ecf-0326097469dd">
