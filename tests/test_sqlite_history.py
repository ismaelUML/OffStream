from pathlib import Path
from adapters.out_bound.sqlite_history import SqliteHistoryAdapter
from domain.models import DownloadRecord


def test_sqlite_history_crud(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    adapter = SqliteHistoryAdapter(str(db_file))

    # 1. Agregar registros
    rec1 = DownloadRecord(
        id=None,
        video_id="abc12345678",
        title="Daft Punk - Get Lucky (Official Audio)",
        channel="Daft Punk VEVO",
        duration_seconds=248,
        created_at="2026-09-25T10:00:00",
        file_path="C:/Downloads/Get Lucky.mp3",
        media_kind="audio",
    )
    rec2 = DownloadRecord(
        id=None,
        video_id="xyz98765432",
        title="Queen - Bohemian Rhapsody",
        channel="Queen Official",
        duration_seconds=355,
        created_at="2026-09-25T11:00:00",
        file_path="C:/Downloads/Bohemian Rhapsody.mp4",
        media_kind="video",
    )

    id1 = adapter.add_record(rec1)
    id2 = adapter.add_record(rec2)
    assert id1 > 0
    assert id2 > id1

    # 2. Listar todos
    all_recs = adapter.list_records()
    assert len(all_recs) == 2
    assert all_recs[0].id == id2  # ORDER BY id DESC
    assert all_recs[1].id == id1

    # 3. Buscar por query (título y canal)
    search_daft = adapter.list_records(query="Daft")
    assert len(search_daft) == 1
    assert search_daft[0].video_id == "abc12345678"

    search_queen = adapter.list_records(query="bohemian")
    assert len(search_queen) == 1
    assert search_queen[0].video_id == "xyz98765432"

    search_none = adapter.list_records(query="Inexistente")
    assert len(search_none) == 0

    # 4. Eliminar un registro
    deleted = adapter.delete_record(id1)
    assert deleted is True
    assert len(adapter.list_records()) == 1

    # 5. Limpiar todo
    cleared = adapter.clear_all()
    assert cleared == 1
    assert len(adapter.list_records()) == 0
