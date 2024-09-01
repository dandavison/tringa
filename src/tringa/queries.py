def failed_tests_in_branch(branch: str) -> str:
    return f"""
        select name, passed, max(time) as max_time, count(*) as runs from test
        where passed = false and skipped = false and branch = '{branch}'
        group by name, passed
        order by max_time desc
    """
