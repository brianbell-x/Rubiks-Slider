import React, { useEffect, useRef, useState } from "react";
import Board from "./Board.jsx";
import {
  FIXED_LIMITS,
  parseQuery,
  solvedLetters,
  buildTileBoard,
  deepCopyBoard,
  isSolved,
  applyMove,
  applySequence,
  generateDeterministicSequence,
  colorForLetter,
  fromBase64Url,
} from "./game.js";

export default function App() {
  // Core state (kept minimal, mirrors MVP)
  const [size, setSize] = useState(6);
  const [board, setBoard] = useState(() => buildTileBoard(6, solvedLetters(6)));
  const [startBoard, setStartBoard] = useState(() => deepCopyBoard(board));
  const [shuffleSeq, setShuffleSeq] = useState([]);
  const [moveCount, setMoveCount] = useState(0);
  const [limitMoves, setLimitMoves] = useState(FIXED_LIMITS[6] || 72);
  const [progressive, setProgressive] = useState(true);
  const [levelSizes] = useState([3, 4, 5, 6]);
  const [levelIndex, setLevelIndex] = useState(0);
  const [animating, setAnimating] = useState(false);
  const [outOfMoves, setOutOfMoves] = useState(false);
  const [solvedVisible, setSolvedVisible] = useState(false);
  const [limitVisible, setLimitVisible] = useState(false);
  const [solvedMessage, setSolvedMessage] = useState("Solved!");
  const [newSaltCounter, setNewSaltCounter] = useState(0);

  // Mini-map canvas ref
  const miniRef = useRef(null);

  function updateLimitForSize(nextSize) {
    setLimitMoves(FIXED_LIMITS[nextSize] || nextSize * nextSize * 2);
  }

  // Mini-map drawing (solved-state preview)
  function drawMiniMap(n) {
    const canvas = miniRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const letters = solvedLetters(n);
    const W = canvas.width,
      H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    const gap = 1;
    const cellW = Math.floor((W - (n + 1) * gap) / n);
    const cellH = Math.floor((H - (n + 1) * gap) / n);
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const x = gap + c * (cellW + gap);
        const y = gap + r * (cellH + gap);
        ctx.fillStyle = colorForLetter(letters[r][c]);
        ctx.fillRect(x, y, cellW, cellH);
      }
    }
  }

  // Perform one user move (row/column, 1-based index, direction)
  function performMove(move) {
    if (animating || outOfMoves) return;

    // Enforce move limit exactly like benchmark
    if (moveCount >= limitMoves) {
      setLimitVisible(true);
      setOutOfMoves(true);
      return;
    }

    setAnimating(true);

    const next = deepCopyBoard(board);
    applyMove(next, move);
    setBoard(next);
    setMoveCount((c) => c + 1);

    // After animation period, clear animating and check solved
    window.setTimeout(() => {
      setAnimating(false);
      if (isSolved(next)) {
        if (progressive) {
          setSolvedMessage("Level complete!");
          setSolvedVisible(true);
          window.setTimeout(() => advanceLevel(), 800);
        } else {
          setSolvedMessage("Solved!");
          setSolvedVisible(true);
        }
      }
    }, 230);
  }

  // Reset to the start state for this puzzle
  function resetPuzzle() {
    setBoard(deepCopyBoard(startBoard));
    setMoveCount(0);
    setOutOfMoves(false);
    setSolvedVisible(false);
    setLimitVisible(false);
  }

  // New deterministic puzzle for current size, with session salt increment
  function newDeterministicPuzzleForSize(n) {
    const letters = solvedLetters(n);
    const fresh = buildTileBoard(n, letters);
    const nextSalt = newSaltCounter + 1;
    const seq = generateDeterministicSequence(n, null, `_salt${nextSalt}`);
    setShuffleSeq(seq);

    const applied = deepCopyBoard(fresh);
    applySequence(applied, seq);

    setStartBoard(deepCopyBoard(applied));
    setBoard(deepCopyBoard(applied));
    setMoveCount(0);
    setOutOfMoves(false);
    setSolvedVisible(false);
    setLimitVisible(false);
    setNewSaltCounter(nextSalt);
    drawMiniMap(n);
  }

  // Progressive level control
  function startLevel(n) {
    setSize(n);
    updateLimitForSize(n);
    setSolvedVisible(false);
    setLimitVisible(false);
    setOutOfMoves(false);

    const letters = solvedLetters(n);
    const base = buildTileBoard(n, letters);

    // Per-size deterministic sequence (no salt) to match benchmark-like behavior
    const seq = generateDeterministicSequence(n);
    setShuffleSeq(seq);

    const applied = deepCopyBoard(base);
    applySequence(applied, seq);

    setStartBoard(deepCopyBoard(applied));
    setBoard(deepCopyBoard(applied));
    setMoveCount(0);
    drawMiniMap(n);
  }

  function advanceLevel() {
    if (!progressive) return;
    if (levelIndex + 1 >= levelSizes.length) {
      setSolvedMessage("All levels complete!");
      setSolvedVisible(true);
      return;
    }
    const nextIdx = levelIndex + 1;
    setLevelIndex(nextIdx);
    startLevel(levelSizes[nextIdx]);
  }

  // Initialize from URL query
  useEffect(() => {
    const { size: qSize, p, progressive: qProgressive } = parseQuery(window.location.search);
    const singlePuzzle = !!p;

    const useProgressive = qProgressive || !singlePuzzle;
    setProgressive(!!useProgressive);

    if (useProgressive) {
      setLevelIndex(0);
      startLevel(levelSizes[0]); // 3x3
      return;
    }

    // Single puzzle mode
    const n = qSize;
    setSize(n);
    updateLimitForSize(n);

    const letters = solvedLetters(n);
    const base = buildTileBoard(n, letters);

    if (p) {
      try {
        const decoded = JSON.parse(fromBase64Url(p));
        if (decoded && decoded.size === n && Array.isArray(decoded.seq)) {
          const seq = decoded.seq.map((m) => ({
            type: m.type,
            index: parseInt(m.index, 10),
            direction: m.direction,
          }));
          setShuffleSeq(seq);
          const applied = deepCopyBoard(base);
          applySequence(applied, seq);
          setStartBoard(deepCopyBoard(applied));
          setBoard(deepCopyBoard(applied));
          setMoveCount(0);
          setSolvedVisible(false);
          setLimitVisible(false);
          drawMiniMap(n);
          return;
        }
      } catch {
        // fall through to deterministic
      }
    }

    const seq = generateDeterministicSequence(n);
    setShuffleSeq(seq);
    const applied = deepCopyBoard(base);
    applySequence(applied, seq);
    setStartBoard(deepCopyBoard(applied));
    setBoard(deepCopyBoard(applied));
    setMoveCount(0);
    setSolvedVisible(false);
    setLimitVisible(false);
    drawMiniMap(n);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Actions (buttons)
  function onNew() {
    newDeterministicPuzzleForSize(size);
  }
  function onSolvedReset() {
    resetPuzzle();
    setSolvedVisible(false);
  }
  function onSolvedNew() {
    newDeterministicPuzzleForSize(size);
    setSolvedVisible(false);
  }
  function onLimitRetry() {
    resetPuzzle();
    setLimitVisible(false);
  }
  function onLimitRestart() {
    setProgressive(true);
    setLevelIndex(0);
    setLimitVisible(false);
    startLevel(levelSizes[0]);
  }

  return (
    <div className="wrap">
      <header>
        <h1>Rubik's Slider</h1>
      </header>

      <div className="toolbar">
        <button title="Create a new puzzle" onClick={onNew}>New</button>
        <div className="counter">
          <span>{moveCount}</span>/<span>{limitMoves}</span> Moves Made
        </div>
      </div>

      <div className="board-wrap">
        <Board size={size} board={board} onCommitMove={performMove} />

        <div className={`overlay ${solvedVisible ? "show" : ""}`} role="status" aria-live="polite">
          <div className="card">
            <div className="big">{solvedMessage}</div>
            <div className="hint">{progressive ? "Level complete." : "Level complete."}</div>
            <div className="actions">
              <button onClick={onSolvedReset}>Reset</button>
              <button onClick={onSolvedNew}>New</button>
            </div>
          </div>
        </div>

        <div className={`overlay ${limitVisible ? "show" : ""}`} role="status" aria-live="polite">
          <div className="card">
            <div className="big">Out of moves</div>
            <div className="hint">Move limit reached.</div>
            <div className="actions">
              <button onClick={onLimitRetry}>Retry</button>
              <button onClick={onLimitRestart}>Restart</button>
            </div>
          </div>
        </div>

        <div className="hud">
          <div className="mini">
            <canvas id="mini" ref={miniRef} width="96" height="96" aria-label="Solved preview"></canvas>
          </div>
        </div>
      </div>

      <div className="footer"></div>
    </div>
  );
}
