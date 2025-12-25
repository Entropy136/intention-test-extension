"""
Tests for core/registry.py and core/session.py.
"""
from unittest.mock import MagicMock


class TestSessionRegistry:
    """Test the SessionRegistry thread-safe session management."""

    def test_register_and_get(self):
        """Test registering and retrieving a session."""
        from core.registry import SessionRegistry

        registry = SessionRegistry()
        mock_session = MagicMock()
        mock_session.session_id = "test-123"

        registry.register(mock_session)
        result = registry.get("test-123")

        assert result is mock_session

    def test_get_nonexistent_returns_none(self):
        """Test getting a non-existent session returns None."""
        from core.registry import SessionRegistry

        registry = SessionRegistry()
        result = registry.get("nonexistent")

        assert result is None

    def test_remove_session(self):
        """Test removing a session."""
        from core.registry import SessionRegistry

        registry = SessionRegistry()
        mock_session = MagicMock()
        mock_session.session_id = "test-456"

        registry.register(mock_session)
        registry.remove("test-456")
        result = registry.get("test-456")

        assert result is None

    def test_list_active_ids(self):
        """Test listing all active session IDs."""
        from core.registry import SessionRegistry

        registry = SessionRegistry()
        for i in range(3):
            mock = MagicMock()
            mock.session_id = f"session-{i}"
            registry.register(mock)

        ids = registry.list_active_ids()

        assert len(ids) == 3
        assert "session-0" in ids
        assert "session-1" in ids
        assert "session-2" in ids

    def test_remove_nonexistent_does_not_raise(self):
        """Test removing a non-existent session doesn't raise."""
        from core.registry import SessionRegistry

        registry = SessionRegistry()
        # Should not raise
        registry.remove("nonexistent")


class TestModelQuerySession:
    """Test the ModelQuerySession class."""

    def test_required_fields(self):
        """Test that required_fields is defined correctly."""
        from core.session import ModelQuerySession

        assert "target_focal_method" in ModelQuerySession.required_fields
        assert "test_desc" in ModelQuerySession.required_fields
        assert len(ModelQuerySession.required_fields) == 5

    def test_request_stop_and_should_stop(self):
        """Test the cancellation mechanism."""
        from core.session import ModelQuerySession

        writer = MagicMock()
        executor = MagicMock()
        raw_data = {
            "target_focal_method": "test",
            "target_focal_file": "Test.java",
            "test_desc": "desc",
            "project_path": "/path",
            "focal_file_path": "/path/Test.java",
        }

        session = ModelQuerySession(
            session_id="sess-1",
            raw_data=raw_data,
            writer=writer,
            executor=executor,
            junit_version=4,
        )

        assert session.should_stop() is False
        session.request_stop()
        assert session.should_stop() is True

    def test_write_start_message(self):
        """Test writing start message."""
        from core.session import ModelQuerySession
        import json

        captured = []

        def writer(data):
            captured.append(data)

        raw_data = {
            "target_focal_method": "test",
            "target_focal_file": "Test.java",
            "test_desc": "desc",
            "project_path": "/path",
            "focal_file_path": "/path/Test.java",
        }

        session = ModelQuerySession(
            session_id="sess-2",
            raw_data=raw_data,
            writer=writer,
            executor=MagicMock(),
            junit_version=5,
        )

        session.write_start_message()

        assert len(captured) == 1
        parsed = json.loads(captured[0].decode())
        assert parsed["type"] == "status"
        assert parsed["data"]["status"] == "start"

    def test_write_finish_message(self):
        """Test writing finish message."""
        from core.session import ModelQuerySession
        import json

        captured = []

        def writer(data):
            captured.append(data)

        raw_data = {
            "target_focal_method": "test",
            "target_focal_file": "Test.java",
            "test_desc": "desc",
            "project_path": "/path",
            "focal_file_path": "/path/Test.java",
        }

        session = ModelQuerySession(
            session_id="sess-3",
            raw_data=raw_data,
            writer=writer,
            executor=MagicMock(),
            junit_version=4,
        )

        session.write_finish_message()

        assert len(captured) == 1
        parsed = json.loads(captured[0].decode())
        assert parsed["data"]["status"] == "finish"

    def test_update_messages(self):
        """Test updating and sending messages."""
        from core.session import ModelQuerySession
        import json

        captured = []

        def writer(data):
            captured.append(data)

        raw_data = {
            "target_focal_method": "test",
            "target_focal_file": "Test.java",
            "test_desc": "desc",
            "project_path": "/path",
            "focal_file_path": "/path/Test.java",
        }

        session = ModelQuerySession(
            session_id="sess-4",
            raw_data=raw_data,
            writer=writer,
            executor=MagicMock(),
            junit_version=4,
        )

        messages = [{"role": "assistant", "content": "Hello"}]
        session.update_messages(messages)

        assert session.messages == messages
        assert len(captured) == 1
        parsed = json.loads(captured[0].decode())
        assert parsed["type"] == "msg"
