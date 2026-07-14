import sqlite3
import json
import sqlite_vec
from typing import Any


class DatabaseHandler:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)

        self.db.enable_load_extension(True)
        sqlite_vec.load(self.db)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                text TEXT,
                metadata TEXT
            )
        """)

        self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                embedding float[768]
            )
        """)

        self.db.commit()

    def add(
        self,
        user_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        cursor = self.db.execute(
            """
            INSERT INTO memories (user_id, text, metadata)
            VALUES (?, ?, ?)
            """,
            (user_id, text, json.dumps(metadata or {})),
        )

        self.db.execute(
            """
            INSERT INTO memory_vectors (rowid, embedding)
            VALUES (?, ?)
            """,
            (cursor.lastrowid, embedding),
        )

        self.db.commit()

    def search(
        self,
        user_id: str,
        query_vector: list[float],
        k: int = 5,
    ) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT
                memories.text,
                memories.metadata,
                memory_vectors.distance
            FROM memory_vectors
            JOIN memories ON memories.id = memory_vectors.rowid
            WHERE memory_vectors MATCH ?
              AND memories.user_id = ?
            ORDER BY distance
            LIMIT ?
            """,
            (query_vector, user_id, k),
        ).fetchall()

        return [
            {
                "text": text,
                "metadata": json.loads(metadata),
                "distance": distance,
            }
            for text, metadata, distance in rows
        ]
