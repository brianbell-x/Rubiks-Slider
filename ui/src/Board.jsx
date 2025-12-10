import React, { useEffect, useLayoutEffect, useRef, useState, useMemo } from "react";
import { colorForTile } from "./game.js";

export default function Board({ size, board, onCommitMove }) {
  const boardRef = useRef(null);
  const [dims, setDims] = useState({ width: 0, gap: 6, cell: 0, offset: 0 });

  const computeGap = () => {
    const v = getComputedStyle(document.documentElement).getPropertyValue("--tile-gap");
    const parsed = parseInt(v, 10);
    return Number.isFinite(parsed) ? parsed : 6;
  };

  useLayoutEffect(() => {
    const el = boardRef.current;
    if (!el) return;
    function measure() {
      const width = el.clientWidth || 0;
      const n = size;
      const gap = computeGap();
      // Reserve space for labels (approx 24px on left/top)
      const labelSpace = 24;
      const availWidth = width - labelSpace;
      
      const totalGap = gap * (n + 1);
      const cell = n > 0 ? Math.floor((availWidth - totalGap) / n) : 0;
      // Center the grid within the available space, plus the label offset
      const offset = (availWidth - (n * cell + totalGap)) / 2;
      
      setDims({ width, gap, cell, offset, labelSpace });
    }
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [size]);

  const tiles = useMemo(() => {
    const arr = [];
    const n = size;
    const { gap, cell, offset, labelSpace } = dims;
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const cellObj = board[r][c];
        const left = Math.round(labelSpace + offset + gap + c * (cell + gap));
        const top = Math.round(labelSpace + offset + gap + r * (cell + gap));
        arr.push({
          id: cellObj.id,
          val: cellObj.val,
          r,
          c,
          style: {
            width: `${cell}px`,
            height: `${cell}px`,
            left: `${left}px`,
            top: `${top}px`,
            background: colorForTile(cellObj.val),
          },
        });
      }
    }
    return arr;
  }, [board, size, dims]);

  const labels = useMemo(() => {
    const { gap, cell, offset, labelSpace } = dims;
    if (!cell) return { rows: [], cols: [] };
    
    const rows = [];
    const cols = [];
    const n = size;
    
    for (let i = 0; i < n; i++) {
      // Row labels (left side)
      const rTop = Math.round(labelSpace + offset + gap + i * (cell + gap));
      rows.push({
        text: `R${i + 1}`,
        style: {
          position: 'absolute',
          left: '0px',
          top: `${rTop}px`,
          width: `${labelSpace}px`,
          height: `${cell}px`,
          lineHeight: `${cell}px`,
          textAlign: 'center',
          fontSize: '12px',
          color: '#9aa0a6'
        }
      });

      // Col labels (top side)
      const cLeft = Math.round(labelSpace + offset + gap + i * (cell + gap));
      cols.push({
        text: `C${i + 1}`,
        style: {
          position: 'absolute',
          left: `${cLeft}px`,
          top: '0px',
          width: `${cell}px`,
          height: `${labelSpace}px`,
          lineHeight: `${labelSpace}px`,
          textAlign: 'center',
          fontSize: '12px',
          color: '#9aa0a6'
        }
      });
    }
    return { rows, cols };
  }, [size, dims]);

  const draggingRef = useRef({
    active: false,
    startX: 0,
    startY: 0,
    axis: null, // "x" or "y"
    lockIndex: null, // 1-based
  });

  useEffect(() => {
    const el = boardRef.current;
    if (!el) return;

    function onPointerDown(ev) {
      const target = ev.target.closest(".tile");
      if (!target || !el.contains(target)) return;

      el.setPointerCapture(ev.pointerId);
      const d = draggingRef.current;
      d.active = true;
      d.startX = ev.clientX;
      d.startY = ev.clientY;
      d.axis = null;
      d.lockIndex = null;
    }

    function onPointerMove(ev) {
      const d = draggingRef.current;
      if (!d.active) return;

      const dx = ev.clientX - d.startX;
      const dy = ev.clientY - d.startY;

      if (!d.axis) {
        const absX = Math.abs(dx);
        const absY = Math.abs(dy);
        if (absX > 8 || absY > 8) {
          d.axis = absX >= absY ? "x" : "y";
          const at = document.elementFromPoint(d.startX, d.startY);
          const tile = at ? at.closest(".tile") : null;
          if (tile) {
            const r = parseInt(tile.dataset.r, 10);
            const c = parseInt(tile.dataset.c, 10);
            d.lockIndex = d.axis === "x" ? r + 1 : c + 1; // 1-based
          }
        }
      }
    }

    function onPointerUp(ev) {
      const d = draggingRef.current;
      if (!d.active) return;

      try {
        const dx = ev.clientX - d.startX;
        const dy = ev.clientY - d.startY;

        const n = size;
        const { cell } = dims;
        const threshold = Math.max(18, Math.round(cell * 0.25)) || 18;

        if (d.axis && d.lockIndex != null) {
          if (d.axis === "x" && Math.abs(dx) > threshold) {
            onCommitMove?.({
              type: "row",
              index: d.lockIndex,
              direction: dx < 0 ? "left" : "right",
            });
          } else if (d.axis === "y" && Math.abs(dy) > threshold) {
            onCommitMove?.({
              type: "column",
              index: d.lockIndex,
              direction: dy < 0 ? "up" : "down",
            });
          }
        }
      } finally {
        d.active = false;
        d.axis = null;
        d.lockIndex = null;
        el.releasePointerCapture(ev.pointerId);
      }
    }

    el.addEventListener("pointerdown", onPointerDown);
    el.addEventListener("pointermove", onPointerMove);
    el.addEventListener("pointerup", onPointerUp);
    el.addEventListener("pointercancel", onPointerUp);

    return () => {
      el.removeEventListener("pointerdown", onPointerDown);
      el.removeEventListener("pointermove", onPointerMove);
      el.removeEventListener("pointerup", onPointerUp);
      el.removeEventListener("pointercancel", onPointerUp);
    };
  }, [size, dims, onCommitMove]);

  return (
    <div id="board" className="board" ref={boardRef} aria-label="Sliding puzzle board">
      {labels.rows.map((l, i) => <div key={`r-${i}`} style={l.style}>{l.text}</div>)}
      {labels.cols.map((l, i) => <div key={`c-${i}`} style={l.style}>{l.text}</div>)}
      
      {tiles.map((t) => (
        <div
          key={t.id}
          className="tile"
          style={t.style}
          data-id={t.id}
          data-r={t.r}
          data-c={t.c}
        >
          {t.val}
        </div>
      ))}
    </div>
  );
}
