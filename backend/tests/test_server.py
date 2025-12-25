"""
Tests for app/server.py utility functions.
"""
import pytest


class TestValidateQueryPayload:
    """Test the validate_query_payload function."""

    def test_valid_payload(self):
        """Test a valid query payload."""
        from app.server import validate_query_payload

        payload = {
            "type": "query",
            "session_id": "test-session",
            "data": {
                "target_focal_method": "test",
                "target_focal_file": "Test.java",
                "test_desc": "description",
                "project_path": "/path",
                "focal_file_path": "/path/Test.java",
            },
        }

        session_id, data = validate_query_payload(payload)

        assert session_id == "test-session"
        assert data["target_focal_method"] == "test"

    def test_invalid_type_raises(self):
        """Test that invalid type raises ValueError."""
        from app.server import validate_query_payload

        payload = {"type": "invalid", "data": {}}

        with pytest.raises(ValueError, match="Unsupported request type"):
            validate_query_payload(payload)

    def test_missing_data_raises(self):
        """Test that missing data raises ValueError."""
        from app.server import validate_query_payload

        payload = {"type": "query", "data": "not_a_dict"}

        with pytest.raises(ValueError, match="must be a JSON object"):
            validate_query_payload(payload)

    def test_missing_required_fields_raises(self):
        """Test that missing required fields raises ValueError."""
        from app.server import validate_query_payload

        payload = {
            "type": "query",
            "data": {"target_focal_method": "test"},
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            validate_query_payload(payload)

    def test_generates_session_id_when_missing(self):
        """Test that session_id is generated when not provided."""
        from app.server import validate_query_payload

        payload = {
            "type": "query",
            "data": {
                "target_focal_method": "test",
                "target_focal_file": "Test.java",
                "test_desc": "description",
                "project_path": "/path",
                "focal_file_path": "/path/Test.java",
            },
        }

        session_id, _ = validate_query_payload(payload)

        assert session_id is not None
        assert len(session_id) > 0


class TestResponseStream:
    """Test the ResponseStream class."""

    def test_call_writes_data(self):
        """Test that calling the stream writes data."""
        from app.server import ResponseStream
        from unittest.mock import MagicMock
        from io import BytesIO

        handler = MagicMock()
        handler.wfile = BytesIO()

        stream = ResponseStream(handler)
        stream(b"test data")

        handler.wfile.seek(0)
        assert handler.wfile.read() == b"test data\n"


class TestGenerateSessionId:
    """Test the _generate_session_id function."""

    def test_generates_unique_ids(self):
        """Test that generated IDs are unique."""
        from app.server import _generate_session_id

        ids = [_generate_session_id() for _ in range(10)]

        assert len(set(ids)) == 10  # All unique

    def test_generates_hex_string(self):
        """Test that generated ID is a hex string."""
        from app.server import _generate_session_id

        session_id = _generate_session_id()

        assert len(session_id) == 32  # UUID hex is 32 chars
        assert all(c in "0123456789abcdef" for c in session_id)
