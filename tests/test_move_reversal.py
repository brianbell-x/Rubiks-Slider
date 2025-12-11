"""Tests for move reversal logic."""

import pytest
import json
from core.puzzle import Puzzle


class TestReverseMove:
    """Tests for _reverse_move static method."""

    def test_reverse_left_to_right(self):
        """Test reversing left direction to right."""
        move = {"type": "row", "index": 1, "direction": "left"}
        reversed_move = Puzzle._reverse_move(move)
        assert reversed_move["direction"] == "right"
        assert reversed_move["type"] == "row"
        assert reversed_move["index"] == 1

    def test_reverse_right_to_left(self):
        """Test reversing right direction to left."""
        move = {"type": "row", "index": 2, "direction": "right"}
        reversed_move = Puzzle._reverse_move(move)
        assert reversed_move["direction"] == "left"

    def test_reverse_up_to_down(self):
        """Test reversing up direction to down."""
        move = {"type": "column", "index": 1, "direction": "up"}
        reversed_move = Puzzle._reverse_move(move)
        assert reversed_move["direction"] == "down"
        assert reversed_move["type"] == "column"

    def test_reverse_down_to_up(self):
        """Test reversing down direction to up."""
        move = {"type": "column", "index": 3, "direction": "down"}
        reversed_move = Puzzle._reverse_move(move)
        assert reversed_move["direction"] == "up"

    def test_reverse_preserves_type(self):
        """Test that reverse preserves move type."""
        row_move = {"type": "row", "index": 1, "direction": "left"}
        col_move = {"type": "column", "index": 1, "direction": "up"}

        assert Puzzle._reverse_move(row_move)["type"] == "row"
        assert Puzzle._reverse_move(col_move)["type"] == "column"

    def test_reverse_preserves_index(self):
        """Test that reverse preserves index."""
        move = {"type": "row", "index": 5, "direction": "left"}
        reversed_move = Puzzle._reverse_move(move)
        assert reversed_move["index"] == 5

    def test_reverse_does_not_modify_original(self):
        """Test that reverse creates a new dict, not modifying original."""
        move = {"type": "row", "index": 1, "direction": "left"}
        Puzzle._reverse_move(move)
        assert move["direction"] == "left"

    def test_double_reverse_returns_original_direction(self):
        """Test that reversing twice returns original direction."""
        move = {"type": "row", "index": 1, "direction": "left"}
        reversed_once = Puzzle._reverse_move(move)
        reversed_twice = Puzzle._reverse_move(reversed_once)
        assert reversed_twice["direction"] == "left"


class TestReverseSequence:
    """Tests for reverse_sequence static method."""

    def test_reverse_single_move_sequence(self):
        """Test reversing a sequence with one move."""
        sequence = [{"type": "row", "index": 1, "direction": "left"}]
        reversed_seq = Puzzle.reverse_sequence(sequence)

        assert len(reversed_seq) == 1
        assert reversed_seq[0]["direction"] == "right"

    def test_reverse_two_move_sequence(self):
        """Test reversing a sequence with two moves."""
        sequence = [
            {"type": "row", "index": 1, "direction": "left"},
            {"type": "column", "index": 2, "direction": "up"}
        ]
        reversed_seq = Puzzle.reverse_sequence(sequence)

        # Order should be reversed
        assert len(reversed_seq) == 2
        assert reversed_seq[0]["type"] == "column"
        assert reversed_seq[0]["direction"] == "down"
        assert reversed_seq[1]["type"] == "row"
        assert reversed_seq[1]["direction"] == "right"

    def test_reverse_three_move_sequence(self):
        """Test reversing a sequence with three moves."""
        sequence = [
            {"type": "row", "index": 1, "direction": "left"},
            {"type": "row", "index": 2, "direction": "right"},
            {"type": "column", "index": 3, "direction": "down"}
        ]
        reversed_seq = Puzzle.reverse_sequence(sequence)

        assert len(reversed_seq) == 3
        # First in reversed is last in original (with direction inverted)
        assert reversed_seq[0]["type"] == "column"
        assert reversed_seq[0]["index"] == 3
        assert reversed_seq[0]["direction"] == "up"
        # Last in reversed is first in original (with direction inverted)
        assert reversed_seq[2]["type"] == "row"
        assert reversed_seq[2]["index"] == 1
        assert reversed_seq[2]["direction"] == "right"

    def test_reverse_empty_sequence(self):
        """Test reversing an empty sequence."""
        sequence = []
        reversed_seq = Puzzle.reverse_sequence(sequence)
        assert reversed_seq == []

    def test_reverse_does_not_modify_original_sequence(self):
        """Test that reverse_sequence doesn't modify the original."""
        sequence = [
            {"type": "row", "index": 1, "direction": "left"},
            {"type": "column", "index": 2, "direction": "up"}
        ]
        original_first_direction = sequence[0]["direction"]
        Puzzle.reverse_sequence(sequence)

        assert sequence[0]["direction"] == original_first_direction
        assert len(sequence) == 2


