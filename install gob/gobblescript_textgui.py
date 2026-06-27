#!/usr/bin/env python3
"""
GobbleScript Text GUI -- shows a GobbleScript program's printed output in a
window, instead of a console that flashes open and shut (or stays open and
clutters your taskbar with a black box). Same language, same semantics as
gobblescript.py -- '.' still means "print a character" -- this just renders
that output somewhere nicer, and progressively as the program runs rather
than all at once at the end.

You can also type into the window while a program runs: each keypress feeds
exactly one ',' (there's no line buffering -- it's one key in, one ',' out,
same as gobblescript.py's stdin handling, just sourced from the window
instead of a terminal).

This is intentionally a SEPARATE, self-contained file, just like
gobblescript_canvas.py -- it doesn't import or modify gobblescript.py.

Usage:
    python3 gobblescript_textgui.py program.gob
    python3 gobblescript_textgui.py program.gob --hunger 5000 --seed 7
"""

import sys
import random
import argparse
import tkinter as tk
from tkinter import font as tkfont

ACTIVE = set(">.<+-.,[]~?$%@")
DEFAULT_HUNGER = 20000
FEED_AMOUNT = 3
STARVE_PENALTY = 1
BURP_RANGE = (-5, 5)
BELCH_RANGE = 12
DEFAULT_MAX_STEPS = 5_000_000


class GobbleError(Exception):
    """Malformed GobbleScript source (e.g. an unmatched bracket)."""


class TextGobbleMachine:
    """Same core model as gobblescript.py / gobblescript_canvas.py. '.'
    calls on_char(ch) instead of writing to stdout; ',' reads from a key
    queue fed by the GUI instead of real stdin. Steps one instruction at a
    time via step() so a GUI event loop can animate it."""

    def __init__(self, source_text, hunger=DEFAULT_HUNGER, seed=None,
                 max_steps=DEFAULT_MAX_STEPS):
        if seed is not None:
            random.seed(seed)
        self.source = self._tokenize(source_text)
        self.tape = {}
        self.pos = 0
        self.direction = 1
        self.hunger = hunger
        self.ip = 0
        self.max_steps = max_steps
        self.steps = 0
        self.halted_reason = None
        self.key_queue = []   # fed by the GUI's key handler
        self.on_char = None   # callback(ch) set by the App

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
        self.key_queue.append(code)

    def step(self):
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
            if self.on_char:
                self.on_char(chr(self.cell()))
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


class TextApp:
    """The tkinter window: a scrollable text area, a status line, and a
    Restart button (handy since chaos ops mean reruns can differ)."""

    BG = "#1c1b22"
    FG = "#F4F1EA"
    MUTED = "#A79FB0"
    ERROR = "#FF6B5B"
    BTN_BG = "#2A1418"

    def __init__(self, source_text, hunger=DEFAULT_HUNGER, seed=None,
                 max_steps=DEFAULT_MAX_STEPS, delay_ms=1, steps_per_tick=40,
                 title="GobbleScript"):
        self.source_text = source_text
        self.hunger0 = hunger
        self.seed = seed
        self.max_steps = max_steps
        self.delay_ms = delay_ms
        self.steps_per_tick = steps_per_tick

        self.root = tk.Tk()
        self.root.title(title)
        self.root.configure(bg=self.BG)
        self.root.geometry("640x420")

        mono = tkfont.Font(family="Consolas", size=12)
        if mono.actual("family").lower() != "consolas":
            mono = tkfont.Font(family="Courier New", size=12)

        bar = tk.Frame(self.root, bg=self.BG)
        bar.pack(side="bottom", fill="x")
        self.status = tk.Label(bar, text="running...", anchor="w",
                                fg=self.MUTED, bg=self.BG,
                                font=("monospace", 10))
        self.status.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        self.restart_btn = tk.Button(bar, text="Restart", command=self.restart,
                                      bg=self.BTN_BG, fg=self.FG, relief="flat",
                                      activebackground="#3a1c22",
                                      activeforeground=self.FG, padx=10)
        self.restart_btn.pack(side="right", padx=8, pady=6)

        # packed AFTER the bottom bar, so the bar keeps its space and the
        # text area expands to fill whatever's left -- not the other way
        # around (pack() gives space to widgets in the order they're
        # packed, so an expand=True widget packed first claims everything).
        self.text = tk.Text(self.root, bg=self.BG, fg=self.FG,
                             insertbackground=self.FG, font=mono,
                             wrap="word", relief="flat", padx=10, pady=10,
                             borderwidth=0, highlightthickness=0)
        self.text.pack(fill="both", expand=True)
        self.text.configure(state="disabled")

        self.root.bind("<Key>", self._on_key)
        self.machine = None
        self.start()

    def start(self):
        self.machine = TextGobbleMachine(
            self.source_text, hunger=self.hunger0, seed=self.seed,
            max_steps=self.max_steps,
        )
        self.machine.on_char = self._append_char
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self.status.configure(fg=self.MUTED)
        self.root.after(self.delay_ms, self._tick)

    def restart(self):
        self.start()

    def _append_char(self, ch):
        self.text.configure(state="normal")
        self.text.insert("end", ch)
        self.text.see("end")
        self.text.configure(state="disabled")

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
            self.status.config(text=f"malformed source: {e}", fg=self.ERROR)
            return  # don't reschedule

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
        description="Run a GobbleScript program and show its text output "
                     "in a window instead of a console."
    )
    parser.add_argument("file", help="path to a .gob source file")
    parser.add_argument("--hunger", type=int, default=DEFAULT_HUNGER)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument("--speed", type=int, default=40,
                         help="instructions executed per animation frame")
    parser.add_argument("--delay", type=int, default=1,
                         help="milliseconds between animation frames")
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    app = TextApp(
        source, hunger=args.hunger, seed=args.seed, max_steps=args.max_steps,
        delay_ms=args.delay, steps_per_tick=args.speed,
        title=f"GobbleScript -- {args.file}",
    )
    app.run()


if __name__ == "__main__":
    main()
