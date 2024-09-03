from textwrap import dedent


def count_test_results() -> str:
    return "select count(*) from test;"


def failed_tests_in_run(run_id: str) -> str:
    return dedent(f"""
        select file, name, passed, flaky, count(*) as runs, max(time) as max_time from test
        where passed = false and skipped = false and run_id = '{run_id}'
        group by file, name, passed, flaky
        order by file, flaky desc, max_time desc;
    """)


def last_run_id(repo: str, branch: str) -> str:
    return dedent(f"""
        select run_id from test
        where repo = '{repo}' and branch = '{branch}'
        order by suite_timestamp desc
        limit 1;
    """)
