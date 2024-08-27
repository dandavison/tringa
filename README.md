`tringa` is a tool for querying test output across multiple CI builds on GitHub.
It is in early development and not ready for use.

### Install
```
uv tool install git+https://github.com/dandavison/tringa
```

### Example usage

Running `tringa` will download artifacts and leave you in an IPython REPL.
There you'll find a function named `sql`, from the [DuckDB Python API](https://duckdb.org/docs/api/python/overview.html).
It is connected to a database that has one table, named `test`.


```
$ tringa temporalio/sdk-python

In [1]: sql("select * from test limit 1")
Out[1]:
┌────────────────────┬─────────┬──────────────────────┬───┬─────────┬─────────┬─────────┬─────────┐
│        file        │  suite  │   suite_timestamp    │ … │ passed  │ skipped │ message │  text   │
│      varchar       │ varchar │      timestamp       │   │ boolean │ boolean │ varchar │ varchar │
├────────────────────┼─────────┼──────────────────────┼───┼─────────┼─────────┼─────────┼─────────┤
│ 3.8-ubuntu-arm.xml │ pytest  │ 2024-08-25 15:27:5…  │ … │ true    │ false   │ NULL    │ NULL    │
├────────────────────┴─────────┴──────────────────────┴───┴─────────┴─────────┴─────────┴─────────┤
│ 1 rows                                                                     11 columns (7 shown) │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

In [2]: sql("select message from test where passed = false and skipped = false")
Out[2]:
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                message                                                 │
│                                                varchar                                                 │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ AssertionError: assert 'Deliberately failing with next_retry_delay set' != 'Deliberately failing wit…  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

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

### Example queries

<details>
<summary>
Find failed tests in a single PR
</summary>

<br>

**TODO**: support limiting by PR instead of branch.

```
$ uv run tringa temporalio/sdk-python --branch=fix-rpc-error-handling

In [8]: sql("select passed, message from test where name = 'test_rpc_already_exists_error_is_raised' ")
Out[8]:
┌─────────┬────────────────────────────────────────────────────────────────────────────────────────────┐
│ passed  │                                          message                                           │
│ boolean │                                          varchar                                           │
├─────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ true    │ NULL                                                                                       │
│ false   │ AttributeError: '_TimeSkippingClientOutboundInterceptor' object has no attribute '_client' │
│ true    │ NULL                                                                                       │
│ true    │ NULL                                                                                       │
│ false   │ AttributeError: '_TimeSkippingClientOutboundInterceptor' object has no attribute '_client' │
│ true    │ NULL                                                                                       │
│ true    │ NULL                                                                                       │
│ false   │ AttributeError: '_TimeSkippingClientOutboundInterceptor' object has no attribute '_client' │
│ true    │ NULL                                                                                       │
│ false   │ AttributeError: '_TimeSkippingClientOutboundInterceptor' object has no attribute '_client' │
│ true    │ NULL                                                                                       │
│ false   │ AttributeError: '_TimeSkippingClientOutboundInterceptor' object has no attribute '_client' │
│ true    │ NULL                                                                                       │
│ true    │ NULL                                                                                       │
├─────────┴────────────────────────────────────────────────────────────────────────────────────────────┤
│ 14 rows                                                                                    2 columns │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

</details>