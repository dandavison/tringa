def failed_tests_in_branch(branch: str) -> str:
    return f"""
        select name, passed, flaky, count(*) as runs, max(time) as max_time from test
        where passed = false and skipped = false and branch = '{branch}'
        group by name, passed, flaky
        order by flaky desc, max_time desc
    """
