"""Tests for benchmark response parsing functions."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from benchmark.runner import parse_moves, parse_prediction


class TestParseMoves:
    """Tests for parse_moves function."""

    def test_parse_single_move(self):
        """Test parsing a single move."""
        response = "<move>R1 L</move>"
        moves = parse_moves(response, 3)
        assert moves is not None
        assert len(moves) == 1
        assert moves[0]["type"] == "row"
        assert moves[0]["index"] == 1
        assert moves[0]["direction"] == "left"

    def test_parse_move_row_right(self):
        """Test parsing row right move."""
        response = "<move>R2 R</move>"
        moves = parse_moves(response, 3)
        assert moves[0]["direction"] == "right"

    def test_parse_move_column_up(self):
        """Test parsing column up move."""
        response = "<move>C1 U</move>"
        moves = parse_moves(response, 3)
        assert moves[0]["type"] == "column"
        assert moves[0]["direction"] == "up"

    def test_parse_move_column_down(self):
        """Test parsing column down move."""
        response = "<move>C3 D</move>"
        moves = parse_moves(response, 3)
        assert moves[0]["type"] == "column"
        assert moves[0]["direction"] == "down"

    def test_parse_multiple_moves_semicolon(self):
        """Test parsing multiple moves separated by semicolons."""
        response = "<move>R1 L; C2 U; R3 R</move>"
        moves = parse_moves(response, 3)
        assert moves is not None
        assert len(moves) == 3
        assert moves[0]["type"] == "row"
        assert moves[1]["type"] == "column"
        assert moves[2]["type"] == "row"

    def test_parse_multiple_moves_newline(self):
        """Test parsing multiple moves separated by newlines."""
        response = "<move>R1 L\nC2 U\nR3 R</move>"
        moves = parse_moves(response, 3)
        assert moves is not None
        assert len(moves) == 3

    def test_parse_moves_with_extra_text(self):
        """Test parsing moves from response with extra text."""
        response = "I'll move the row. <move>R1 L</move> That should help."
        moves = parse_moves(response, 3)
        assert moves is not None
        assert len(moves) == 1

    def test_parse_moves_lowercase_tags(self):
        """Test parsing with lowercase move tags."""
        response = "<move>R1 L</move>"
        moves = parse_moves(response, 3)
        assert moves is not None

    def test_parse_moves_no_tags(self):
        """Test parsing when no move tags present."""
        response = "I'll just move R1 L"
        moves = parse_moves(response, 3)
        assert moves is None

    def test_parse_moves_empty_tags(self):
        """Test parsing empty move tags."""
        response = "<move></move>"
        moves = parse_moves(response, 3)
        assert moves is None

    def test_parse_moves_invalid_move(self):
        """Test parsing invalid move format."""
        response = "<move>invalid move</move>"
        moves = parse_moves(response, 3)
        assert moves is None

    def test_parse_moves_out_of_bounds(self):
        """Test parsing move with index out of bounds."""
        response = "<move>R4 L</move>"  # 4 > 3
        moves = parse_moves(response, 3)
        assert moves is None

    def test_parse_moves_mixed_valid_invalid(self):
        """Test parsing when one move is invalid."""
        response = "<move>R1 L; R5 R</move>"  # R5 invalid for 3x3
        moves = parse_moves(response, 3)
        assert moves is None  # Whole thing should fail

    def test_parse_moves_whitespace(self):
        """Test parsing moves with extra whitespace."""
        response = "<move>  R1 L  ;  C2 U  </move>"
        moves = parse_moves(response, 3)
        assert moves is not None
        assert len(moves) == 2


class TestParsePrediction:
    """Tests for parse_prediction function."""

    def test_parse_valid_prediction(self):
        """Test parsing valid prediction."""
        response = "<prediction>R1C1</prediction>"
        pred = parse_prediction(response)
        assert pred == "R1C1"

    def test_parse_prediction_double_digit(self):
        """Test parsing prediction with double digits."""
        response = "<prediction>R10C10</prediction>"
        pred = parse_prediction(response)
        assert pred == "R10C10"

    def test_parse_prediction_with_text(self):
        """Test parsing prediction from response with extra text."""
        response = "The tile will be at <prediction>R2C3</prediction> after the move."
        pred = parse_prediction(response)
        assert pred == "R2C3"

    def test_parse_prediction_lowercase_tags(self):
        """Test parsing with lowercase prediction tags."""
        response = "<prediction>R1C1</prediction>"
        pred = parse_prediction(response)
        assert pred == "R1C1"

    def test_parse_prediction_no_tags(self):
        """Test parsing when no prediction tags present."""
        response = "The tile is at R1C1"
        pred = parse_prediction(response)
        assert pred is None

    def test_parse_prediction_empty_tags(self):
        """Test parsing empty prediction tags."""
        response = "<prediction></prediction>"
        pred = parse_prediction(response)
        assert pred is None

    def test_parse_prediction_invalid_format(self):
        """Test parsing invalid prediction format."""
        response = "<prediction>invalid</prediction>"
        pred = parse_prediction(response)
        assert pred is None

    def test_parse_prediction_lowercase_rc(self):
        """Test parsing lowercase r and c."""
        response = "<prediction>r1c1</prediction>"
        pred = parse_prediction(response)
        assert pred is None  # Must be uppercase

    def test_parse_prediction_with_spaces(self):
        """Test parsing prediction with spaces."""
        response = "<prediction>R1 C1</prediction>"
        pred = parse_prediction(response)
        assert pred is None

    def test_parse_prediction_with_whitespace_around(self):
        """Test parsing prediction with whitespace around value."""
        response = "<prediction>  R1C1  </prediction>"
        pred = parse_prediction(response)
        assert pred == "R1C1"  # Should strip whitespace


class TestParseMovesAndPredictionTogether:
    """Tests for parsing both moves and predictions from same response."""

    def test_parse_both_from_response(self):
        """Test parsing moves and prediction from same response."""
        response = """
        Let me make this move:
        <move>R1 L</move>

        The tile will end up at:
        <prediction>R1C3</prediction>
        """
        moves = parse_moves(response, 3)
        pred = parse_prediction(response)

        assert moves is not None
        assert len(moves) == 1
        assert pred == "R1C3"

    def test_parse_complex_response(self):
        """Test parsing from a complex model-like response."""
        response = """I'll make two moves to get closer to the solution.

