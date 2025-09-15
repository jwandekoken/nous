"""ArcadeDB connection and utilities.
This implementation uses ArcadeDB through the ArcadeDB HTTP API.
"""

from .client import GraphDB
from .connection import close_graph_db, get_database_name, get_graph_db, reset_graph_db

__all__ = [
    "GraphDB",
    "get_graph_db",
    "close_graph_db",
    "reset_graph_db",
    "get_database_name",
]
