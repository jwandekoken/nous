"""User graph database models and utilities.
This example shows how to structure graph models for Neo4j.
"""

from datetime import datetime
from typing import Any

from app.db.graph import get_graph_db


class UserNode:
    """User node representation for graph database."""

    def __init__(
        self,
        user_id: int,
        email: str,
        full_name: str | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
    ):
        self.user_id = user_id
        self.email = email
        self.full_name = full_name
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert user node to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserNode":
        """Create user node from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        return cls(
            user_id=data["user_id"],
            email=data["email"],
            full_name=data.get("full_name"),
            is_active=data.get("is_active", True),
            created_at=created_at,
        )


class UserGraphService:
    """Service for managing user nodes and relationships in graph database."""

    async def create_user_node(self, user_node: UserNode) -> bool:
        """Create a user node in the graph database."""
        graph_db = await get_graph_db()

        query = """
        CREATE (u:User {
            user_id: $user_id,
            email: $email,
            full_name: $full_name,
            is_active: $is_active,
            created_at: $created_at
        })
        RETURN u
        """

        result = await graph_db.execute_query(query, user_node.to_dict())
        return len(result) > 0

    async def get_user_node(self, user_id: int) -> UserNode | None:
        """Get a user node by ID."""
        graph_db = await get_graph_db()

        query = """
        MATCH (u:User {user_id: $user_id})
        RETURN u
        """

        result = await graph_db.execute_query(query, {"user_id": user_id})

        if result:
            user_data = result[0].get("u", {})
            return UserNode.from_dict(user_data)

        return None

    async def update_user_node(self, user_id: int, updates: dict[str, Any]) -> bool:
        """Update a user node."""
        graph_db = await get_graph_db()

        # Build SET clause dynamically
        set_clauses = [f"u.{key} = ${key}" for key in updates]
        set_clause = ", ".join(set_clauses)

        query = f"""
        MATCH (u:User {{user_id: $user_id}})
        SET {set_clause}
        RETURN u
        """

        params = {"user_id": user_id, **updates}
        result = await graph_db.execute_query(query, params)
        return len(result) > 0

    async def delete_user_node(self, user_id: int) -> bool:
        """Delete a user node and all its relationships."""
        graph_db = await get_graph_db()

        query = """
        MATCH (u:User {user_id: $user_id})
        DETACH DELETE u
        """

        await graph_db.execute_query(query, {"user_id": user_id})
        return True

    async def create_friendship(self, user_id1: int, user_id2: int) -> bool:
        """Create a friendship relationship between two users."""
        graph_db = await get_graph_db()

        query = """
        MATCH (u1:User {user_id: $user_id1})
        MATCH (u2:User {user_id: $user_id2})
        CREATE (u1)-[:FRIENDS_WITH {created_at: $created_at}]->(u2)
        CREATE (u2)-[:FRIENDS_WITH {created_at: $created_at}]->(u1)
        """

        params = {
            "user_id1": user_id1,
            "user_id2": user_id2,
            "created_at": datetime.utcnow().isoformat(),
        }

        await graph_db.execute_query(query, params)
        return True

    async def get_user_friends(self, user_id: int) -> list[UserNode]:
        """Get all friends of a user."""
        graph_db = await get_graph_db()

        query = """
        MATCH (u:User {user_id: $user_id})-[:FRIENDS_WITH]->(friend:User)
        RETURN friend
        """

        result = await graph_db.execute_query(query, {"user_id": user_id})

        friends = []
        for record in result:
            friend_data = record.get("friend", {})
            friends.append(UserNode.from_dict(friend_data))

        return friends
