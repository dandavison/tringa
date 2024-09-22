from typing import Union

from duckdb import DuckDBPyRelation
from rich.console import Console

from tringa import cli
from tringa.models import Serializable

console = Console()


def tringa_print(obj: Union[DuckDBPyRelation, Serializable]) -> None:
    match obj:
        case DuckDBPyRelation() as rel:
            print_relation(rel)
        case Serializable() as obj:
            print_serializable(obj)
        case _:
            raise ValueError(f"Unsupported type: {type(obj)}")


def print_relation(rel: DuckDBPyRelation) -> None:
    if cli.options.json:
        console.print_json(data=rel.df().to_dict(orient="records"), sort_keys=True)
    else:
        console.print(rel)


def print_serializable(obj: Serializable) -> None:
    if cli.options.json:
        console.print_json(data=obj.to_dict(), sort_keys=True)
    else:
        console.print(obj)
