"""Integration tests for complete puzzle mechanics."""

import pytest
import json
from core.puzzle import Puzzle, parse_simple_move


class TestCompleteGameFlow:
    """Tests for complete game flows."""

    def test_full_game_solve_via_reverse_shuffle(self):
        """Test a complete game: shuffle, verify unsolved, reverse, verify solved."""
        # Create and shuffle
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=15)

        # Verify not solved
        assert not puzzle.is_solved()

        # Get and reverse shuffle
        shuffle_seq = puzzle.get_shuffle_key()
        reversed_seq = Puzzle.reverse_sequence(shuffle_seq)

        # Apply reversed sequence
        for move in reversed_seq:
            puzzle.apply_move_from_json(json.dumps(move))

        # Verify solved
        assert puzzle.is_solved()

    def test_game_with_move_parsing(self):
        """Test game using parse_simple_move for input."""
        puzzle = Puzzle(size=3, auto_shuffle=False)

        # Make moves via parsing
        json_move, _ = parse_simple_move("R1 L", 3)
        puzzle.apply_move_from_json(json_move)

        json_move, _ = parse_simple_move("C2 U", 3)
        puzzle.apply_move_from_json(json_move)

        # Verify state changed
        assert not puzzle.is_solved()

        # Reverse the moves
        json_move, _ = parse_simple_move("C2 D", 3)
        puzzle.apply_move_from_json(json_move)

        json_move, _ = parse_simple_move("R1 R", 3)
        puzzle.apply_move_from_json(json_move)

        # Verify solved
        assert puzzle.is_solved()

    def test_prediction_workflow(self):
        """Test complete prediction workflow: move, check position, validate."""
        puzzle = Puzzle(size=3, auto_shuffle=False)

        # Choose a tile to track
        tile = 5  # Center tile
        initial_pos = puzzle.get_tile_position(tile)
        assert initial_pos == (2, 2)

        # Plan a move and predict outcome
        # Row 2 left will move tile 5 from C2 to C1
        expected_pos = "R2C1"

        # Apply the move
        puzzle.apply_move_from_json('{"type": "row", "index": 2, "direction": "left"}')

        # Validate prediction
        assert puzzle.validate_prediction(tile, expected_pos)

    def test_complex_prediction_sequence(self):
        """Test predictions through multiple moves."""
        puzzle = Puzzle(size=3, auto_shuffle=False)

        # Track tile 1 through multiple moves
        # Initial: R1C1

        # Move 1: R1 L - tile 1 goes to R1C3
        puzzle.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        assert puzzle.validate_prediction(1, "R1C3")

        # Move 2: C3 D - tile 1 goes to R2C3
        puzzle.apply_move_from_json('{"type": "column", "index": 3, "direction": "down"}')
        assert puzzle.validate_prediction(1, "R2C3")

        # Move 3: R2 R - tile 1 goes to R2C1
        puzzle.apply_move_from_json('{"type": "row", "index": 2, "direction": "right"}')
        assert puzzle.validate_prediction(1, "R2C1")


class TestBenchmarkScenarios:
    """Tests simulating benchmark scenarios."""

    def test_benchmark_single_move_phase(self):
        """Test benchmark phase 1 (single move per turn) scenario."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=5)

        moves_made = 0
        max_moves = 50

        shuffle_seq = puzzle.get_shuffle_key()
        reversed_seq = Puzzle.reverse_sequence(shuffle_seq)

        for move in reversed_seq:
            if puzzle.is_solved():
                break
            success, _ = puzzle.apply_move_from_json(json.dumps(move))
            assert success
            moves_made += 1
            assert moves_made <= max_moves

        assert puzzle.is_solved()

    def test_benchmark_multi_move_phase(self):
        """Test benchmark phase 2 (multiple moves per turn) scenario."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)

        shuffle_seq = puzzle.get_shuffle_key()
        reversed_seq = Puzzle.reverse_sequence(shuffle_seq)

        # Apply all moves at once (simulating multi-move turn)
        for move in reversed_seq:
            puzzle.apply_move_from_json(json.dumps(move))

        assert puzzle.is_solved()

    def test_prediction_accuracy_tracking(self):
        """Test tracking prediction accuracy like benchmark does."""
        puzzle = Puzzle(size=3, auto_shuffle=False)

        predictions_total = 0
        predictions_correct = 0

        # Make some moves and predictions
        moves = [
            ('{"type": "row", "index": 1, "direction": "left"}', 1, "R1C3"),  # Correct
            ('{"type": "column", "index": 3, "direction": "up"}', 1, "R3C3"),  # Correct
            ('{"type": "row", "index": 3, "direction": "right"}', 1, "R3C1"),  # Correct
        ]

        for move_json, tile, prediction in moves:
            puzzle.apply_move_from_json(move_json)
            predictions_total += 1
            if puzzle.validate_prediction(tile, prediction):
                predictions_correct += 1

        accuracy = (predictions_correct / predictions_total) * 100
        assert accuracy == 100.0


