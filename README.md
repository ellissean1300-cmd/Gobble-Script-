# GobbleScript

GobbleScript is Brainfuck's unstable cousin: an esoteric, tape-based
language where the *program itself* gets hungry, hiccups, burps, and can
permanently eat its own instructions while it runs. Two runs of the same
source file are not guaranteed to do the same thing — and that's the point.
It's an irrational language on purpose.

```
$ python3 gobblescript.py examples/hello_world.gob
Hello World!
```

```
$ python3 gobblescript.py examples/chaos.gob
Hello, Gobblek
N
$ python3 gobblescript.py examples/chaos.gob
Hello, Gobbles
N
```

## The model

- **The Tape** — an infinite line of byte cells (0–255, wrapping), just
  like Brainfuck.
- **The Maw** — the data pointer. Starts at cell 0.
- **Hunger** — a meter that starts at some number (default `20000`) and
  drops by 1 every single instruction executed. If Hunger reaches 0, the
  program **starves** and halts immediately, mid-execution, regardless of
  what it was doing. `+` feeds Hunger back up; `-` drains it faster. Tight
  `-`-heavy programs can genuinely starve to death before finishing — this
  is a real resource you have to manage, not just flavor text.
- **The Source** — unlike Brainfuck, the instruction stream is *mutable*.
  One instruction (`@`) can permanently delete another instruction from it,
  forever, including from inside a loop's body. A loop is not guaranteed to
  look the same on lap 2 as it did on lap 1.

## Commands

| Symbol | Name | Effect |
|---|---|---|
| `>` | Lurch Right | Move the Maw one cell in the current direction |
| `<` | Lurch Left | Move the Maw one cell against the current direction |
| `+` | Feed | Cell +1; Hunger +3 (net Hunger gain after the per-instruction cost) |
| `-` | Starve | Cell −1; Hunger −1 extra (net Hunger loss) |
| `.` | Burp | Output the current cell as a character |
| `,` | Swallow | Read one character of input into the current cell |
| `[` | Open Maw | Enter the loop while the current cell ≠ 0 (else jump past matching `]`) |
| `]` | Close Maw | Jump back to the matching `[` if the current cell ≠ 0 |
| `~` | Indigestion | Add random noise (−5..+5) to the current cell |
| `?` | Hiccup | 50% chance to skip the very next instruction entirely |
| `$` | Belch | Teleport the Maw by a random offset (±12 cells) |
| `%` | Reflux | Flip the meaning of `<` and `>` for the rest of the program |
| `@` | Gobble | **Permanently delete** the next instruction from the source — it can never run again, even on a future pass through a loop |
| `#` | — | Comment: everything to end of line is ignored |

Every character that isn't one of the above is ignored, so you can write
prose freely around your code (or just use `#` comments).

## Why "irrational"

A handful of design choices make GobbleScript intentionally non-deterministic
and occasionally self-destructive, instead of merely minimal like Brainfuck:

1. **Genuine randomness in control flow and data** (`~`, `?`, `$`) means the
   same source can legitimately produce different output, or even take a
   different control path, from one run to the next.
2. **Self-modification that survives loops** (`@`) means static analysis of
   the source doesn't tell you what will actually run — a loop's body is
   re-read fresh from a list that the loop itself might be shrinking.
3. **A finite resource that's tied to control flow** (Hunger) means a
   logically correct program can still fail for an unrelated reason: it
   simply ran out of steam.

None of this is hidden state — it's all visible on the tape, in the Hunger
counter, and in the shrinking source — but it does mean you should treat a
GobbleScript program as a living thing with moods, not a fixed recipe.

## Running it

```
python3 gobblescript.py program.gob [options]

  --hunger N       starting Hunger (default 20000)
  --seed N         random seed, for reproducible chaos
  --input "text"   fixed input string fed to ',' instructions
                    (omit to read live from stdin instead)
  --max-steps N    safety cap on executed instructions (default 5,000,000)
  -v, --verbose    print a step-by-step trace to stderr
```

Exit codes: `0` finished normally, `1` malformed source (unmatched bracket),
`2` starved to death, `3` hit the step safety cap (probably an infinite loop).

## Examples

- `examples/hello_world.gob` — plain deterministic Brainfuck-style code (no
  `~ ? $ % @`), proving the base tape/loop/IO mechanics behave normally
  before any chaos is introduced.
- `examples/chaos.gob` — the same idea, but the last couple of characters
  are jittered by `~`, possibly skipped by `?`, and one is deliberately
  protected from chaos by `@` eating the troublemaker before it can fire.
  Run it a few times in a row and watch the output change.
- `examples/self_eating_loop.gob` — a cautionary tale: a loop that looks
  like it should print 5 digits but only ever prints 2, because `@` inside
  the loop body eats its own closing bracket on the second pass. This one
  *is* fully deterministic — `@` is the one operator with no randomness in
  it, it's just very good at permanently breaking things.

## GUI mode: GobbleScript Canvas

GobbleScript has no GUI commands — like Brainfuck, its only output is "write
one character." `gobblescript_canvas.py` is a separate, self-contained
companion script that gives `.` a different *meaning* instead of adding new
syntax: the tape becomes a grid of pixels.

- The Maw's position (wrapped to fit the grid) picks which pixel is "current."
- `.` paints that pixel using the current cell's value (0–255) as grayscale
  brightness, instead of printing a character.
- `,` reads the most recently pressed key in the window (or `0` if none yet),
  instead of reading stdin.
- Everything else — Hunger, `@` permanently deleting instructions, `~` `?`
  `$` `%` — works exactly as documented above.

```
python3 gobblescript_canvas.py examples/ring.gob

  --width N / --height N   grid size in pixels (default 32x32)
  --scale N                screen pixels per grid cell (default 14)
  --hunger N, --seed N, --max-steps N   same meaning as the text interpreter
  --speed N                instructions executed per animation frame (default 200)
  --delay N                milliseconds between frames (default 1)
```

It opens a window and draws progressively, frame by frame, rather than
computing the whole image and showing it only at the end — so you can watch
a GobbleScript program "think." `examples/ring.gob` draws a simple glowing
ring as a sanity check that your setup works.

Requires Python's built-in `tkinter` (bundled with the standard Windows/Mac
installers; on Linux, `sudo apt install python3-tk` if it's missing).

## A starter exercise

Try writing a GobbleScript program that prints your name reliably even
under random Hunger budgets — you'll need to balance `+` (which feeds
Hunger) against how much `-`, `[`, and `]` work the loop body does. Then
try a second version that's *deliberately* fragile: one bad `@` placement
inside a loop, and watch it die a different way every time you tweak the
seed.
