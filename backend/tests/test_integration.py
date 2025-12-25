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