class TestMoveCommutativity:
    """Tests for when moves commute (can be swapped)."""

    def test_independent_row_moves_commute(self, puzzle_3x3):
        """Test that moves on different rows can be swapped."""
        # Make copy
        puzzle_copy = Puzzle(size=3, auto_shuffle=False)

        # Puzzle 1: R1 L then R3 R
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 3, "direction": "right"}')

        # Puzzle 2: R3 R then R1 L
        puzzle_copy.apply_move_from_json('{"type": "row", "index": 3, "direction": "right"}')
        puzzle_copy.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')

        assert puzzle_3x3.board == puzzle_copy.board

    def test_independent_column_moves_commute(self, puzzle_3x3):
        """Test that moves on different columns can be swapped."""
        puzzle_copy = Puzzle(size=3, auto_shuffle=False)

        puzzle_3x3.apply_move_from_json('{"type": "column", "index": 1, "direction": "up"}')
        puzzle_3x3.apply_move_from_json('{"type": "column", "index": 3, "direction": "down"}')

        puzzle_copy.apply_move_from_json('{"type": "column", "index": 3, "direction": "down"}')
        puzzle_copy.apply_move_from_json('{"type": "column", "index": 1, "direction": "up"}')

        assert puzzle_3x3.board == puzzle_copy.board

    def test_row_column_moves_dont_commute(self, puzzle_3x3):
        """Test that intersecting row/column moves don't commute."""
        puzzle_copy = Puzzle(size=3, auto_shuffle=False)

        # Puzzle 1: R1 L then C1 U (they intersect at R1C1)
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        puzzle_3x3.apply_move_from_json('{"type": "column", "index": 1, "direction": "up"}')

        # Puzzle 2: C1 U then R1 L
        puzzle_copy.apply_move_from_json('{"type": "column", "index": 1, "direction": "up"}')
        puzzle_copy.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')

        # These should NOT be equal
        assert puzzle_3x3.board != puzzle_copy.board


class TestStateConsistency:
    """Tests for state consistency throughout operations."""

    def test_tile_count_preserved(self, puzzle_3x3):
        """Test all tiles present after many random moves."""
        import random

        for _ in range(100):
            if random.choice([True, False]):
                row = random.randint(0, 2)
                direction = random.choice(["left", "right"])
                puzzle_3x3._shift_row(row, direction)
            else:
                col = random.randint(0, 2)
                direction = random.choice(["up", "down"])
                puzzle_3x3._shift_column(col, direction)

        # All tiles should still be present
        all_tiles = set()
        for row in puzzle_3x3.board:
            for tile in row:
                all_tiles.add(tile)

        expected = {str(i) for i in range(1, 10)}
        assert all_tiles == expected

    def test_no_duplicate_tiles(self, puzzle_3x3):
        """Test no duplicate tiles after operations."""
        puzzle_3x3._shift_row(0, "left")
        puzzle_3x3._shift_column(1, "up")
        puzzle_3x3._shift_row(2, "right")

        all_tiles = []
        for row in puzzle_3x3.board:
            all_tiles.extend(row)

        # All unique
        assert len(all_tiles) == len(set(all_tiles))

    def test_grid_size_preserved(self, puzzle_3x3):
        """Test grid dimensions preserved after operations."""
        puzzle_3x3._shift_row(0, "left")
        puzzle_3x3._shift_column(0, "up")

        assert len(puzzle_3x3.board) == 3
        for row in puzzle_3x3.board:
            assert len(row) == 3


class TestReproducibility:
    """Tests for reproducibility of operations."""

    def test_same_moves_produce_same_result(self):
        """Test that identical move sequences produce identical results."""
        puzzle1 = Puzzle(size=3, auto_shuffle=False)
        puzzle2 = Puzzle(size=3, auto_shuffle=False)

        moves = [
            '{"type": "row", "index": 1, "direction": "left"}',
            '{"type": "column", "index": 2, "direction": "up"}',
            '{"type": "row", "index": 3, "direction": "right"}',
        ]

        for move in moves:
            puzzle1.apply_move_from_json(move)
            puzzle2.apply_move_from_json(move)

        assert puzzle1.board == puzzle2.board

    def test_shuffle_with_same_sequence_reproducible(self):
        """Test applying same shuffle sequence produces same state."""
        # Create a puzzle and get its shuffle sequence
        puzzle1 = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        shuffle_seq = puzzle1.get_shuffle_key()

        # Apply same sequence to a fresh puzzle
        puzzle2 = Puzzle(size=3, auto_shuffle=False)
        for move in shuffle_seq:
            puzzle2.apply_move_from_json(json.dumps(move))

        assert puzzle1.board == puzzle2.board
