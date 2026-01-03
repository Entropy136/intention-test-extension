"""
Tests for backend/server.py session utilities.
"""

from __future__ import annotations

import json


class DummyHandler:
    def __init__(self):
        self.written: list[bytes] = []

    def write_single_line(self, data: bytes):
        self.written.append(data)


def _minimal_raw_data():
    return {
        "target_focal_method": "test",
        "target_focal_file": "Test.java",
        "test_desc": "desc",
        "project_path": "/path",
        "focal_file_path": "/path/Test.java",
    }


class TestModelQuerySession:
    def test_required_fields(self):
        import server

        assert "target_focal_method" in server.ModelQuerySession.required_fields
        assert "test_desc" in server.ModelQuerySession.required_fields
        assert len(server.ModelQuerySession.required_fields) == 5

    def test_request_stop_and_should_stop(self):
        import server

        session = server.ModelQuerySession("sess-1", _minimal_raw_data(), DummyHandler())

        assert session.should_stop() is False
        session.request_stop()
        assert session.should_stop() is True

    def test_write_start_message(self):
        import server

        handler = DummyHandler()
        session = server.ModelQuerySession("sess-2", _minimal_raw_data(), handler)
        session.write_start_message()

        parsed = json.loads(handler.written[0].decode("utf-8"))
        assert parsed["type"] == "status"
        assert parsed["data"]["status"] == "start"
        assert parsed["data"]["message"]["session_id"] == "sess-2"

    def test_write_finish_message(self):
        import server

        handler = DummyHandler()
        session = server.ModelQuerySession("sess-3", _minimal_raw_data(), handler)
        session.write_finish_message()

        parsed = json.loads(handler.written[0].decode("utf-8"))
        assert parsed["type"] == "status"
        assert parsed["data"]["status"] == "finish"
        assert parsed["data"]["message"]["session_id"] == "sess-3"

    def test_update_messages(self):
        import server

        handler = DummyHandler()
        session = server.ModelQuerySession("sess-4", _minimal_raw_data(), handler)

        messages = [{"role": "assistant", "content": "Hello"}]
        session.update_messages(messages)

        parsed = json.loads(handler.written[0].decode("utf-8"))
        assert parsed["type"] == "msg"
        assert parsed["data"]["session_id"] == "sess-4"
        assert parsed["data"]["messages"] == messages


class TestAssignToSession:
    def test_assign_registers_session(self):
        import server

        handler = DummyHandler()
        query_text = json.dumps({"type": "query", "data": _minimal_raw_data()})
        session = server.assign_to_session(query_text, handler)

        assert session is not None
        with server.sessions_lock:
            assert session.session_id in server.sessions
            server.sessions.clear()