<move>R1 L; C2 D</move>

After these moves, tile 5 will be at position <prediction>R3C2</prediction>.
"""
        moves = parse_moves(response, 3)
        pred = parse_prediction(response)

        assert moves is not None
        assert len(moves) == 2
        assert moves[0]["direction"] == "left"
        assert moves[1]["direction"] == "down"
        assert pred == "R3C2"

    def test_parse_response_with_only_moves(self):
        """Test parsing response with only moves, no prediction."""
        response = "<move>R1 L</move>"
        moves = parse_moves(response, 3)
        pred = parse_prediction(response)

        assert moves is not None
        assert pred is None

    def test_parse_response_with_only_prediction(self):
        """Test parsing response with only prediction, no moves."""
        response = "<prediction>R1C1</prediction>"
        moves = parse_moves(response, 3)
        pred = parse_prediction(response)

        assert moves is None
        assert pred == "R1C1"


class TestParseMovesCaseInsensitive:
    """Tests for case insensitivity in move parsing."""

    def test_lowercase_move_notation(self):
        """Test lowercase r and c in move notation."""
        response = "<move>r1 l</move>"
        moves = parse_moves(response, 3)
        assert moves is not None
        assert moves[0]["type"] == "row"

    def test_mixed_case_move_notation(self):
        """Test mixed case in move notation."""
        response = "<move>R1 l</move>"
        moves = parse_moves(response, 3)
        assert moves is not None

    def test_uppercase_direction(self):
        """Test uppercase direction letter."""
        response = "<move>R1 L</move>"
        moves = parse_moves(response, 3)
        assert moves is not None
        assert moves[0]["direction"] == "left"


class TestParseMovesBoundaryConditions:
    """Tests for boundary conditions in move parsing."""

    def test_parse_move_index_1(self):
        """Test parsing move with minimum valid index."""
        response = "<move>R1 L</move>"
        moves = parse_moves(response, 3)
        assert moves is not None

    def test_parse_move_max_index(self):
        """Test parsing move with maximum valid index."""
        response = "<move>R3 L</move>"
        moves = parse_moves(response, 3)
        assert moves is not None
        assert moves[0]["index"] == 3

    def test_parse_move_index_zero(self):
        """Test parsing move with index 0 (invalid)."""
        response = "<move>R0 L</move>"
        moves = parse_moves(response, 3)
        assert moves is None

    def test_parse_move_large_grid(self):
        """Test parsing moves for larger grid."""
        response = "<move>R10 L</move>"
        moves = parse_moves(response, 10)
        assert moves is not None
        assert moves[0]["index"] == 10

    def test_parse_multiple_moves_large_grid(self):
        """Test parsing multiple moves for larger grid."""
        response = "<move>R10 L; C5 U; R1 R</move>"
        moves = parse_moves(response, 10)
        assert moves is not None
        assert len(moves) == 3
