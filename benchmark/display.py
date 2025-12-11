"""Rich-based live dashboard for benchmark visualization."""

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.spinner import Spinner
from typing import List, Optional, Dict, Any
import re

console = Console()


class BenchmarkDashboard:
    """Manages the live dashboard display during benchmark runs."""

    def __init__(self, model: str, phase: int, attempt: int, total_attempts: int):
        self.model = model
        self.phase = phase
        self.attempt = attempt
        self.total_attempts = total_attempts
        self.grid_size = 3

        # State
        self.before_board: Optional[List[List[str]]] = None
        self.after_board: Optional[List[List[str]]] = None
        self.last_move: Optional[str] = None
        self.prediction_tile: Optional[int] = None
        self.prediction_tile_position: Optional[str] = None  # e.g., "R2C3"

        # Stats box info
        self.prev_question: Optional[str] = None
        self.prev_answer: Optional[str] = None
        self.prev_correct: Optional[bool] = None
        self.prev_prediction_tile: Optional[int] = None
        self.prev_prediction_position: Optional[str] = None

        # Stats
        self.turn = 0
        self.moves = 0
        self.predictions_correct = 0
        self.predictions_wrong = 0
        self.streak = 0

        # Display state
        self.is_thinking = False
        self.live: Optional[Live] = None

    def _render_board(self, board: List[List[str]], highlight_tile: Optional[int] = None, 
                     prev_prediction_pos: Optional[str] = None, prev_correct: Optional[bool] = None,
                     prev_tile: Optional[int] = None) -> Table:
        """Render a board as a rich Table."""
        n = len(board)
        table = Table(show_header=True, header_style="dim", box=None, padding=(0, 1))

        # Add column headers
        table.add_column("", justify="center", style="dim")
        for c in range(n):
            table.add_column(f"C{c+1}", justify="center", style="dim")

        # Parse previous prediction position if provided
        pred_row = None
        pred_col = None
        correct_tile_pos = None
        if prev_prediction_pos and prev_tile:
            match = re.match(r"R(\d+)C(\d+)", prev_prediction_pos)
            if match:
                pred_row = int(match.group(1)) - 1
                pred_col = int(match.group(2)) - 1
                # Find correct tile position
                for r in range(n):
                    for c in range(n):
                        if board[r][c] == str(prev_tile):
                            correct_tile_pos = (r, c)
                            break
                    if correct_tile_pos:
                        break

        # Add rows
        for r in range(n):
            row_data = [f"R{r+1}"]
            for c in range(n):
                val = board[r][c]
                cell_style = f"{val:^2}"
                
                # Handle previous prediction highlighting
                if prev_prediction_pos and prev_tile is not None:
                    if prev_correct:
                        # Correct: highlight predicted tile green
                        if r == pred_row and c == pred_col:
                            cell_style = f"[bold white on green]{val:^2}[/]"
                    else:
                        # Wrong: highlight predicted tile red
                        if r == pred_row and c == pred_col:
                            cell_style = f"[bold white on red]{val:^2}[/]"
                        # Show correct tile number in green (no background)
                        elif correct_tile_pos and r == correct_tile_pos[0] and c == correct_tile_pos[1]:
                            cell_style = f"[bold green]{val:^2}[/]"
                
                row_data.append(cell_style)
            table.add_row(*row_data)

        return table

    def _render_header(self) -> Panel:
        """Render the header panel."""
        header_text = Text()
        header_text.append(f"Model: {self.model}", style="bold white")
        header_text.append("  |  ", style="dim")
        header_text.append(f"Phase {self.phase}", style="yellow")
        header_text.append("  |  ", style="dim")
        header_text.append(f"Attempt {self.attempt}/{self.total_attempts}", style="green")
        header_text.append("  |  ", style="dim")
        header_text.append(f"Turn: {self.turn}", style="cyan")
        header_text.append("  |  ", style="dim")
        header_text.append(f"Moves: {self.moves}", style="cyan")

        return Panel(header_text, title="Rubiks Slider Benchmark", border_style="blue")

    def _render_boards(self) -> Table:
        """Render the before/after board comparison."""
        outer = Table(show_header=False, box=None, padding=(0, 2))

        # Before board
        if self.before_board:
            before_table = self._render_board(self.before_board)
            outer.add_column("BEFORE", justify="center")
        else:
            outer.add_column("")

        # Arrow and move
        outer.add_column("", justify="center", width=20)

        # After board
        if self.after_board:
            after_table = self._render_board(
                self.after_board,
                prev_prediction_pos=self.prev_prediction_position,
                prev_correct=self.prev_correct,
                prev_tile=self.prev_prediction_tile
            )
            outer.add_column("AFTER", justify="center")
        else:
            outer.add_column("")

        # Build the row
        before_content = self._render_board(self.before_board) if self.before_board else Text("(waiting)")

        move_text = Text()
        if self.last_move:
            move_text.append(f"Move: {self.last_move}\n\n", style="bold yellow")
        move_text.append("----------->", style="dim")

        after_content = self._render_board(
            self.after_board,
            prev_prediction_pos=self.prev_prediction_position,
            prev_correct=self.prev_correct,
            prev_tile=self.prev_prediction_tile
        ) if self.after_board else Text("(waiting)")

        outer.add_row(before_content, move_text, after_content)

        return outer

    def _render_stats_box(self) -> Panel:
        """Render the stats box with previous turn's question and answer."""
        if self.prev_question is None:
            content = Text("(No previous turn)", style="dim")
        else:
            content = Text()
            content.append(f"Q: {self.prev_question}\n", style="white")
            if self.prev_answer:
                if self.prev_correct:
                    content.append(f"A: {self.prev_answer} ", style="white")
                    content.append("Correct", style="bold green")
                else:
                    content.append(f"A: {self.prev_answer} ", style="white")
                    content.append("Wrong", style="bold red")
            streak_text = f"{self.streak}" if self.streak >= 0 else f"{self.streak}"
            content.append(f"\nCorrect: {self.predictions_correct}  |  Wrong: {self.predictions_wrong}  Streak: {streak_text}", style="dim")

        return Panel(content, title="Stats", border_style="dim")

    def _render_stats(self) -> Panel:
        """Render the streak stats."""
        streak_text = f"{self.streak}" if self.streak >= 0 else f"{self.streak}"
        streak_display = f"Streak: {streak_text}"

        return Panel(streak_display, border_style="dim")

    def _render_spinner(self) -> Text:
        """Render thinking indicator."""
        if self.is_thinking:
            return Text("Thinking...", style="dim italic", justify="right")
        return Text("")

    def render(self) -> Layout:
        """Render the complete dashboard."""
        layout = Layout()

        layout.split_column(
            Layout(self._render_header(), name="header", size=3),
            Layout(name="body", size=8),
            Layout(self._render_stats_box(), name="stats_box", size=5),
            Layout(self._render_spinner(), name="spinner", size=1),
        )

        layout["body"].update(Panel(self._render_boards(), border_style="dim"))

        return layout

    def start(self):
        """Start the live display."""
        self.live = Live(self.render(), console=console, refresh_per_second=4)
        self.live.start()

    def stop(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def update(self):
        """Refresh the display."""
        if self.live:
            self.live.update(self.render())

    def set_thinking(self, thinking: bool):
        """Set the thinking state."""
        self.is_thinking = thinking
        self.update()

    def set_boards(self, before: List[List[str]], after: List[List[str]], move: str):
        """Update the board states."""
        self.before_board = before
        self.after_board = after
        self.last_move = move
        self.update()

    def set_prediction_target(self, tile: int):
        """Set which tile is being asked about."""
        self.prediction_tile = tile
        self.update()

    def record_prediction_result(self, question: str, answer: str, correct: bool):
        """Record the result of a prediction."""
        self.prev_question = question
        self.prev_answer = answer
        self.prev_correct = correct
        
        # Extract tile number from question (e.g., "Where will tile 7 be?" -> 7)
        tile_match = re.search(r"tile\s+(\d+)", question, re.IGNORECASE)
        if tile_match:
            self.prev_prediction_tile = int(tile_match.group(1))
        else:
            self.prev_prediction_tile = None
        
        # Store prediction position if valid format
        if answer and re.match(r"^R\d+C\d+$", answer):
            self.prev_prediction_position = answer
        else:
            self.prev_prediction_position = None

        if correct:
            self.predictions_correct += 1
            if self.streak < 0:
                self.streak = 1
            else:
                self.streak += 1
        else:
            self.predictions_wrong += 1
            if self.streak > 0:
                self.streak = -1
            else:
                self.streak -= 1

        self.update()

    def increment_turn(self):
        """Increment the turn counter."""
        self.turn += 1
        self.update()

    def add_moves(self, count: int):
        """Add to the move counter."""
        self.moves += count
        self.update()
