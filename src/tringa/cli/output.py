from duckdb import DuckDBPyRelation
from rich import print, print_json

from tringa import cli
from tringa.models import Serializable


def print_relation(rel: DuckDBPyRelation) -> None:
    if cli.options.json:
        print_json(data=rel.df().to_dict(orient="records"), sort_keys=True)
    else:
        print(rel)


def print_serializable(obj: Serializable) -> None:
    if cli.options.json:
        print_json(data=obj.to_dict(), sort_keys=True)
    print(obj)
