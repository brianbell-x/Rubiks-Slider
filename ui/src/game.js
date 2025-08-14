/**
 * Game logic and utilities shared by React components.
 * Mirrors benchmark/settings.py seeds and core/puzzle.py move semantics.
 */

// Constants aligned with MVP and benchmark
export const FIXED_LIMITS = { 3: 50, 4: 100, 5: 200, 6: 400 };
// Keep aligned with benchmark/settings.py VERSION
function getVersionFromQuery(search = typeof window !== "undefined" ? window.location.search : "") {
  try {
    const params = new URLSearchParams(search || "");
    const v = params.get("version");
    if (v && /^\d{12}$/.test(v)) return v;
  } catch (e) {}
  return null;
}
export const VERSION = getVersionFromQuery() || makeVersionNow();

// Palette and color mapping based on letter
export const PALETTE = [
  "#e6194B", // A Red
  "#4363d8", // B Blue
  "#ffe119", // C Yellow
  "#3cb44b", // D Green
  "#f58231", // E Orange
  "#911eb4", // F Purple
  "#42d4f4", // G Cyan
  "#fabed4", // H Pink
  "#469990", // I Teal
  "#f032e6", // J Magenta
  "#bcf60c", // K Lime
  "#9A6324", // L Brown
  "#800000", // M Maroon
  "#2E8B57", // N SeaGreen
  "#87CEEB", // O SkyBlue
];
export function colorForLetter(ch) {
  const idx = (ch.charCodeAt(0) - 65) % PALETTE.length;
  return PALETTE[(idx + PALETTE.length) % PALETTE.length];
}

// Query parsing
export function clampInt(n, lo, hi) {
  if (Number.isNaN(n)) return lo;
  return Math.max(lo, Math.min(hi, n));
}
export function parseQuery(search = window.location.search) {
  const params = new URLSearchParams(search);
  return {
    size: clampInt(parseInt(params.get("size") || "6", 10), 2, 12),
    p: params.get("p") || null,
    progressive:
      params.get("progressive") === "1" || params.get("progressive") === "true",
  };
}

// Base64 URL helpers
export function toBase64Url(str) {
  const b = btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return b;
}
export function fromBase64Url(b64url) {
  const pad = "=".repeat((4 - (b64url.length % 4)) % 4);
  const b64 = b64url.replace(/-/g, "+").replace(/_/g, "/") + pad;
  return atob(b64);
}

// Deterministic RNG: hash32 + mulberry32
export function hash32(str) {
  let h = 5381 >>> 0;
  for (let i = 0; i < str.length; i++) {
    h = (((h << 5) + h) ^ str.charCodeAt(i)) >>> 0;
  }
  return h >>> 0;
}
export function mulberry32(a) {
  return function () {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function rngFromSeedString(seedStr) {
  const seed = hash32(seedStr);
  const r = mulberry32(seed);
  return {
    rand: () => r(),
    randint: (min, max) => Math.floor(r() * (max - min + 1)) + min,
    choice: (arr) => arr[Math.floor(r() * arr.length)],
  };
}
export function getDeterministicShuffleCount(size) {
  const rng = rngFromSeedString(`ShuffleCount_v${VERSION}_${size}`);
  const min = size;
  const max = size * size * 2;
  return rng.randint(min, max);
}
export function generateDeterministicSequence(size, moves = null, salt = "") {
  const count = moves != null ? moves : getDeterministicShuffleCount(size);
  const rng = rngFromSeedString(`Benchmark_v${VERSION}_${size}${salt}`);
  const seq = [];
  for (let i = 0; i < count; i++) {
    const type = rng.choice(["row", "column"]);
    const index = rng.randint(1, size);
    const direction =
      type === "row" ? rng.choice(["left", "right"]) : rng.choice(["up", "down"]);
    seq.push({ type, index, direction });
  }
  return seq;
}

// Version string used by MVP (not displayed but kept for parity)
export function makeVersionNow() {
  const d = new Date();
  const pad = (n) => n.toString().padStart(2, "0");
  const MM = pad(d.getMonth() + 1);
  const DD = pad(d.getDate());
  const YYYY = d.getFullYear();
  const HH = pad(d.getHours());
  const mm = pad(d.getMinutes());
  return `${MM}${DD}${YYYY}${HH}${mm}`;
}

// Board helpers
export function solvedLetters(size) {
  const grid = [];
  for (let r = 0; r < size; r++) {
    const ch = String.fromCharCode(65 + r);
    const row = Array.from({ length: size }, () => ch);
    grid.push(row);
  }
  return grid;
}
export function buildTileBoard(size, lettersGrid) {
  let id = 1;
  const board = [];
  for (let r = 0; r < size; r++) {
    const row = [];
    for (let c = 0; c < size; c++) {
      row.push({ id: id++, letter: lettersGrid[r][c] });
    }
    board.push(row);
  }
  return board;
}
export function deepCopyBoard(board) {
  return board.map((row) => row.map((cell) => ({ id: cell.id, letter: cell.letter })));
}
export function isSolved(board) {
  const size = board.length;
  for (let r = 0; r < size; r++) {
    const expected = String.fromCharCode(65 + r);
    for (let c = 0; c < size; c++) {
      if (board[r][c].letter !== expected) return false;
    }
  }
  return true;
}

// One-cell wrap-around shift (matches core/puzzle.py semantics)
export function applyMove(board, move) {
  const n = board.length;
  const idx = move.index - 1;
  if (move.type === "row") {
    if (move.direction === "left") {
      const first = board[idx][0];
      for (let c = 0; c < n - 1; c++) board[idx][c] = board[idx][c + 1];
      board[idx][n - 1] = first;
    } else if (move.direction === "right") {
      const last = board[idx][n - 1];
      for (let c = n - 1; c > 0; c--) board[idx][c] = board[idx][c - 1];
      board[idx][0] = last;
    }
  } else if (move.type === "column") {
    if (move.direction === "up") {
      const first = board[0][idx];
      for (let r = 0; r < n - 1; r++) board[r][idx] = board[r + 1][idx];
      board[n - 1][idx] = first;
    } else if (move.direction === "down") {
      const last = board[n - 1][idx];
      for (let r = n - 1; r > 0; r--) board[r][idx] = board[r - 1][idx];
      board[0][idx] = last;
    }
  }
}
export function applySequence(board, seq) {
  for (const m of seq) applyMove(board, m);
}
