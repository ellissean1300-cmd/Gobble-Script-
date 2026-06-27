#!/usr/bin/env python3
"""
GobbleScript Canvas -- a GUI companion to gobblescript.py.

GobbleScript itself has no notion of windows, pixels, or widgets -- like
Brainfuck, its only output is "write one character." This script doesn't
add GUI commands to the language; instead it gives `.` a different *meaning*.

The tape becomes a grid of pixels instead of a string of characters:

  * The Maw's position (mod width*height) selects which pixel is "current."
  * `.` doesn't print the current cell -- it paints the current pixel using
    the current cell's value (0-255) as grayscale brightness.
  * `,` doesn't read stdin -- it reads the most recent key pressed in the
    window (or 0 if nothing's been pressed yet), so a program can react to
    you typing while it runs.

Everything else -- Hunger, Gobble (@) permanently deleting instructions,
Burp (~), Hiccup (?), Belch ($), Reflux (%) -- works exactly like the base
language. A GobbleScript Canvas program can still starve to death, still eat
its own loop out from under itself, and still behave differently from one
run to the next.

This is intentionally a SEPARATE, self-contained file. It doesn't import or
modify gobblescript.py, so it'll drop into any folder that already has your
GobbleScript project in it without touching anything you've already set up.

Usage:
    python3 gobblescript_canvas.py picture.gob
    python3 gobblescript_canvas.py picture.gob --width 32 --height 32 --scale 14
    python3 gobblescript_canvas.py picture.gob --speed 400 --seed 7

Requires: Python's built-in tkinter (ships with the standard Windows/Mac
Python installers; on Linux you may need `sudo apt install python3-tk`).
"""

import sys
import random
import argparse
import tkinter as tk

ACTIVE = set(">.<+-.,[]~?$%@")
DEFAULT_HUNGER = 20000
FEED_AMOUNT = 3
STARVE_PENALTY = 1
BURP_RANGE = (-5, 5)
BELCH_RANGE = 12
DEFAULT_MAX_STEPS = 5_000_000


class GobbleError(Exception):
    """Malformed GobbleScript source (e.g. an unmatched bracket)."""


class CanvasGobbleMachine:
    """Same core model as gobblescript.py (tape, Maw, Hunger, self-deleting
    source) but '.' paints a pixel and ',' reads a key instead of doing
    console I/O. Drives one instruction at a time via step(), so a GUI
    event loop can animate it instead of running it all at once."""

    def __init__(self, source_text, width, height, hunger=DEFAULT_HUNGER,
                 seed=None, max_steps=DEFAULT_MAX_STEPS):
        if seed is not None:
            random.seed(seed)
        self.source = self._tokenize(source_text)
        self.width = width
        self.height = height
        self.cells_total = width * height
        self.tape = {}
        self.pos = 0
        self.direction = 1
        self.hunger = hunger
        self.ip = 0
        self.max_steps = max_steps
        self.steps = 0
        self.halted_reason = None
        self.key_queue = []          # fed by the GUI's key handler
        self.on_pixel = None         # callback(x, y, value) set by the App

    @staticmethod
    def _tokenize(text):
        lines = text.split("\n")
        kept = []
        for line in lines:
            if "#" in line:
                line = line[: line.index("#")]
            kept.append(line)
        code = "\n".join(kept)
        return [ch for ch in code if ch in ACTIVE]

    def cell(self):
        return self.tape.get(self.pos, 0)

    def set_cell(self, value):
        self.tape[self.pos] = value % 256

    def _match_forward(self):
        depth = 1
        i = self.ip + 1
        n = len(self.source)
        while i < n:
            if self.source[i] == "[":
                depth += 1
            elif self.source[i] == "]":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        raise GobbleError("Unmatched '[' -- the Gob choked on an open loop")

    def _match_backward(self):
        depth = 1
        i = self.ip - 1
        while i >= 0:
            if self.source[i] == "]":
                depth += 1
            elif self.source[i] == "[":
                depth -= 1
                if depth == 0:
                    return i
            i -= 1
        raise GobbleError("Unmatched ']' -- the Gob hiccuped on a stray close")

    def feed_key(self, code):
        """Called by the GUI whenever a key is pressed."""
        self.key_queue.append(code)

    def step(self):
        """Execute exactly one instruction. Returns True if the machine can
        keep going, False if it has halted (check .halted_reason why)."""
        if self.ip >= len(self.source):
            self.halted_reason = "finished"
            return False
        if self.hunger <= 0:
            self.halted_reason = "starved"
            return False
        if self.steps >= self.max_steps:
            self.halted_reason = "step-limit"
            return False

        instr = self.source[self.ip]
        self.steps += 1
        self.hunger -= 1
        advance = 1

        if instr == ">":
            self.pos += self.direction
        elif instr == "<":
            self.pos -= self.direction
        elif instr == "+":
            self.set_cell(self.cell() + 1)
            self.hunger += FEED_AMOUNT
        elif instr == "-":
            self.set_cell(self.cell() - 1)
            self.hunger -= STARVE_PENALTY
        elif instr == ".":
            idx = self.pos % self.cells_total
            x, y = idx % self.width, idx // self.width
            if self.on_pixel:
                self.on_pixel(x, y, self.cell())
        elif instr == ",":
            self.set_cell(self.key_queue.pop(0) if self.key_queue else 0)
        elif instr == "[":
            if self.cell() == 0:
                self.ip = self._match_forward()
        elif instr == "]":
            if self.cell() != 0:
                self.ip = self._match_backward()
        elif instr == "~":
            self.set_cell(self.cell() + random.randint(*BURP_RANGE))
        elif instr == "?":
            if random.random() < 0.5:
                advance = 2
        elif instr == "$":
            self.pos += random.randint(-BELCH_RANGE, BELCH_RANGE)
        elif instr == "%":
            self.direction *= -1
        elif instr == "@":
            if self.ip + 1 < len(self.source):
                del self.source[self.ip + 1]

        self.ip += advance
        return True


