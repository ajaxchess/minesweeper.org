# How to Play Minesweeper

Minesweeper is a classic logic puzzle where your goal is to uncover every safe cell on a grid without clicking on a hidden mine. It looks simple, but beneath the surface lies a game of deduction, pattern recognition, and careful reasoning. This guide will teach you everything you need to know to play minesweeper — from the very basics to strategies that will help you climb the leaderboard.

## The Basics

A minesweeper board is a grid of covered cells. Some of those cells contain hidden mines. Your job is to reveal all the cells that don't contain mines. If you click on a mine, the game is over.

When you reveal a cell, one of two things happens:

- **A number appears.** This number tells you exactly how many mines are hidden in the eight cells immediately surrounding it (above, below, left, right, and the four diagonals). A "1" means one of its eight neighbors is a mine. A "3" means three of its neighbors are mines. This is the core information you use to solve the puzzle.
- **A blank space opens up.** If a revealed cell has zero neighboring mines, it appears blank and the game automatically reveals all of its neighbors too. This can cascade outward, opening up large sections of the board at once. These cascading openings are how most games begin — your first click will never be a mine, and it usually opens up a region that gives you enough information to start reasoning.

## Controls

On Minesweeper.org, the controls are straightforward:

- **Left-click** on a covered cell to reveal it.
- **Right-click** on a covered cell to place a flag. Flags mark cells you believe contain mines. Right-click again to remove a flag. On mobile, you can tap the flag button to toggle flag mode, then tap cells to flag them.
- **Click the smiley face** (🙂) to reset the board and start a new game.

The mine counter in the top left shows how many mines remain unflagged. The timer in the top right tracks your solving time in seconds.

## How to Use the Numbers

The numbers are everything in minesweeper. Learning to read them quickly and accurately is what separates beginners from experienced players.

Consider a cell showing "1" at the edge of a revealed region. It has eight neighbors, but suppose five of them are already revealed and safe. That means the one mine must be among the three remaining covered cells. If two of those covered cells are also accounted for by other numbers, you can narrow it down to exactly one cell — that's your mine. Flag it.

The reverse logic is just as important: if a numbered cell already has all of its mines accounted for (for example, a "1" that already has one flagged neighbor), then every other covered neighbor of that cell is guaranteed safe. You can click them all without risk.

This back-and-forth reasoning — identifying mines and identifying safe cells — is the fundamental loop of minesweeper.

## Common Patterns to Recognize

As you play more, you'll start to recognize certain number arrangements instantly. Here are some of the most common:

**The 1-1 pattern along a wall.** When two "1" cells sit side by side along the edge of an opening, and they share covered neighbors, the mine must be in the cell that is a neighbor to both of them. The cells that only neighbor one of the two 1s are safe.

**The 1-2-1 pattern.** In a row of three numbers reading 1-2-1 along a boundary, the mine for the "2" is in the middle covered cell, and the outer covered cells are safe.

**The 1-2-2-1 pattern.** Similar to the above but extended. Once you recognize these patterns, you can solve entire sections of the board at a glance rather than reasoning through each cell individually.

**Satisfied numbers.** Any number whose flag count already matches its value is "satisfied" — all remaining covered neighbors are safe. Scanning for satisfied numbers is one of the fastest ways to make progress.

## Beginner Strategy

If you're new to minesweeper, start with the Beginner board (10×10 with 10 mines). Here's a simple approach:

**Start by clicking near the center of the board.** Your first click is always safe, and clicking near the center gives you the best chance of a large opening that reveals lots of numbers to work with.

**Look for easy deductions first.** After the board opens up, scan for cells where the logic is obvious — a "1" with only one covered neighbor means that neighbor is definitely a mine. Flag it. A "1" that already has a flag next to it means all its other covered neighbors are safe. Reveal them.

**Work from what you know outward.** Each flag you place or safe cell you reveal gives you new information. Follow the chain of logic from the edges of the revealed area, working outward into the unknown.

**Don't guess if you don't have to.** On Minesweeper.org, you can enable No Guess mode, which guarantees that every puzzle is fully solvable through logic alone. With No Guess mode on, there is always a deduction available somewhere on the board — you never need to take a 50/50 chance.

**Use flags generously.** Flagging confirmed mines makes it much easier to count remaining mines around numbered cells. Some advanced players skip flagging to save time, but as a beginner, flags are your best friend.

## Difficulty Levels

Minesweeper.org offers three standard difficulty levels plus a custom option:

