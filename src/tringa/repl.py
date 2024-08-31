import duckdb
import IPython


def repl(conn: duckdb.DuckDBPyConnection):
    sql = conn.sql
    schema = sql(
        "select column_name, data_type from information_schema.columns where table_name = 'test'"
    )
    print(schema)
    n_rows = sql("select count(*) from test").fetchone()
    print("#rows: ", n_rows[0] if n_rows else "?")
    print("Example queries:\n")
    example_queries = [
        'sql("select name from test where passed = false and skipped = false")',
        'sql("select name, time from test order by time desc limit 10")',
    ]
    for q in example_queries:
        print(q)
    print("https://duckdb.org/docs/api/python/dbapi.html")
    IPython.start_ipython(argv=[], user_ns={"conn": conn, "sql": sql})
