`tringa` is a tool for querying test output across multiple CI builds on GitHub.
It is in early development and not ready for use.

------------------------
- [Install](#install)
- [Example usage](#example-usage)
  - [TUI](#tui)
  - [SQL REPL](#sql-repl)
- [Required changes to GitHub Actions workflows](#required-changes-to-github-actions-workflows)
------------------------


### Install

Use [uv](https://docs.astral.sh/uv/):

```
$ uv tool install git+https://github.com/dandavison/tringa
```

### Example usage

```
$ tringa --help
```
<img width="856" alt="image" src="https://github.com/user-attachments/assets/e763b96a-f879-4d3a-985a-11b37db949cb">

Some commands print to the terminal, some bring up a TUI, and some bring up a SQL REPL for interactive queries.
By default the database is `duckdb` and persists across invocations.
The REPL can be a traditional SQL REPL, or a Python session using the [DuckDB Python API](https://duckdb.org/docs/api/python/overview.html).

#### TUI

```
$ tringa --tui pr
```

<img width="1295" alt="image" src="https://github.com/user-attachments/assets/765bd3f3-f333-4c23-8ecf-0326097469dd">

#### SQL REPL

The DB has one table, named `test`.

```
$ tringa pr --repl sql
```

```
D select artifact_name, name from test
  where passed = false and skipped = false and repo = 'temporalio/cli';
┌───────────────────────────────────────────┬─────────────────────────────────────────────────────────┐
│               artifact_name               │                          name                           │
│                  varchar                  │                         varchar                         │
├───────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ junit-xml--10631569269--1--ubuntu-latest  │ TestSharedServerSuite/TestWorkflow_Update_Execute       │
│ junit-xml--10631569269--1--ubuntu-latest  │ TestSharedServerSuite/TestWorkflow_Update_Start         │
│ junit-xml--10631569269--1--ubuntu-latest  │ TestSharedServerSuite                                   │
│ junit-xml--10884926916--1--windows-latest │ TestServer_StartDev_ConcurrentStarts                    │
│ junit-xml--10885937402--1--ubuntu-arm     │ TestSharedServerSuite/TestActivity_Complete             │
│ junit-xml--10885937402--1--ubuntu-arm     │ TestSharedServerSuite/TestWorkflow_Reset_ReapplyExclude │
│ junit-xml--10885937402--1--ubuntu-arm     │ TestSharedServerSuite                                   │
└───────────────────────────────────────────┴─────────────────────────────────────────────────────────┘

D SELECT name, type FROM pragma_table_info('test');
┌─────────────────┬───────────┐
│      name       │   type    │
│     varchar     │  varchar  │
├─────────────────┼───────────┤
│ artifact_name   │ VARCHAR   │
│ repo            │ VARCHAR   │
│ branch          │ VARCHAR   │
│ run_id          │ VARCHAR   │
│ sha             │ VARCHAR   │
│ file            │ VARCHAR   │
│ suite           │ VARCHAR   │
│ suite_time      │ TIMESTAMP │
│ suite_duration  │ FLOAT     │
│ name            │ VARCHAR   │
│ classname       │ VARCHAR   │
│ duration        │ FLOAT     │
│ passed          │ BOOLEAN   │
│ skipped         │ BOOLEAN   │
│ flaky           │ BOOLEAN   │
│ message         │ VARCHAR   │
│ text            │ VARCHAR   │
├─────────────────┴───────────┤
│ 17 rows           2 columns │
└─────────────────────────────┘
```

### Required changes to GitHub Actions workflows

For `tringa` to find output from a CI workflow run, at least one job in the run must upload an artifact containing a directory of junit-xml format files (named uniquely for that job).
For example, the following fragment of GitHub Actions workflow yaml creates a directory containing junit-xml output from two different test suite runs, and uploads the directory as an artifact.
You must ensure that the artifact name is unique within the repository (so you'll probably want to use `${{github.run_id}}` at least)

```yaml
- run: mkdir junit-xml
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