- **Beginner:** 10×10 grid with 10 mines. A great starting point for learning the mechanics and building confidence.
- **Intermediate:** 16×16 grid with 40 mines. A significant step up — the board is larger and mine density is higher, requiring more careful reasoning and better pattern recognition.
- **Expert:** 30×16 grid with 99 mines. The classic competitive format. Expert boards are dense with mines and demand fast, accurate deduction. Most competitive minesweeper times are measured on Expert.
- **Custom:** Set your own rows, columns, and mine count. Great for practicing at a specific difficulty or creating unusual challenges.

## No Guess Mode

One of the most frustrating aspects of traditional minesweeper is the endgame coin flip — reaching a point where no amount of logic can tell you which cell is the mine, and you just have to guess. Minesweeper.org solves this problem with No Guess mode.

When No Guess is enabled, every board that is generated is guaranteed to be solvable through pure logic. There will always be at least one safe deduction available at every step of the puzzle. This means that if you lose, it was because you made a reasoning error — not because the game forced you into an impossible situation. No Guess mode makes minesweeper a true test of logic.

## Game Modes Beyond Classic

Minesweeper.org offers several game modes that go beyond the traditional experience:

### Rush

Rush is an endless, fast-paced mode where new rows of mines continuously push up from the bottom of the board. Your goal is to survive as long as possible by flagging all the mines in each row to clear it. Hitting a mine adds two penalty rows, making the board even harder to manage. Rush is pure speed and pressure — great for players who want a more action-oriented minesweeper experience.

### Duel

Duel is a real-time 1v1 multiplayer mode. You and an opponent both play the same board simultaneously. Scoring is based on tiles revealed plus a time bonus calculated from your speed and the percentage of the board you've uncovered. Share the link with a friend, hit Start, and race to see who can clear the board faster.

### PvP

PvP is another multiplayer mode for players who want competitive head-to-head minesweeper.

### Tentaizu

Tentaizu is a logic puzzle that uses minesweeper-style number clues but plays very differently. You're given a 7×7 grid with some numbers already revealed. There are exactly 10 hidden mines, and the numbers tell you how many mines are adjacent to that cell — just like in minesweeper. But instead of clicking to reveal cells, you cycle through three states: flag as a mine (💣), mark as safe (✓), or leave as unknown (?). The game doesn't end on a wrong guess — you keep refining until you've correctly identified all 10 mines. A daily Tentaizu puzzle is available each day, plus a random mode for extra practice.

### Variants: Cylinder and Toroid

These variants change the shape of the board itself. In Cylinder mode, the left and right edges of the board are connected, so a mine on the far right side affects cells on the far left. In Toroid mode, all four edges wrap around — left connects to right, and top connects to bottom — so you're effectively playing on the surface of a donut. Every cell on a toroid board has exactly eight neighbors, even corner cells. These wrapping edges change familiar patterns in surprising ways and force you to rethink strategies you take for granted on a flat board.

### Quests

Quests give you daily and seasonal goals to work toward. A new daily quest appears every 24 hours, and seasonal quests run for the entire month. Completing enough quests earns you rewards, including the ability to permanently disable ads on your device by maintaining a 20-day daily quest streak or completing 10 daily quests in a season.

## Tips for Improving Your Speed

Once you're comfortable with the logic, the next challenge is getting faster. Here are some tips:

**Learn to chord.** Chording (also called double-clicking or simultaneous clicking) is a technique where you click on a revealed number that already has all its mines flagged. This instantly reveals all remaining covered neighbors of that cell. It saves enormous amounts of time compared to clicking each safe cell individually.

**Scan, don't stare.** Experienced players keep their eyes moving across the board, scanning for easy deductions and satisfied numbers rather than fixating on one difficult spot. If you get stuck in one area, move to another — you'll often find easier progress elsewhere that eventually gives you the information you need.

**Reduce unnecessary flagging.** While flags are helpful for beginners, competitive players often skip flagging obvious mines to save time. If you can see that a cell is a mine and don't need the flag to help you reason about surrounding cells, you can leave it unflagged and move on.

**Practice on Intermediate before jumping to Expert.** Intermediate boards build your pattern recognition and speed in a less punishing environment. Once you can consistently solve Intermediate boards in under two minutes, you're ready for Expert.

## The Leaderboard

Minesweeper.org has a global leaderboard that tracks the fastest times for each difficulty level. Scores reset daily at midnight UTC, so every day is a fresh competition. Sign in with Google to save your times and see how you stack up against other players around the world.

## Ready to Play?

Head back to the [Beginner board](https://minesweeper.org/) and start playing. Remember: every number is a clue, every flag is progress, and with No Guess mode on, every puzzle has a solution. Good luck!
