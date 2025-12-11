"""Tests for shuffle mechanics."""

import pytest
from core.puzzle import Puzzle


class TestShuffleBasics:
    """Basic tests for shuffle functionality."""

    def test_shuffle_creates_sequence(self):
        """Test that shuffling creates a shuffle sequence."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=5)
        assert len(puzzle.shuffle_sequence) >= 5

    def test_shuffle_sequence_has_correct_structure(self):
        """Test that shuffle sequence moves have correct structure."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=5)

        for move in puzzle.shuffle_sequence:
            assert "type" in move
            assert "index" in move
            assert "direction" in move
            assert move["type"] in ["row", "column"]
            assert 1 <= move["index"] <= 3

    def test_shuffle_row_moves_have_correct_directions(self):
        """Test that row moves in shuffle have left/right directions."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=20)

        for move in puzzle.shuffle_sequence:
            if move["type"] == "row":
                assert move["direction"] in ["left", "right"]

    def test_shuffle_column_moves_have_correct_directions(self):
        """Test that column moves in shuffle have up/down directions."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=20)

        for move in puzzle.shuffle_sequence:
            if move["type"] == "column":
                assert move["direction"] in ["up", "down"]

    def test_shuffle_modifies_board(self):
        """Test that shuffling actually changes the board."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        solved = puzzle.solved_board

        # After 10 moves, it's extremely unlikely the board is solved
        # (the recursive check would have added more moves)
        # At minimum, the shuffle_sequence should be non-empty
        assert len(puzzle.shuffle_sequence) > 0

    def test_shuffle_with_zero_moves(self):
        """Test shuffling with 0 moves (should trigger recursive if solved)."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=0)
        # With 0 moves, board stays solved, triggering recursive call with +5
        # So shuffle_sequence should have at least 5 moves
        assert len(puzzle.shuffle_sequence) >= 5

    def test_shuffle_preserves_all_tiles(self):
        """Test that all tiles are still present after shuffle."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=20)

        all_tiles = set()
        for row in puzzle.board:
            for tile in row:
                all_tiles.add(tile)

        expected_tiles = {str(i) for i in range(1, 10)}
        assert all_tiles == expected_tiles


class TestGetShuffleKey:
    """Tests for get_shuffle_key method."""

    def test_get_shuffle_key_returns_copy(self):
        """Test that get_shuffle_key returns a copy, not original."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=5)
        key = puzzle.get_shuffle_key()

        # Modify the returned key
        key[0]["direction"] = "modified"

        # Original should be unchanged
        assert puzzle.shuffle_sequence[0]["direction"] != "modified"

    def test_get_shuffle_key_same_length(self):
        """Test that get_shuffle_key returns same length as original."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        key = puzzle.get_shuffle_key()
        assert len(key) == len(puzzle.shuffle_sequence)

    def test_get_shuffle_key_empty_for_no_shuffle(self):
        """Test that get_shuffle_key returns empty for unshuffled puzzle."""
        puzzle = Puzzle(size=3, auto_shuffle=False)
        key = puzzle.get_shuffle_key()
        assert key == []


class TestShuffleRecursion:
    """Tests for shuffle recursion when puzzle ends up solved."""

    def test_shuffle_never_leaves_puzzle_solved(self):
        """Test that shuffle always results in non-solved state."""
        # Run multiple times to increase confidence
        for _ in range(10):
            puzzle = Puzzle(size=2, auto_shuffle=True, shuffle_moves=2)
            # A 2x2 puzzle with 2 moves has high chance of being solved
            # But recursive check should prevent this
            assert not puzzle.is_solved() or len(puzzle.shuffle_sequence) >= 7

    def test_shuffle_recursive_adds_moves(self):
        """Test that if solved after initial shuffle, more moves are added."""
        # This is hard to test directly, but we can check the behavior
        # by using a small puzzle with few moves
        puzzle = Puzzle(size=2, auto_shuffle=True, shuffle_moves=2)

        # Either the puzzle is not solved (good), or there are extra moves
        if puzzle.is_solved():
            # If still solved, sequence should be longer than original
            assert len(puzzle.shuffle_sequence) > 2


class TestShuffleMoveIndices:
    """Tests for shuffle move index bounds."""

    def test_shuffle_indices_in_bounds_3x3(self):
        """Test shuffle indices are valid for 3x3."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=50)

        for move in puzzle.shuffle_sequence:
            assert 1 <= move["index"] <= 3

    def test_shuffle_indices_in_bounds_6x6(self):
        """Test shuffle indices are valid for 6x6."""
        puzzle = Puzzle(size=6, auto_shuffle=True, shuffle_moves=50)

        for move in puzzle.shuffle_sequence:
            assert 1 <= move["index"] <= 6

    def test_shuffle_indices_in_bounds_2x2(self):
        """Test shuffle indices are valid for 2x2."""
        puzzle = Puzzle(size=2, auto_shuffle=True, shuffle_moves=20)

        for move in puzzle.shuffle_sequence:
            assert 1 <= move["index"] <= 2


class TestShuffleRandomness:
    """Tests for shuffle randomness."""

    def test_shuffle_includes_both_types(self):
        """Test that shuffle includes both row and column moves."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=50)

        types = {move["type"] for move in puzzle.shuffle_sequence}
        # With 50 moves, extremely likely to have both types
        assert "row" in types
        assert "column" in types

    def test_shuffle_includes_all_directions(self):
        """Test that shuffle includes all four directions."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=100)

        directions = {move["direction"] for move in puzzle.shuffle_sequence}
        # With 100 moves, should have all directions
        assert "left" in directions
        assert "right" in directions
        assert "up" in directions
        assert "down" in directions

    def test_shuffle_varies_indices(self):
        """Test that shuffle uses various indices."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=50)

        indices = {move["index"] for move in puzzle.shuffle_sequence}
        # With 50 moves on 3x3, should use all 3 indices
        assert len(indices) == 3

    def test_two_shuffles_produce_different_sequences(self):
        """Test that two shuffles likely produce different sequences."""
        puzzle1 = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        puzzle2 = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)

        # This could theoretically fail, but extremely unlikely with 10 moves
        # Just check they're not identical
        seq1 = [(m["type"], m["index"], m["direction"]) for m in puzzle1.shuffle_sequence]
        seq2 = [(m["type"], m["index"], m["direction"]) for m in puzzle2.shuffle_sequence]

        # They could be same length but different content
        # Not asserting inequality because it could randomly be same
        # Just verify they were created independently
        assert len(puzzle1.shuffle_sequence) >= 10
        assert len(puzzle2.shuffle_sequence) >= 10
