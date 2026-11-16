from datetime import datetime, timedelta, timezone

import database


class MemoryQuery:
    def __init__(self, table):
        self.table = table
        self.operation = "select"
        self.filters = {}
        self.less_than = None
        self.payload = None

    def select(self, _columns):
        self.operation = "select"
        return self

    def upsert(self, payload, on_conflict=None):
        self.operation = "upsert"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def lt(self, column, value):
        self.less_than = (column, value)
        return self

    def limit(self, _count):
        return self

    def execute(self):
        if self.operation == "upsert":
            self.table.rows[self.payload["client_id"]] = self.payload
            return type("Response", (), {"data": [self.payload]})()
        matches = [
            row for row in self.table.rows.values()
            if all(row.get(key) == value for key, value in self.filters.items())
        ]
        if self.less_than:
            column, bound = self.less_than
            matches = [row for row in matches if row[column] < bound]
        if self.operation == "delete":
            for row in matches:
                self.table.rows.pop(row["client_id"], None)
        return type("Response", (), {"data": matches})()


class MemoryTable:
    def __init__(self):
        self.rows = {}

    def table(self, _name):
        return MemoryQuery(self)


def test_active_session_can_be_retrieved_after_store_reinitialization(monkeypatch):
    persistent_table = MemoryTable()
    monkeypatch.setattr(database, "_client", lambda: persistent_table)
    state = {"question_count": 2, "chat_history": [{"role": "coach", "text": "Next?"}]}

    database.save_active_interview("user-1", "session-1", state)
    restored = database.get_active_interview("user-1")

    assert restored["session_id"] == "session-1"
    assert restored["question_count"] == 2
    assert restored["chat_history"] == state["chat_history"]
    assert persistent_table.rows["user-1"]["updated_at"]


def test_expired_session_is_deleted_on_retrieval(monkeypatch):
    persistent_table = MemoryTable()
    monkeypatch.setattr(database, "_client", lambda: persistent_table)
    database.save_active_interview("user-1", "session-1", {"question_count": 1})
    persistent_table.rows["user-1"]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()

    assert database.get_active_interview("user-1") is None
    assert "user-1" not in persistent_table.rows


def test_cleanup_removes_all_expired_sessions(monkeypatch):
    persistent_table = MemoryTable()
    monkeypatch.setattr(database, "_client", lambda: persistent_table)
    database.save_active_interview("user-1", "session-1", {})
    persistent_table.rows["user-1"]["expires_at"] = "2000-01-01T00:00:00+00:00"

    database.cleanup_expired_active_interviews()

    assert persistent_table.rows == {}
