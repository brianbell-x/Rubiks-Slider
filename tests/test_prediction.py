"""Tests for prediction validation."""

import pytest
from core.puzzle import Puzzle


class TestValidatePrediction:
    """Tests for validate_prediction method."""

    def test_correct_prediction_tile_1(self, puzzle_3x3):
        """Test correct prediction for tile 1 at R1C1."""
        result = puzzle_3x3.validate_prediction(1, "R1C1")
        assert result is True

    def test_correct_prediction_tile_5(self, puzzle_3x3):
        """Test correct prediction for tile 5 at R2C2."""
        result = puzzle_3x3.validate_prediction(5, "R2C2")
        assert result is True

    def test_correct_prediction_tile_9(self, puzzle_3x3):
        """Test correct prediction for tile 9 at R3C3."""
        result = puzzle_3x3.validate_prediction(9, "R3C3")
        assert result is True

    def test_incorrect_prediction(self, puzzle_3x3):
        """Test incorrect prediction."""
        result = puzzle_3x3.validate_prediction(1, "R2C2")
        assert result is False

    def test_prediction_after_row_move(self, puzzle_3x3):
        """Test prediction validation after row move."""
        puzzle_3x3._shift_row(0, "left")
        # Tile 1 moved from R1C1 to R1C3
        assert puzzle_3x3.validate_prediction(1, "R1C3") is True
        assert puzzle_3x3.validate_prediction(1, "R1C1") is False

    def test_prediction_after_column_move(self, puzzle_3x3):
        """Test prediction validation after column move."""
        puzzle_3x3._shift_column(0, "up")
        # Tile 1 moved from R1C1 to R3C1
        assert puzzle_3x3.validate_prediction(1, "R3C1") is True
        assert puzzle_3x3.validate_prediction(1, "R1C1") is False


class TestPredictionFormat:
    """Tests for prediction format validation."""

    def test_valid_format_single_digit(self, puzzle_3x3):
        """Test valid format with single digits."""
        assert puzzle_3x3.validate_prediction(1, "R1C1") is True

    def test_valid_format_double_digit(self, puzzle_4x4):
        """Test valid format with double digits."""
        # Tile 10 is at (3, 2) in 4x4
        # Row 3, Col 2 -> R3C2
        result = puzzle_4x4.validate_prediction(10, "R3C2")
        assert result is True

    def test_invalid_format_lowercase(self, puzzle_3x3):
        """Test that lowercase format is invalid."""
        result = puzzle_3x3.validate_prediction(1, "r1c1")
        assert result is False

    def test_invalid_format_missing_r(self, puzzle_3x3):
        """Test format without R prefix."""
        result = puzzle_3x3.validate_prediction(1, "1C1")
        assert result is False

    def test_invalid_format_missing_c(self, puzzle_3x3):
        """Test format without C prefix."""
        result = puzzle_3x3.validate_prediction(1, "R11")
        assert result is False

    def test_invalid_format_with_spaces(self, puzzle_3x3):
        """Test format with spaces."""
        result = puzzle_3x3.validate_prediction(1, "R1 C1")
        assert result is False

    def test_invalid_format_empty_string(self, puzzle_3x3):
        """Test empty string prediction."""
        result = puzzle_3x3.validate_prediction(1, "")
        assert result is False

    def test_invalid_format_random_text(self, puzzle_3x3):
        """Test random text prediction."""
        result = puzzle_3x3.validate_prediction(1, "invalid")
        assert result is False


class TestPredictionWithNonexistentTile:
    """Tests for predictions with tiles that don't exist."""

    def test_nonexistent_tile_returns_false(self, puzzle_3x3):
        """Test that predicting for nonexistent tile returns False."""
        result = puzzle_3x3.validate_prediction(10, "R1C1")
        assert result is False

    def test_zero_tile_returns_false(self, puzzle_3x3):
        """Test that predicting for tile 0 returns False."""
        result = puzzle_3x3.validate_prediction(0, "R1C1")
        assert result is False

    def test_negative_tile_returns_false(self, puzzle_3x3):
        """Test that predicting for negative tile returns False."""
        result = puzzle_3x3.validate_prediction(-1, "R1C1")
        assert result is False


class TestPredictionOutOfBounds:
    """Tests for predictions with out-of-bounds positions."""

    def test_row_out_of_bounds(self, puzzle_3x3):
        """Test prediction with row > grid size."""
        # Even if format is valid, position doesn't match
        result = puzzle_3x3.validate_prediction(1, "R4C1")
        assert result is False

    def test_column_out_of_bounds(self, puzzle_3x3):
        """Test prediction with column > grid size."""
        result = puzzle_3x3.validate_prediction(1, "R1C4")
        assert result is False

    def test_zero_row_index(self, puzzle_3x3):
        """Test prediction with row 0."""
        result = puzzle_3x3.validate_prediction(1, "R0C1")
        assert result is False

    def test_zero_column_index(self, puzzle_3x3):
        """Test prediction with column 0."""
        result = puzzle_3x3.validate_prediction(1, "R1C0")
        assert result is False


class TestPredictionAfterMultipleMoves:
    """Tests for predictions after complex move sequences."""

    def test_predict_after_three_moves(self, puzzle_3x3):
        """Test prediction after a sequence of moves."""
        # Track tile 5
        # Start: R2C2
        puzzle_3x3._shift_row(1, "left")  # Row 2 left: 5 moves to R2C1
        puzzle_3x3._shift_column(0, "up")  # Col 1 up: 5 moves to R1C1
        puzzle_3x3._shift_row(0, "right")  # Row 1 right: 5 moves to R1C2

        assert puzzle_3x3.validate_prediction(5, "R1C2") is True

    def test_predict_multiple_tiles(self, puzzle_3x3):
        """Test predicting multiple tiles after moves."""
        puzzle_3x3._shift_row(0, "left")
        # Row 1: [2,3,1]

        assert puzzle_3x3.validate_prediction(1, "R1C3") is True
        assert puzzle_3x3.validate_prediction(2, "R1C1") is True
        assert puzzle_3x3.validate_prediction(3, "R1C2") is True
        # Unchanged tiles
        assert puzzle_3x3.validate_prediction(5, "R2C2") is True


class TestPredictionOnLargerGrids:
    """Tests for predictions on larger grids."""

    def test_prediction_4x4(self, puzzle_4x4):
        """Test predictions on 4x4 grid."""
        assert puzzle_4x4.validate_prediction(1, "R1C1") is True
        assert puzzle_4x4.validate_prediction(16, "R4C4") is True
        assert puzzle_4x4.validate_prediction(8, "R2C4") is True

    def test_prediction_6x6(self, puzzle_6x6):
        """Test predictions on 6x6 grid."""
        assert puzzle_6x6.validate_prediction(1, "R1C1") is True
        assert puzzle_6x6.validate_prediction(36, "R6C6") is True
        assert puzzle_6x6.validate_prediction(15, "R3C3") is True

    def test_prediction_with_double_digit_position(self):
        """Test prediction with double digit row/column."""
        puzzle = Puzzle(size=10, auto_shuffle=False)
        # Tile 100 at R10C10
        assert puzzle.validate_prediction(100, "R10C10") is True
        # Tile 11 at R2C1
        assert puzzle.validate_prediction(11, "R2C1") is True
