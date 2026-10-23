import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.database import (
    init_db,
    create_action,
    clear_ai_recommendation_actions,
    get_all_actions,
    get_action_by_id,
    update_action,
    update_action_status_and_notes,
    delete_action,
    get_action_statistics,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite database path."""
    db_file = tmp_path / "test_mezy.db"
    init_db(db_file)
    return db_file


def test_init_db_creates_table(temp_db: Path):
    """Verify init_db initializes the schema correctly."""
    actions = get_all_actions(db_path=temp_db)
    assert actions == []


def test_create_action_valid(temp_db: Path):
    """Verify creating an action persists correctly and returns an integer ID."""
    action_id = create_action(
        title="Speed up kitchen order dispatch",
        action="Implement order queuing display in kitchen",
        priority="High",
        evidence="Customer waited 45 mins for pasta",
        notes="Discuss with head chef",
        status="Open",
        db_path=temp_db,
    )
    assert isinstance(action_id, int)
    assert action_id > 0

    item = get_action_by_id(action_id, db_path=temp_db)
    assert item is not None
    assert item["title"] == "Speed up kitchen order dispatch"
    assert item["action"] == "Implement order queuing display in kitchen"
    assert item["priority"] == "High"
    assert item["status"] == "Open"
    assert item["evidence"] == "Customer waited 45 mins for pasta"
    assert item["notes"] == "Discuss with head chef"
    assert item["created_at"] is not None


def test_create_action_validation_failures(temp_db: Path):
    """Verify create_action raises ValueError on missing required fields or invalid enums."""
    with pytest.raises(ValueError, match="Issue title is required"):
        create_action(title="", action="Fix hygiene", db_path=temp_db)

    with pytest.raises(ValueError, match="Suggested action is required"):
        create_action(title="Hygiene issue", action="", db_path=temp_db)

    with pytest.raises(ValueError, match="Invalid priority"):
        create_action(
            title="Title", action="Action", priority="SuperUrgent", db_path=temp_db
        )

    with pytest.raises(ValueError, match="Invalid status"):
        create_action(
            title="Title", action="Action", status="Waiting", db_path=temp_db
        )


def test_get_all_actions_filtering_and_search(temp_db: Path):
    """Verify filtering by status, priority, and text search."""
    id1 = create_action(
        title="Train waitstaff on cordial greetings",
        action="Conduct 15-minute morning hospitality briefing",
        priority="Medium",
        evidence="Staff was cold",
        status="Open",
        db_path=temp_db,
    )
    id2 = create_action(
        title="Replace broken air conditioner",
        action="Call HVAC repair service",
        priority="High",
        evidence="Dining area was uncomfortably hot",
        status="In Progress",
        db_path=temp_db,
    )
    id3 = create_action(
        title="Revise menu pricing for desserts",
        action="Update printed menus and POS system",
        priority="Low",
        evidence="Desserts are too pricey",
        status="Resolved",
        db_path=temp_db,
    )

    all_items = get_all_actions(db_path=temp_db)
    assert len(all_items) == 3

    open_items = get_all_actions(status="Open", db_path=temp_db)
    assert len(open_items) == 1
    assert open_items[0]["id"] == id1

    high_items = get_all_actions(priority="High", db_path=temp_db)
    assert len(high_items) == 1
    assert high_items[0]["id"] == id2

    search_hvac = get_all_actions(search_query="HVAC", db_path=temp_db)
    assert len(search_hvac) == 1
    assert search_hvac[0]["id"] == id2


def test_update_action(temp_db: Path):
    """Verify full update of an action record."""
    action_id = create_action(
        title="Original Title",
        action="Original Action",
        priority="Low",
        status="Open",
        db_path=temp_db,
    )

    success = update_action(
        action_id=action_id,
        title="Updated Title",
        action="Updated Action",
        priority="High",
        status="In Progress",
        evidence="Updated evidence",
        notes="In progress note",
        db_path=temp_db,
    )
    assert success is True

    updated = get_action_by_id(action_id, db_path=temp_db)
    assert updated["title"] == "Updated Title"
    assert updated["action"] == "Updated Action"
    assert updated["priority"] == "High"
    assert updated["status"] == "In Progress"
    assert updated["evidence"] == "Updated evidence"
    assert updated["notes"] == "In progress note"


def test_update_action_status_and_notes(temp_db: Path):
    """Verify quick status and notes update."""
    action_id = create_action(
        title="Clean kitchen exhaust",
        action="Hire exhaust cleaning contractor",
        priority="Medium",
        status="Open",
        db_path=temp_db,
    )

    ok = update_action_status_and_notes(
        action_id, status="Resolved", notes="Completed on Monday", db_path=temp_db
    )
    assert ok is True

    item = get_action_by_id(action_id, db_path=temp_db)
    assert item["status"] == "Resolved"
    assert item["notes"] == "Completed on Monday"


def test_delete_action(temp_db: Path):
    """Verify deletion removes the record."""
    action_id = create_action(
        title="Temporary action",
        action="Will be removed",
        priority="Low",
        db_path=temp_db,
    )
    assert get_action_by_id(action_id, db_path=temp_db) is not None

    deleted = delete_action(action_id, db_path=temp_db)
    assert deleted is True
    assert get_action_by_id(action_id, db_path=temp_db) is None

    # Deleting non-existent returns False
    assert delete_action(9999, db_path=temp_db) is False


def test_get_action_statistics(temp_db: Path):
    """Verify statistical aggregation across statuses and priority."""
    create_action(title="A1", action="Act 1", priority="High", status="Open", db_path=temp_db)
    create_action(title="A2", action="Act 2", priority="Medium", status="In Progress", db_path=temp_db)
    create_action(title="A3", action="Act 3", priority="Low", status="Resolved", db_path=temp_db)
    create_action(title="A4", action="Act 4", priority="High", status="Resolved", db_path=temp_db)

    stats = get_action_statistics(db_path=temp_db)
    assert stats["total"] == 4
    assert stats["open"] == 1
    assert stats["in_progress"] == 1
    assert stats["resolved"] == 2
    assert stats["high_priority"] == 2


def test_persistence_across_connections(temp_db: Path):
    """Verify SQLite persistence remains intact when opening a fresh connection."""
    action_id = create_action(
        title="Persistent Action",
        action="Should survive restart",
        priority="High",
        db_path=temp_db,
    )

    # Re-fetch from the same file path (simulating app restart)
    fetched = get_action_by_id(action_id, db_path=temp_db)
    assert fetched is not None
    assert fetched["title"] == "Persistent Action"


def test_clear_ai_recommendation_actions_preserves_manual_actions(temp_db: Path):
    """Verify clear_ai_recommendation_actions removes AI recommendations but preserves manual actions."""
    # 1. Create a manual user action
    manual_id = create_action(
        title="Manual Audit",
        action="Conduct manager walkthrough",
        priority="High",
        db_path=temp_db,
        source="manual",
    )

    # 2. Create an AI recommendation action
    rec_id = create_action(
        title="Kitchen Prep",
        action="Pre-cut ingredients before rush",
        priority="Medium",
        db_path=temp_db,
        source="ai_recommendation",
    )

    # Both actions exist
    all_acts = get_all_actions(db_path=temp_db)
    assert len(all_acts) == 2

    # Clear AI recommendations (simulating new dataset upload or reset)
    deleted_cnt = clear_ai_recommendation_actions(db_path=temp_db)
    assert deleted_cnt == 1

    # Only manual action remains
    remaining = get_all_actions(db_path=temp_db)
    assert len(remaining) == 1
    assert remaining[0]["id"] == manual_id
    assert remaining[0]["title"] == "Manual Audit"
    assert remaining[0]["source"] == "manual"

