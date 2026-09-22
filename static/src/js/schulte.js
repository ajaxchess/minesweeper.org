/**
 * Schulte Grid — F52
 * Tap numbers 1→N² in order as fast as possible.
 * Six modes, eight board sizes, leaderboard submission.
 */

(function () {
  "use strict";

  // ── State ────────────────────────────────────────────────────────────────────
  let mode      = "normal";
  let boardSize = 5;
  let numbers   = [];      // current value shown in each cell index
  let target    = 1;       // next number to tap
  let total     = 0;       // N²
  let timerMs   = 0;
  let timerInterval = null;
  let started   = false;
  let finished  = false;
  let savedName = localStorage.getItem("sg_name") || "";

  // ── DOM refs ─────────────────────────────────────────────────────────────────
  const board       = document.getElementById("sg-board");
  const timerEl     = document.getElementById("sg-timer");
  const nextLabel   = document.getElementById("sg-next-label");
  const resultPanel = document.getElementById("sg-result");
  const resultTime  = document.getElementById("sg-result-time");
  const submitForm  = document.getElementById("sg-submit-form");
  const nameInput   = document.getElementById("sg-name");
  const resultSub   = document.getElementById("sg-result-sub");
  const submitMsg   = document.getElementById("sg-submit-msg");
  const playAgain   = document.getElementById("sg-play-again");

  // ── Mode / size selectors ────────────────────────────────────────────────────
  document.getElementById("mode-btns").addEventListener("click", function (e) {
    const btn = e.target.closest(".sg-mode-btn");
    if (!btn) return;
    document.querySelectorAll(".sg-mode-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    mode = btn.dataset.mode;
    resetGame();
  });

  document.getElementById("size-btns").addEventListener("click", function (e) {
    const btn = e.target.closest(".sg-size-btn");
    if (!btn) return;
    document.querySelectorAll(".sg-size-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    boardSize = parseInt(btn.dataset.size, 10);
    resetGame();
  });

  // ── Timer helpers ────────────────────────────────────────────────────────────
  function startTimer() {
    if (timerInterval) return;
    const startTime = performance.now() - timerMs;
    timerInterval = setInterval(function () {
      timerMs = performance.now() - startTime;
      timerEl.textContent = (timerMs / 1000).toFixed(2);
    }, 50);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
    timerEl.textContent = (timerMs / 1000).toFixed(2);
  }

  // ── Board construction ───────────────────────────────────────────────────────
  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function buildBoard() {
    total   = boardSize * boardSize;
    numbers = shuffle(Array.from({ length: total }, (_, i) => i + 1));

    board.innerHTML = "";
    board.style.gridTemplateColumns = `repeat(${boardSize}, 1fr)`;

    for (let i = 0; i < total; i++) {
      const cell = document.createElement("div");
      cell.className = "sg-cell";
      cell.dataset.index = i;
      cell.textContent = numbers[i];
      board.appendChild(cell);
    }
  }

  // ── Reset / init ─────────────────────────────────────────────────────────────
  function resetGame() {
    stopTimer();
    timerMs   = 0;
    target    = 1;
    started   = false;
    finished  = false;
    timerEl.textContent = "0.00";
    nextLabel.innerHTML = "Tap <strong>1</strong> to start";
    resultPanel.style.display = "none";
    submitMsg.textContent = "";
    buildBoard();
    if (nameInput && savedName) nameInput.value = savedName;
  }

  // ── Tap handler ──────────────────────────────────────────────────────────────
  board.addEventListener("click", function (e) {
    if (finished) return;
    const cell = e.target.closest(".sg-cell");
    if (!cell) return;

    const idx = parseInt(cell.dataset.index, 10);
    const val = numbers[idx];

    if (val !== target) {
      // Wrong tap — no penalty, just ignore silently
      return;
    }

    // Correct tap
    if (!started) {
      started = true;
      startTimer();
    }

    applyModeEffect(cell, idx);
    target++;

    if (target > total) {
      onComplete();
    } else {
      nextLabel.innerHTML = `Tap <strong>${target}</strong>`;
      if (mode === "mix" || mode === "easy_mix") {
        repositionRemaining();
      }
    }
  });

  // ── Mode visual effects ───────────────────────────────────────────────────────
  function applyModeEffect(cell, idx) {
    switch (mode) {
      case "normal":
        cell.classList.add("sg-cell--correct");
        setTimeout(() => cell.classList.remove("sg-cell--correct"), 300);
        break;

      case "easy":
        cell.classList.add("sg-cell--cleared");   // background gone, number stays
        cell.classList.add("sg-cell--correct");
        setTimeout(() => cell.classList.remove("sg-cell--correct"), 300);
        break;

      case "blind_normal":
        cell.classList.add("sg-cell--blind");     // number gone, tile stays
        break;

      case "blind_easy":
        cell.classList.add("sg-cell--vanished");  // both gone
        break;

      case "easy_mix":
        cell.classList.add("sg-cell--cleared");
        cell.classList.add("sg-cell--correct");
        setTimeout(() => cell.classList.remove("sg-cell--correct"), 300);
        break;

      case "mix":
        cell.classList.add("sg-cell--correct");
        setTimeout(() => cell.classList.remove("sg-cell--correct"), 300);
        break;
    }
  }

  // ── Reposition remaining numbers (Mix / Easy Mix) ────────────────────────────
  function repositionRemaining() {
    // Collect indices of cells that still have active numbers
    const cells = Array.from(board.querySelectorAll(".sg-cell"));
    const activeIndices = [];
    for (let i = 0; i < cells.length; i++) {
      if (!cells[i].classList.contains("sg-cell--cleared") &&
          !cells[i].classList.contains("sg-cell--vanished") &&
          !cells[i].classList.contains("sg-cell--blind")) {
        // For mix mode we shuffle all non-tapped values
        // For easy_mix, cleared cells have no text; we only shuffle visible ones
        if (mode === "mix" || mode === "easy_mix") {
          if (numbers[i] >= target) {
            activeIndices.push(i);
          }
        }
      }
    }

    // Extract active values, shuffle, reassign
    const activeVals = activeIndices.map(i => numbers[i]);
    shuffle(activeVals);
    activeIndices.forEach((cellIdx, j) => {
      numbers[cellIdx] = activeVals[j];
      cells[cellIdx].textContent = activeVals[j];
    });
  }

  // ── Completion ───────────────────────────────────────────────────────────────
  async function onComplete() {
    stopTimer();
    finished = true;
    nextLabel.textContent = "Complete!";

    const secs = (timerMs / 1000).toFixed(2);
    resultTime.textContent = secs + "s";
    resultSub.textContent  = `All ${total} numbers found!`;
    resultPanel.style.display = "flex";

    // Auto-submit for logged-in users
    if (window.SG_USER && window.SG_USER.email) {
      const name = window.SG_USER.display_name || window.SG_USER.name || "Anonymous";
      submitMsg.textContent = "Submitting…";
      submitForm.style.display = "none";
      await submitScore(name);
    } else {
      if (nameInput && savedName) nameInput.value = savedName;
    }
  }

  // ── Score submission ──────────────────────────────────────────────────────────
  async function submitScore(name) {
    const payload = {
      name:        name,
      puzzle_date: window.SG_TODAY,
      mode:        mode,
      board_size:  boardSize,
      time_ms:     Math.round(timerMs),
    };
    try {
      const res = await fetch("/api/schulte-scores", {
        method:  "POST",
        headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
        body:    JSON.stringify(payload),
      });
      if (res.ok) {
        submitMsg.textContent = "Score submitted!";
        submitForm.style.display = "none";
      } else {
        submitMsg.textContent = "Could not submit score.";
        submitForm.style.display = "flex";
      }
    } catch {
      submitMsg.textContent = "Network error — score not saved.";
      submitForm.style.display = "flex";
    }
  }

  submitForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const name = (nameInput.value || "").trim() || "Anonymous";
    savedName = name;
    localStorage.setItem("sg_name", name);
    submitMsg.textContent = "Submitting…";
    submitForm.style.display = "none";
    await submitScore(name);
  });

  // ── Play again ───────────────────────────────────────────────────────────────
  playAgain.addEventListener("click", resetGame);

  // ── Init ─────────────────────────────────────────────────────────────────────
  resetGame();

})();
