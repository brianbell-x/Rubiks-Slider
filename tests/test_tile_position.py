"""Tests for tile position queries."""

import pytest
from core.puzzle import Puzzle


class TestGetTilePosition:
    """Tests for get_tile_position method."""

    def test_tile_1_position_solved(self, puzzle_3x3):
        """Test tile 1 position in solved state."""
        pos = puzzle_3x3.get_tile_position(1)
        assert pos == (1, 1)  # R1C1

    def test_tile_5_position_solved(self, puzzle_3x3):
        """Test tile 5 (center) position in solved state."""
        pos = puzzle_3x3.get_tile_position(5)
        assert pos == (2, 2)  # R2C2

    def test_tile_9_position_solved(self, puzzle_3x3):
        """Test tile 9 (last) position in solved state."""
        pos = puzzle_3x3.get_tile_position(9)
        assert pos == (3, 3)  # R3C3

    def test_all_tiles_3x3(self, puzzle_3x3):
        """Test all tile positions in 3x3 solved state."""
        expected = {
            1: (1, 1), 2: (1, 2), 3: (1, 3),
            4: (2, 1), 5: (2, 2), 6: (2, 3),
            7: (3, 1), 8: (3, 2), 9: (3, 3)
        }
        for tile, expected_pos in expected.items():
            assert puzzle_3x3.get_tile_position(tile) == expected_pos

    def test_all_tiles_2x2(self, puzzle_2x2):
        """Test all tile positions in 2x2 solved state."""
        expected = {
            1: (1, 1), 2: (1, 2),
            3: (2, 1), 4: (2, 2)
        }
        for tile, expected_pos in expected.items():
            assert puzzle_2x2.get_tile_position(tile) == expected_pos

    def test_nonexistent_tile_returns_none(self, puzzle_3x3):
        """Test that looking for nonexistent tile returns None."""
        pos = puzzle_3x3.get_tile_position(10)
        assert pos is None

    def test_zero_tile_returns_none(self, puzzle_3x3):
        """Test that looking for tile 0 returns None."""
        pos = puzzle_3x3.get_tile_position(0)
        assert pos is None

    def test_negative_tile_returns_none(self, puzzle_3x3):
        """Test that looking for negative tile returns None."""
        pos = puzzle_3x3.get_tile_position(-1)
        assert pos is None


class TestTilePositionAfterMoves:
    """Tests for tile positions after moves."""

    def test_tile_position_after_row_left(self, puzzle_3x3):
        """Test tile positions after row left shift."""
        # Initial: [1,2,3], [4,5,6], [7,8,9]
        puzzle_3x3._shift_row(0, "left")
        # After: [2,3,1], [4,5,6], [7,8,9]

        assert puzzle_3x3.get_tile_position(1) == (1, 3)  # Was C1, now C3
        assert puzzle_3x3.get_tile_position(2) == (1, 1)  # Was C2, now C1
        assert puzzle_3x3.get_tile_position(3) == (1, 2)  # Was C3, now C2

    def test_tile_position_after_row_right(self, puzzle_3x3):
        """Test tile positions after row right shift."""
        puzzle_3x3._shift_row(0, "right")
        # After: [3,1,2]

        assert puzzle_3x3.get_tile_position(1) == (1, 2)
        assert puzzle_3x3.get_tile_position(2) == (1, 3)
        assert puzzle_3x3.get_tile_position(3) == (1, 1)

    def test_tile_position_after_column_up(self, puzzle_3x3):
        """Test tile positions after column up shift."""
        # Column 0: 1,4,7 -> 4,7,1
        puzzle_3x3._shift_column(0, "up")

        assert puzzle_3x3.get_tile_position(1) == (3, 1)  # Wrapped to bottom
        assert puzzle_3x3.get_tile_position(4) == (1, 1)  # Moved up
        assert puzzle_3x3.get_tile_position(7) == (2, 1)  # Moved up

    def test_tile_position_after_column_down(self, puzzle_3x3):
        """Test tile positions after column down shift."""
        # Column 0: 1,4,7 -> 7,1,4
        puzzle_3x3._shift_column(0, "down")

        assert puzzle_3x3.get_tile_position(1) == (2, 1)  # Moved down
        assert puzzle_3x3.get_tile_position(4) == (3, 1)  # Moved down
        assert puzzle_3x3.get_tile_position(7) == (1, 1)  # Wrapped to top

    def test_tile_position_after_multiple_moves(self, puzzle_3x3):
        """Test tile position tracking through multiple moves."""
        # Track tile 5 through several moves
        # Start: R2C2

        puzzle_3x3._shift_row(1, "left")  # Row 2 left: [5,6,4]
        assert puzzle_3x3.get_tile_position(5) == (2, 1)

        puzzle_3x3._shift_column(0, "up")  # Col 1 up
        # Col 0: 1,5,7 -> 5,7,1
        assert puzzle_3x3.get_tile_position(5) == (1, 1)

        puzzle_3x3._shift_row(0, "right")  # Row 1 right
        # Row 0: 5,2,3 -> 3,5,2
        assert puzzle_3x3.get_tile_position(5) == (1, 2)


class TestTilePositionOnLargerGrids:
    """Tests for tile positions on larger grids."""

    def test_tile_positions_4x4(self, puzzle_4x4):
        """Test corner tile positions in 4x4."""
        assert puzzle_4x4.get_tile_position(1) == (1, 1)
        assert puzzle_4x4.get_tile_position(4) == (1, 4)
        assert puzzle_4x4.get_tile_position(13) == (4, 1)
        assert puzzle_4x4.get_tile_position(16) == (4, 4)

    def test_tile_positions_6x6(self, puzzle_6x6):
        """Test tile positions in 6x6."""
        # First row
        assert puzzle_6x6.get_tile_position(1) == (1, 1)
        assert puzzle_6x6.get_tile_position(6) == (1, 6)
        # Last row
        assert puzzle_6x6.get_tile_position(31) == (6, 1)
        assert puzzle_6x6.get_tile_position(36) == (6, 6)
        # Center area
        assert puzzle_6x6.get_tile_position(15) == (3, 3)

    def test_double_digit_tiles(self, puzzle_4x4):
        """Test positions of double-digit tiles."""
        assert puzzle_4x4.get_tile_position(10) == (3, 2)
        assert puzzle_4x4.get_tile_position(11) == (3, 3)
        assert puzzle_4x4.get_tile_position(12) == (3, 4)


class TestTilePositionReturnFormat:
    """Tests for the return format of get_tile_position."""

    def test_returns_tuple(self, puzzle_3x3):
        """Test that get_tile_position returns a tuple."""
        pos = puzzle_3x3.get_tile_position(1)
        assert isinstance(pos, tuple)

    def test_tuple_has_two_elements(self, puzzle_3x3):
        """Test that returned tuple has exactly 2 elements."""
        pos = puzzle_3x3.get_tile_position(1)
        assert len(pos) == 2

    def test_tuple_elements_are_integers(self, puzzle_3x3):
        """Test that tuple elements are integers."""
        pos = puzzle_3x3.get_tile_position(1)
        assert isinstance(pos[0], int)
        assert isinstance(pos[1], int)

    def test_position_is_1_indexed(self, puzzle_3x3):
        """Test that positions are 1-indexed."""
        # Tile at board[0][0] should be position (1,1), not (0,0)
        pos = puzzle_3x3.get_tile_position(1)
        assert pos[0] >= 1
        assert pos[1] >= 1
