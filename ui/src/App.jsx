import React, { useEffect, useRef, useState } from "react";
import Board from "./Board.jsx";
import {
  FIXED_LIMITS,
  parseQuery,
  solvedNumbers,
  buildTileBoard,
  deepCopyBoard,
  isSolved,
  applyMove,
  applySequence,
  generateDeterministicSequence,
  colorForTile,
  fromBase64Url,
} from "./game.js";

export default function App() {
  const [size, setSize] = useState(6);
  const [board, setBoard] = useState(() => buildTileBoard(6, solvedNumbers(6)));
  const [committedBoard, setCommittedBoard] = useState(() => deepCopyBoard(board));
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

  // New Modes & Prediction
  const [blindMode, setBlindMode] = useState(false);
  const [multiMoveMode, setMultiMoveMode] = useState(false);
  const [moveQueue, setMoveQueue] = useState([]);
  const [predictionTarget, setPredictionTarget] = useState(null); // { r, c, val }
  const [predictionInput, setPredictionInput] = useState("");
  const [consecutiveWrong, setConsecutiveWrong] = useState(0);
  const [predictionFeedback, setPredictionFeedback] = useState(null); // { correct: bool, msg: string }

  const miniRef = useRef(null);

  function updateLimitForSize(nextSize) {
    setLimitMoves(FIXED_LIMITS[nextSize] || nextSize * nextSize * 2);
  }

  function pickPredictionTarget(currentBoard) {
    const n = currentBoard.length;
    const r = Math.floor(Math.random() * n);
    const c = Math.floor(Math.random() * n);
    return { r, c, val: currentBoard[r][c].val };
  }

  function drawMiniMap(n) {
    const canvas = miniRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const numbers = solvedNumbers(n);
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
        ctx.fillStyle = colorForTile(numbers[r][c]);
        ctx.fillRect(x, y, cellW, cellH);
      }
    }
  }

  function performMove(move) {
    if (animating || outOfMoves) return;

    if (moveCount >= limitMoves) {
      setLimitVisible(true);
      setOutOfMoves(true);
      return;
    }

    if (blindMode || multiMoveMode) {
      // Queue move
      setMoveQueue((prev) => [...prev, move]);
      // In multi-move (not blind), we might want to show the move immediately?
      // The requirement says: "In multi-move mode, queue moves and require explicit submit."
      // But usually multi-move lets you see the state.
      // However, "Blind mode" hides intermediate.
      // Let's follow: Blind -> Queue, no update. Multi -> Queue, update board?
      // Re-reading: "In multi-move mode, queue moves and require explicit submit."
      // And "Blind mode... User enters moves without seeing intermediate animations"
      
      if (!blindMode) {
        // Apply visually but keep in queue for submission logic if needed,
        // OR just apply immediately and track "turn" moves?
        // The prompt says: "In multi-move mode, queue moves and require explicit submit."
        // This implies we build up a sequence then commit it.
        // So we should update the board state for visual feedback in Multi-Move (non-blind),
        // but in Blind mode we do NOT update the board state.
        
        setAnimating(true);
        const next = deepCopyBoard(board);
        applyMove(next, move);
        setBoard(next);
        window.setTimeout(() => setAnimating(false), 230);
      }
    } else {
      // Single move mode (Phase 1 style) - immediate commit
      commitSingleMove(move);
    }
  }

  function commitSingleMove(move) {
    setAnimating(true);
    const next = deepCopyBoard(board);
    applyMove(next, move);
    setBoard(next);
    setCommittedBoard(deepCopyBoard(next)); // Sync committed state
    setMoveCount((c) => c + 1);

    window.setTimeout(() => {
      setAnimating(false);
      checkSolved(next);
    }, 230);
  }

  function submitMoves() {
    if (moveQueue.length === 0) return;

    // Apply all queued moves to the *committed* board state (start of turn)
    // In non-blind multi-move, 'board' is already updated visually, but 'committedBoard' is behind.
    // In blind mode, 'board' is behind (matches committedBoard).
    
    let next = deepCopyBoard(committedBoard);
    
    // If blind mode, we haven't shown these moves yet.
    // If multi-move non-blind, we have shown them.
    
    // We need to validate prediction if active
    if (predictionTarget) {
      // Calculate where target SHOULD be
      const testBoard = deepCopyBoard(committedBoard);
      applySequence(testBoard, moveQueue);
      
      // Find target in new board
      let actualR = -1, actualC = -1;
      for(let r=0; r<size; r++) {
        for(let c=0; c<size; c++) {
          if (testBoard[r][c].val === predictionTarget.val) {
            actualR = r;
            actualC = c;
          }
        }
      }
      
      // Parse input
      const match = predictionInput.toUpperCase().match(/R(\d+)C(\d+)/);
      let correct = false;
      if (match) {
        const predR = parseInt(match[1], 10) - 1;
        const predC = parseInt(match[2], 10) - 1;
        if (predR === actualR && predC === actualC) {
          correct = true;
        }
      }
      
      if (correct) {
        setPredictionFeedback({ correct: true, msg: "Correct!" });
        setConsecutiveWrong(0);
      } else {
        const newWrong = consecutiveWrong + 1;
        setConsecutiveWrong(newWrong);
        setPredictionFeedback({ correct: false, msg: `Wrong! It's at R${actualR+1}C${actualC+1}` });
        if (newWrong >= 3) {
           // Failure condition could be handled here
        }
      }
      
      // Pick new target for next turn
      setPredictionTarget(pickPredictionTarget(testBoard));
      setPredictionInput("");
    }

    // Apply moves for real
    // For visual continuity in blind mode, we might want to animate?
    // For now, just jump to result to keep it simple or animate sequence?
    // "Only then reveal the result"
    
    applySequence(next, moveQueue);
    setBoard(next);
    setCommittedBoard(deepCopyBoard(next));
    setMoveCount((c) => c + moveQueue.length);
    setMoveQueue([]);
    
    checkSolved(next);
  }

  function checkSolved(currentBoard) {
    if (isSolved(currentBoard)) {
      if (progressive) {
        setSolvedMessage("Level complete!");
        setSolvedVisible(true);
        window.setTimeout(() => advanceLevel(), 800);
      } else {
        setSolvedMessage("Solved!");
        setSolvedVisible(true);
      }
    }
  }

  function resetPuzzle() {
    setBoard(deepCopyBoard(startBoard));
    setCommittedBoard(deepCopyBoard(startBoard));
    setMoveCount(0);
    setOutOfMoves(false);
    setSolvedVisible(false);
    setLimitVisible(false);
    setMoveQueue([]);
    setPredictionFeedback(null);
    setConsecutiveWrong(0);
    if (blindMode || multiMoveMode) {
        setPredictionTarget(pickPredictionTarget(startBoard));
    }
  }

  function newDeterministicPuzzleForSize(n) {
    const numbers = solvedNumbers(n);
    const fresh = buildTileBoard(n, numbers);
    const seq = generateDeterministicSequence(n);
    setShuffleSeq(seq);

    const applied = deepCopyBoard(fresh);
    applySequence(applied, seq);

    setStartBoard(deepCopyBoard(applied));
    setBoard(deepCopyBoard(applied));
    setCommittedBoard(deepCopyBoard(applied));
    setMoveCount(0);
    setOutOfMoves(false);
    setSolvedVisible(false);
    setLimitVisible(false);
    setMoveQueue([]);
    setPredictionFeedback(null);
    setConsecutiveWrong(0);
    drawMiniMap(n);
    
    if (blindMode || multiMoveMode) {
        setPredictionTarget(pickPredictionTarget(applied));
    } else {
        setPredictionTarget(null);
    }
  }

  function startLevel(n) {
    setSize(n);
    updateLimitForSize(n);
    setSolvedVisible(false);
    setLimitVisible(false);
    setOutOfMoves(false);
    setMoveQueue([]);
    setPredictionFeedback(null);

    const numbers = solvedNumbers(n);
    const base = buildTileBoard(n, numbers);

    const seq = generateDeterministicSequence(n);
    setShuffleSeq(seq);

    const applied = deepCopyBoard(base);
    applySequence(applied, seq);

    setStartBoard(deepCopyBoard(applied));
    setBoard(deepCopyBoard(applied));
    setCommittedBoard(deepCopyBoard(applied));
    setMoveCount(0);
    drawMiniMap(n);
    
    if (blindMode || multiMoveMode) {
        setPredictionTarget(pickPredictionTarget(applied));
    } else {
        setPredictionTarget(null);
    }
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

  useEffect(() => {
    const { size: qSize, p, progressive: qProgressive } = parseQuery(window.location.search);
    const singlePuzzle = !!p;

    const useProgressive = qProgressive || !singlePuzzle;
    setProgressive(!!useProgressive);

    if (useProgressive) {
      setLevelIndex(0);
      startLevel(levelSizes[0]); 
      return;
    }

    const n = qSize;
    setSize(n);
    updateLimitForSize(n);

    const numbers = solvedNumbers(n);
    const base = buildTileBoard(n, numbers);

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
          setCommittedBoard(deepCopyBoard(applied));
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
    setCommittedBoard(deepCopyBoard(applied));
    setMoveCount(0);
    setSolvedVisible(false);
    setLimitVisible(false);
    drawMiniMap(n);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  function toggleBlind() {
    setBlindMode(!blindMode);
    // Reset to ensure clean state when switching modes
    resetPuzzle();
  }
  
  function toggleMultiMove() {
    setMultiMoveMode(!multiMoveMode);
    resetPuzzle();
  }

  return (
    <div className="wrap">
      <header>
        <h1>Rubik's Slider</h1>
      </header>

      <div className="toolbar">
        <button title="Create a new puzzle" onClick={onNew}>New</button>
        <button onClick={toggleBlind} className={blindMode ? "active" : ""}>
          {blindMode ? "Blind: ON" : "Blind: OFF"}
        </button>
        <button onClick={toggleMultiMove} className={multiMoveMode ? "active" : ""}>
          {multiMoveMode ? "Multi-Move" : "Single-Move"}
        </button>
        <div className="counter">
          <span>{moveCount}</span>/<span>{limitMoves}</span> Moves
        </div>
      </div>

      {(blindMode || multiMoveMode) && (
        <div className="prediction-panel">
          {predictionTarget && (
            <div className="prediction-challenge">
              <span>Where will tile <b>{predictionTarget.val}</b> be?</span>
              <input
                type="text"
                placeholder="R#C#"
                value={predictionInput}
                onChange={e => setPredictionInput(e.target.value)}
                maxLength={4}
              />
            </div>
          )}
          <div className="queue-controls">
            <span>Queued: {moveQueue.length}</span>
            <button onClick={submitMoves} disabled={moveQueue.length === 0}>Submit Moves</button>
          </div>
          {predictionFeedback && (
            <div className={`feedback ${predictionFeedback.correct ? "good" : "bad"}`}>
              {predictionFeedback.msg}
            </div>
          )}
          {consecutiveWrong > 0 && (
             <div className={`wrong-counter ${consecutiveWrong >= 2 ? "warn" : ""}`}>
               Wrong streak: {consecutiveWrong} {consecutiveWrong >= 3 ? "(FAILED)" : ""}
             </div>
          )}
        </div>
      )}

      <div className="board-wrap">
        <Board size={size} board={board} onCommitMove={performMove} />

        <div className={`overlay ${solvedVisible ? "show" : ""}`} role="status" aria-live="polite">
          <div className="card">
            <div className="big">{solvedMessage}</div>
            <div className="hint">Level complete.</div>
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
