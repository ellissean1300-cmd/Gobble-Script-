<p align="center">
  <img src="logo.svg" alt="GobbleScript logo" width="440">
</p>

<p align="center">
  <strong>GobbleScript</strong><br>
  <em>Brainfuck's unstable, self-eating cousin.</em>
</p>

---

# GobbleScript

GobbleScript is Brainfuck's unstable cousin: an esoteric, tape-based language where the **program itself** gets hungry, hiccups, burps, and can permanently eat its own instructions while it runs.

Two runs of the same source file are **not guaranteed to do the same thing**—and that's the point.

```bash
$ python3 gobblescript.py examples/hello_world.gob
Hello World!
```

```bash
$ python3 gobblescript.py examples/chaos.gob
Hello, Gobblek
N

$ python3 gobblescript.py examples/chaos.gob
Hello, Gobbles
N
```

---

# The Model

GobbleScript is built around four ideas.

### The Tape

An infinite line of byte cells (0–255, wrapping), just like Brainfuck.

### The Maw

The data pointer.

It begins at cell `0`.

### Hunger

A resource meter that begins at a configurable value (default `20000`).

Every instruction executed costs **1 Hunger**.

When Hunger reaches **0**, the program immediately starves and halts, even if it is halfway through a loop or printing output.

Some instructions affect Hunger further:

* `+` feeds the program (+3 Hunger after the instruction cost)
* `-` drains it even faster
* Long-running programs must manage Hunger carefully

Unlike Brainfuck, computation is limited by a real resource.

### The Source

The source code is mutable.

The `@` instruction permanently removes instructions from the running program itself.

A loop can literally shrink while it is executing.

---

# Commands

| Symbol | Name        | Effect                                                            |
| :----: | ----------- | ----------------------------------------------------------------- |
|   `>`  | Lurch Right | Move the Maw one cell in the current direction                    |
|   `<`  | Lurch Left  | Move the Maw one cell against the current direction               |
|   `+`  | Feed        | Current cell +1; Hunger +3 (net gain after execution cost)        |
|   `-`  | Starve      | Current cell −1; Hunger −1 extra                                  |
|   `.`  | Burp        | Output current cell as a character                                |
|   `,`  | Swallow     | Read one byte of input into the current cell                      |
|   `[`  | Open Maw    | Begin loop while current cell ≠ 0                                 |
|   `]`  | Close Maw   | Jump back if current cell ≠ 0                                     |
|   `~`  | Indigestion | Add random noise (−5…+5) to the current cell                      |
|   `?`  | Hiccup      | 50% chance to skip the next instruction                           |
|   `$`  | Belch       | Teleport the Maw by a random offset (±12 cells)                   |
|   `%`  | Reflux      | Reverse the meaning of `<` and `>` for the remainder of execution |
|   `@`  | Gobble      | Permanently delete the next instruction from the source           |
|   `#`  | Comment     | Ignore everything until the end of the line                       |

Any character not listed above is ignored, making it easy to write comments or prose directly inside programs.

---

# Why "Irrational"?

GobbleScript intentionally refuses to be a perfectly logical language.

## Randomness

Instructions like `~`, `?`, and `$` introduce genuine randomness.

The exact same program may:

* print different output
* follow different execution paths
* terminate differently

without any bugs in the interpreter.

---

## Self-modifying code

`@` permanently deletes instructions from the source.

Unlike temporary jumps or runtime patches, these changes persist for the remainder of execution.

Even loop bodies are reread from the modified source each iteration.

Static analysis quickly becomes unreliable.

---

## Hunger

Programs don't simply need to be correct.

They need enough energy to survive.

A perfectly valid algorithm can fail because it literally starves before reaching the end.

Managing Hunger becomes another part of programming.

---

# Running

```text
python3 gobblescript.py program.gob [options]

  --hunger N
      Starting Hunger (default 20000)

  --seed N
      Random seed for reproducible chaos

  --input "text"
      Feed fixed input to ',' instructions

  --max-steps N
      Maximum executed instructions
      (default 5,000,000)

  -v, --verbose
      Print a complete execution trace
```

Exit codes:

| Code | Meaning                               |
| ---: | ------------------------------------- |
|    0 | Finished normally                     |
|    1 | Malformed source (unmatched brackets) |
|    2 | Starved to death                      |
|    3 | Maximum instruction limit reached     |

---

# Example Programs

### hello_world.gob

A completely deterministic Brainfuck-style program.

No chaos operators are used.

Useful for confirming the interpreter behaves correctly.

---

### chaos.gob

A demonstration of GobbleScript's random instructions.

The final characters are influenced by:

* `~`
* `?`

while another dangerous instruction is safely removed by `@` before it can execute.

Run it multiple times to see different results.

---

### self_eating_loop.gob

A deterministic example of self-modifying code.

The loop appears as though it should execute five times.

Instead, `@` eventually consumes part of the loop itself, permanently changing the program.

The result is only two outputs before execution changes forever.

---

# GobbleScript Canvas

GobbleScript also includes a graphical interpreter.

Instead of printing characters, the `.` instruction paints pixels.

Everything else remains identical.

* Hunger still matters.
* Randomness still happens.
* Instructions can still delete themselves.

The tape is interpreted as a pixel grid.

* Maw position selects a pixel.
* Cell value becomes grayscale brightness.
* `.` paints.
* `,` reads the most recent keyboard input instead of stdin.

Run it with:

```bash
python3 gobblescript_canvas.py examples/ring.gob
```

Options:

```text
--width N
--height N
    Canvas dimensions (default 32×32)

--scale N
    Window scaling (default 14)

--speed N
    Instructions per animation frame
    (default 200)

--delay N
    Milliseconds between frames
    (default 1)

--hunger N
--seed N
--max-steps N
    Same meaning as the text interpreter
```

The interpreter renders progressively so you can watch GobbleScript "think" as it executes.

Requires Python's built-in `tkinter`.

Linux users may need:

```bash
sudo apt install python3-tk
```

---

# Starter Challenge

Try writing a GobbleScript program that prints your name reliably under varying Hunger budgets.

You'll need to balance:

* feeding with `+`
* work performed inside loops
* total instruction count

Once you've succeeded, try writing a second version that's intentionally fragile.

Place a single `@` inside a loop and watch how tiny changes in execution produce wildly different behavior.

---

# Philosophy

GobbleScript isn't designed to be practical.

It's designed to feel alive.

Programs become exhausted.

They stumble.

They forget parts of themselves.

Sometimes they succeed.

Sometimes they starve.

Sometimes they eat the very instruction that would have saved them.

Programming GobbleScript is less like writing a recipe and more like raising a particularly chaotic pet.

Happy gobbling.