class TestReverseMoveApplication:
    """Tests that applying reversed moves restores original state."""

    def test_reverse_single_move_restores_state(self, puzzle_3x3):
        """Test that applying a move then its reverse restores original."""
        original_board = [row[:] for row in puzzle_3x3.board]

        move = {"type": "row", "index": 1, "direction": "left"}
        puzzle_3x3.apply_move_from_json(json.dumps(move))

        reversed_move = Puzzle._reverse_move(move)
        puzzle_3x3.apply_move_from_json(json.dumps(reversed_move))

        assert puzzle_3x3.board == original_board

    def test_reverse_column_move_restores_state(self, puzzle_3x3):
        """Test reversing a column move restores original state."""
        original_board = [row[:] for row in puzzle_3x3.board]

        move = {"type": "column", "index": 2, "direction": "down"}
        puzzle_3x3.apply_move_from_json(json.dumps(move))

        reversed_move = Puzzle._reverse_move(move)
        puzzle_3x3.apply_move_from_json(json.dumps(reversed_move))

        assert puzzle_3x3.board == original_board

    def test_reverse_sequence_restores_original_state(self, puzzle_3x3):
        """Test that applying sequence then reversed sequence restores state."""
        original_board = [row[:] for row in puzzle_3x3.board]

        sequence = [
            {"type": "row", "index": 1, "direction": "left"},
            {"type": "column", "index": 2, "direction": "up"},
            {"type": "row", "index": 3, "direction": "right"}
        ]

        # Apply sequence
        for move in sequence:
            puzzle_3x3.apply_move_from_json(json.dumps(move))

        # Apply reversed sequence
        reversed_seq = Puzzle.reverse_sequence(sequence)
        for move in reversed_seq:
            puzzle_3x3.apply_move_from_json(json.dumps(move))

        assert puzzle_3x3.board == original_board

    def test_reverse_shuffle_sequence_solves_puzzle(self):
        """Test that applying reversed shuffle sequence solves the puzzle."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        shuffle_seq = puzzle.get_shuffle_key()

        # Puzzle should not be solved after shuffle
        assert not puzzle.is_solved()

        # Apply reversed shuffle sequence
        reversed_seq = Puzzle.reverse_sequence(shuffle_seq)
        for move in reversed_seq:
            puzzle.apply_move_from_json(json.dumps(move))

        # Puzzle should now be solved
        assert puzzle.is_solved()

    def test_reverse_complex_sequence(self, puzzle_4x4):
        """Test reversing a more complex sequence on 4x4."""
        original_board = [row[:] for row in puzzle_4x4.board]

        sequence = [
            {"type": "row", "index": 1, "direction": "left"},
            {"type": "row", "index": 2, "direction": "left"},
            {"type": "column", "index": 1, "direction": "up"},
            {"type": "column", "index": 4, "direction": "down"},
            {"type": "row", "index": 4, "direction": "right"},
        ]

        for move in sequence:
            puzzle_4x4.apply_move_from_json(json.dumps(move))

        reversed_seq = Puzzle.reverse_sequence(sequence)
        for move in reversed_seq:
            puzzle_4x4.apply_move_from_json(json.dumps(move))

        assert puzzle_4x4.board == original_board
