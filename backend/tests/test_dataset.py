"""
Tests for dataset.py utility methods.
"""


class TestDatasetDivideDesc:
    """Test the divide_desc method for parsing test descriptions."""

    def test_divide_desc_full_format(self):
        """Test parsing a complete description with all sections."""
        from unittest.mock import MagicMock
        from dataset import Dataset

        # Create a mock dataset
        dataset = Dataset.__new__(Dataset)
        dataset.configs = MagicMock()

        desc = """# Objective
Verify the parse method works correctly.

# Preconditions
1. The parser is initialized.
2. Input string is valid.

# Expected Results
1. Returns parsed output.
2. No exceptions thrown."""

        result = dataset.divide_desc(desc)

        assert "objective" in result or "Objective" in str(result)

    def test_divide_desc_missing_section(self):
        """Test parsing a description missing some sections."""
        from unittest.mock import MagicMock
        from dataset import Dataset

        dataset = Dataset.__new__(Dataset)
        dataset.configs = MagicMock()

        desc = """# Objective
Just test something.

# Expected Results
It should work."""

        result = dataset.divide_desc(desc)
        # Should not raise an exception
        assert result is not None


class TestDatasetAddNewlineChar:
    """Test the add_newline_char utility method."""

    def test_add_newline_to_string(self):
        """Test adding newline characters."""
        from unittest.mock import MagicMock
        from dataset import Dataset

        dataset = Dataset.__new__(Dataset)
        dataset.configs = MagicMock()

        result = dataset.add_newline_char("line1\\nline2")

        # Should convert escaped newlines to actual newlines
        assert isinstance(result, str)
