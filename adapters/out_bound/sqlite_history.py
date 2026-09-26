# Persistencia local con SQLite puro de la librería estándar de Python.
# Si el usuario reinicia la PC o apaga el daemon, la memoria RAM desaparece,
# pero con este archivo .db en su perfil de usuario sabe exactamente qué bajó,
# cuándo y dónde quedó guardado en su disco rígido.
import sqlite3
from pathlib import Path
from typing import List, Optional
from domain.models import DownloadRecord
from ports.out_bound import HistoryRepositoryPort


class SqliteHistoryAdapter(HistoryRepositoryPort):
    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            self._db_path = Path(db_path)
        else:
            base_dir = Path.home() / ".offstream"
            base_dir.mkdir(parents=True, exist_ok=True)
            self._db_path = base_dir / "history.db"

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        # Usamos timeout de 10s por si múltiples hilos o la GUI y el daemon tocan la DB a la vez
        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS download_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    channel TEXT,
                    duration_seconds INTEGER,
                    created_at TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    media_kind TEXT DEFAULT 'video'
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_title ON download_history(title);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_channel ON download_history(channel);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON download_history(created_at);")

    def add_record(self, record: DownloadRecord) -> int:
        query = """
            INSERT INTO download_history (video_id, title, channel, duration_seconds, created_at, file_path, media_kind)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                query,
                (
                    record.video_id,
                    record.title,
                    record.channel,
                    record.duration_seconds,
                    record.created_at,
                    record.file_path,
                    record.media_kind,
                ),
            )
            return cursor.lastrowid or 0

    def _fetch_rows(self, conn: sqlite3.Connection, limit: int, query: Optional[str]) -> list:
        clean_query = query.strip() if query else None
        if clean_query:
            pattern = f"%{clean_query}%"
            sql = """
                SELECT id, video_id, title, channel, duration_seconds, created_at, file_path, media_kind
                FROM download_history
                WHERE title LIKE ? OR channel LIKE ?
                ORDER BY id DESC
                LIMIT ?
            """
            return conn.execute(sql, (pattern, pattern, limit)).fetchall()

        sql = """
            SELECT id, video_id, title, channel, duration_seconds, created_at, file_path, media_kind
            FROM download_history
            ORDER BY id DESC
            LIMIT ?
        """
        return conn.execute(sql, (limit,)).fetchall()

    @staticmethod
    def _row_to_record(r: sqlite3.Row) -> DownloadRecord:
        return DownloadRecord(
            id=r["id"],
            video_id=r["video_id"],
            title=r["title"],
            channel=r["channel"] or "Unknown",
            duration_seconds=int(r["duration_seconds"] or 0),
            created_at=r["created_at"],
            file_path=r["file_path"],
            media_kind=r["media_kind"] or "video",
        )

    def list_records(self, limit: int = 100, query: Optional[str] = None) -> List[DownloadRecord]:
        with self._get_connection() as conn:
            rows = self._fetch_rows(conn, limit, query)
        return [self._row_to_record(r) for r in rows]

    def delete_record(self, record_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM download_history WHERE id = ?", (record_id,))
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM download_history")
            return cursor.rowcount