class CanvasApp:
    """The tkinter window: a pixel grid, a status line, and an animation
    loop that calls machine.step() a batch at a time so the picture draws
    progressively instead of popping in all at once at the end."""

    BG = "#1c1b22"
    FG = "#a79fb0"

    def __init__(self, machine, scale=14, delay_ms=1, steps_per_tick=200,
                 title="GobbleScript Canvas"):
        self.machine = machine
        self.scale = scale
        self.delay_ms = delay_ms
        self.steps_per_tick = steps_per_tick

        self.root = tk.Tk()
        self.root.title(title)
        self.root.configure(bg=self.BG)

        w, h = machine.width * scale, machine.height * scale
        self.canvas = tk.Canvas(self.root, width=w, height=h,
                                 bg=self.BG, highlightthickness=0)
        self.canvas.pack()

        self.status = tk.Label(self.root, text="running...", anchor="w",
                                fg=self.FG, bg=self.BG, font=("monospace", 10))
        self.status.pack(fill="x")

        self.root.bind("<Key>", self._on_key)
        machine.on_pixel = self._draw_pixel
        self.root.after(self.delay_ms, self._tick)

    def _draw_pixel(self, x, y, value):
        color = f"#{value:02x}{value:02x}{value:02x}"
        x0, y0 = x * self.scale, y * self.scale
        self.canvas.create_rectangle(
            x0, y0, x0 + self.scale, y0 + self.scale, fill=color, outline=""
        )

    def _on_key(self, event):
        code = ord(event.char) if event.char else 0
        if code:
            self.machine.feed_key(code)

    def _tick(self):
        running = True
        try:
            for _ in range(self.steps_per_tick):
                running = self.machine.step()
                if not running:
                    break
        except GobbleError as e:
            self.status.config(text=f"malformed source: {e}", fg="#FF6B5B")
            return  # don't reschedule -- nothing more this program can do

        if running:
            self.status.config(
                text=f"running -- step {self.machine.steps}, "
                     f"hunger {self.machine.hunger}"
            )
            self.root.after(self.delay_ms, self._tick)
        else:
            self.status.config(
                text=f"halted: {self.machine.halted_reason} "
                     f"after {self.machine.steps} steps "
                     f"(hunger left: {self.machine.hunger})"
            )

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="Run a GobbleScript program in a pixel-canvas window "
                     "instead of as text."
    )
    parser.add_argument("file", help="path to a .gob source file")
    parser.add_argument("--width", type=int, default=32, help="grid width in pixels")
    parser.add_argument("--height", type=int, default=32, help="grid height in pixels")
    parser.add_argument("--scale", type=int, default=14, help="screen pixels per grid cell")
    parser.add_argument("--hunger", type=int, default=DEFAULT_HUNGER)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument("--speed", type=int, default=200,
                         help="instructions executed per animation tick")
    parser.add_argument("--delay", type=int, default=1,
                         help="milliseconds between animation ticks")
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    machine = CanvasGobbleMachine(
        source, args.width, args.height,
        hunger=args.hunger, seed=args.seed, max_steps=args.max_steps,
    )
    app = CanvasApp(
        machine, scale=args.scale, delay_ms=args.delay,
        steps_per_tick=args.speed,
        title=f"GobbleScript Canvas -- {args.file}",
    )
    app.run()


if __name__ == "__main__":
    main()
