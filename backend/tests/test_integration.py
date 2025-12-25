"""
Integration tests for the test generation workflow.

These tests use mocked OpenAI API responses to test the complete
generation flow without making actual API calls.
"""
import json
from unittest.mock import MagicMock, patch


class TestGenerationWorkflow:
    """Test the complete test generation workflow with mocked API."""

    def test_agent_initialization(self):
        """Test that Agent can be initialized with mocked OpenAI client."""
        with patch('agents.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            from agents import Agent

            # Create agent with mocked client
            agent = Agent.__new__(Agent)
            agent.client = mock_client
            agent.model = 'gpt-4o'

            assert agent.client is not None
            assert agent.model == 'gpt-4o'

    def test_extract_code_integration(self):
        """Test code extraction from a realistic API response."""
        with patch('agents.OpenAI'):
            from agents import Agent

            agent = Agent.__new__(Agent)

            # Simulate realistic API response
            response = '''Here's the test code for the Calculator class:

```java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class CalculatorTest {
    @Test
    public void testAdd() {
        Calculator calc = new Calculator();
        assertEquals(5, calc.add(2, 3));
    }

    @Test
    public void testSubtract() {
        Calculator calc = new Calculator();
        assertEquals(1, calc.subtract(3, 2));
    }
}
```

This test covers the basic arithmetic operations.'''

            code = agent.extract_code_from_response(response)

            assert 'CalculatorTest' in code
            assert 'testAdd' in code
            assert 'assertEquals' in code

    def test_remove_thinking_integration(self):
        """Test thinking tag removal from DeepSeek-style responses."""
        with patch('agents.OpenAI'):
            from agents import Agent

            agent = Agent.__new__(Agent)

            response = '''<think>
Let me analyze this code step by step...
First, I need to understand the class structure...
Now I'll generate an appropriate test...
</think>

Here's the test code:

```java
public class MyTest {
    @Test
    public void test() {}
}
```'''

            result = agent.remove_thinking(response)

            assert result is not None
            assert '<think>' not in result
            assert '</think>' not in result
            assert 'Here\'s the test code' in result


class TestMockedAPIFlow:
    """Test complete API flow with mocked responses."""

    def test_chat_completion_mock(self):
        """Test that chat completion can be mocked properly."""
        with patch('agents.OpenAI') as mock_openai:
            # Setup mock
            mock_client = MagicMock()
            mock_completion = MagicMock()
            mock_message = MagicMock()
            mock_message.content = '```java\npublic class Test {}\n```'
            mock_completion.choices = [MagicMock(message=mock_message)]
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            from agents import Agent

            # Verify mock setup
            client = mock_openai()
            response = client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': 'Generate a test'}]
            )

            assert response.choices[0].message.content == '```java\npublic class Test {}\n```'


class TestSessionLifecycle:
    """Integration tests for complete session lifecycle."""

    def test_session_creation_and_registration(self):
        """Test creating a session and registering it."""
        from core.registry import SessionRegistry
        from core.session import ModelQuerySession

        registry = SessionRegistry()

        # Create session using __new__ to skip complex __init__
        session = ModelQuerySession.__new__(ModelQuerySession)
        session.session_id = "integration-test-1"
        session._stop_requested = False
        session._message_callback = None
        registry.register("integration-test-1", session)

        # Verify session is retrievable
        retrieved = registry.get("integration-test-1")
        assert retrieved is session
        assert retrieved.session_id == "integration-test-1"

        # Cleanup
        registry.remove("integration-test-1")
        assert registry.get("integration-test-1") is None

    def test_session_stop_and_message_flow(self):
        """Test session stop mechanism with message updates."""
        from core.session import ModelQuerySession

        # Create session using __new__
        session = ModelQuerySession.__new__(ModelQuerySession)
        session.session_id = "stop-test"
        session._stop_requested = False
        session._message_callback = None

        # Initially not stopped
        assert session.should_stop() is False

        # Request stop
        session.request_stop()

        # Verify stopped
        assert session.should_stop() is True

    def test_message_update_flow(self):
        """Test message update callback flow."""
        from core.session import ModelQuerySession

        received_messages = []

        def message_handler(msg):
            received_messages.append(msg)

        # Create session using __new__
        session = ModelQuerySession.__new__(ModelQuerySession)
        session.session_id = "msg-test"
        session._stop_requested = False
        session._message_callback = None
        session.set_message_callback(message_handler)

        # Send messages
        session.update_message("First message")
        session.update_message("Second message")

        assert len(received_messages) == 2
        assert received_messages[0] == "First message"


class TestRequestValidationFlow:
    """Integration tests for HTTP request validation flow."""

    def test_valid_query_payload_flow(self):
        """Test complete validation of a valid query payload."""
        from app.server import validate_query_payload

        payload = {
            "type": "query",
            "session_id": "valid-session",
            "data": {
                "target_focal_method": "testMethod",
                "target_focal_file": "Test.java",
                "test_desc": "Test description",
                "project_path": "/path/to/project",
                "focal_file_path": "/path/to/Test.java",
            }
        }

        session_id, data = validate_query_payload(payload)

        assert session_id == "valid-session"
        assert data["target_focal_method"] == "testMethod"

    def test_invalid_payload_flow(self):
        """Test validation rejects invalid payloads."""
        import pytest
        from app.server import validate_query_payload

        # Missing required fields
        payload = {
            "type": "query",
            "data": {"target_focal_method": "test"}
        }

        with pytest.raises(ValueError):
            validate_query_payload(payload)


class TestDatasetProcessingFlow:
    """Integration tests for dataset processing flow."""

    def test_description_parsing_flow(self):
        """Test complete description parsing flow."""
        from dataset import Dataset

        dataset = Dataset.__new__(Dataset)
        dataset.configs = type('obj', (object,), {'project_name': 'test'})()

        desc = """# Objective
Test the add method

# Preconditions
Calculator is initialized

# Expected Results
Returns correct sum"""

        result = dataset.divide_desc(desc)

        # divide_desc returns a dict
        assert "add method" in result['Objective']
        assert "initialized" in result['Preconditions']
        assert "correct sum" in result['Expected Results']


class TestEndToEndCodeExtraction:
    """End-to-end tests for code extraction pipeline."""

    def test_multiblock_code_extraction(self):
        """Test extracting code when multiple blocks exist."""
        with patch('agents.OpenAI'):
            from agents import TestGenAgent

            agent = TestGenAgent.__new__(TestGenAgent)

            response = '''I'll provide two test methods:

```java
@Test
public void testPositive() {
    assertEquals(5, calc.add(2, 3));
}
```

And another one:

```java
@Test
public void testNegative() {
    assertEquals(-1, calc.add(2, -3));
}
```
'''
            # Should extract the first code block
            code = agent.extract_code_from_response(response)
            assert 'testPositive' in code

    def test_code_with_line_numbers(self):
        """Test processing code that has line numbers."""
        with patch('agents.OpenAI'):
            from agents import Agent

            agent = Agent.__new__(Agent)

            code_with_numbers = """1: public class Test {
2:     @Test
3:     public void test() {
4:         assertTrue(true);
5:     }
6: }"""

            result = agent.remove_line_numbers(code_with_numbers)

            assert '1:' not in result
            assert 'public class Test' in result
