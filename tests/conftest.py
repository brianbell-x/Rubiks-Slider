"""Pytest configuration and fixtures for Rubiks Slider tests."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.puzzle import Puzzle


@pytest.fixture
def puzzle_2x2():
    """Create a 2x2 puzzle without shuffling."""
    return Puzzle(size=2, auto_shuffle=False)


@pytest.fixture
def puzzle_3x3():
    """Create a 3x3 puzzle without shuffling."""
    return Puzzle(size=3, auto_shuffle=False)


@pytest.fixture
def puzzle_4x4():
    """Create a 4x4 puzzle without shuffling."""
    return Puzzle(size=4, auto_shuffle=False)


@pytest.fixture
def puzzle_6x6():
    """Create a 6x6 puzzle without shuffling."""
    return Puzzle(size=6, auto_shuffle=False)


@pytest.fixture
def solved_3x3_board():
    """Return a solved 3x3 board."""
    return [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"]
    ]


@pytest.fixture
def custom_3x3_board():
    """Return a custom 3x3 board for testing."""
    return [
        ["A", "B", "C"],
        ["D", "E", "F"],
        ["G", "H", "I"]
    ]
