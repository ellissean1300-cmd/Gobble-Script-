#!/usr/bin/env python3
"""
GobbleScript (.gob) -- an irrational, self-devouring esoteric language.

GobbleScript is Brainfuck's unstable cousin. It has the same tape-and-pointer
skeleton, but:

  * The program gets HUNGRY. Every instruction costs Hunger to run. If Hunger
    hits zero, the program starves to death mid-execution -- even if the logic
    was perfectly correct.
  * The program can EAT ITSELF. The `@` instruction permanently deletes the
    next instruction from the source, forever -- including from inside loops.
    A GobbleScript program is not guaranteed to look the same on its 2nd pass
    through a loop as it did on its 1st.
  * The program HICCUPS, BURPS, and BELCHES. `?`, `~`, and `$` inject genuine
    randomness into control flow, cell values, and the pointer. Two runs of
    the same program are not guaranteed to do the same thing. That's the
    "irrational" part -- it is not deterministic, and it is not supposed to be.

See README.md for the full language spec and command table.

Usage:
    python3 gobblescript.py program.gob
    python3 gobblescript.py program.gob --hunger 5000 --seed 42
    python3 gobblescript.py program.gob --input "hello"
"""

import sys
import random
import argparse

VALID_SYMBOLS = set(">/<+-.,[]~?$%@")
# NOTE: '/' is reserved/unused on purpose -- left out of the active symbol
# set below so it's harmless if it ever leaks into source; only the symbols
# in ACTIVE are dispatched on.
ACTIVE = set(">.<+-.,[]~?$%@") - {"/"}

DEFAULT_HUNGER = 20000
FEED_AMOUNT = 3          # net effect of '+' on hunger is (+FEED_AMOUNT - 1)
STARVE_PENALTY = 1       # net effect of '-' on hunger is (-1 - STARVE_PENALTY)
BURP_RANGE = (-5, 5)
BELCH_RANGE = 12
DEFAULT_MAX_STEPS = 5_000_000


class GobbleError(Exception):
    """Raised for malformed GobbleScript source (e.g. unmatched brackets)."""


class GobbleMachine:
    """The runtime: a tape, a pointer (the Maw), a Hunger meter, and a
    self-modifying instruction stream."""

    def __init__(self, source_text, hunger=DEFAULT_HUNGER, verbose=False,
                 input_text=None, seed=None, max_steps=DEFAULT_MAX_STEPS):
        if seed is not None:
            random.seed(seed)
        self.source = self._tokenize(source_text)
        self.tape = {}
        self.pos = 0
        self.direction = 1          # flipped by '%'
        self.hunger = hunger
        self.ip = 0
        self.verbose = verbose
        self.max_steps = max_steps
        self.steps = 0
        self.halted_reason = None
        # If input_text is given, feed from it character by character.
        # Otherwise fall back to live stdin (one char per ',').
        self.input_buffer = list(input_text) if input_text is not None else None

    @staticmethod
    def _tokenize(text):
        """Strip '#' comments (to end of line) and keep only real symbols."""
        lines = text.split("\n")
        kept = []
        for line in lines:
            if "#" in line:
                line = line[: line.index("#")]
            kept.append(line)
        code = "\n".join(kept)
        return [ch for ch in code if ch in ACTIVE]

    # -- tape access -----------------------------------------------------
    def cell(self):
        return self.tape.get(self.pos, 0)

    def set_cell(self, value):
        self.tape[self.pos] = value % 256

    # -- bracket matching (re-scanned each time: the source can mutate!) -
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

    # -- input -------------------------------------------------------------
    def _getchar(self):
        if self.input_buffer is not None:
            if self.input_buffer:
                return ord(self.input_buffer.pop(0))
            return 0
        ch = sys.stdin.read(1)
        return ord(ch) if ch else 0

    # -- main loop -----------------------------------------------------
    def run(self):
        while self.ip < len(self.source):
            if self.hunger <= 0:
                self.halted_reason = "starved"
                break
            if self.steps >= self.max_steps:
                self.halted_reason = "step-limit"
                break

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
                sys.stdout.write(chr(self.cell()))
                sys.stdout.flush()
            elif instr == ",":
                self.set_cell(self._getchar())
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
            # comments are already stripped, no else-branch needed

            if self.verbose:
                self._debug(instr)

            self.ip += advance

        if self.halted_reason is None:
            self.halted_reason = "finished"
        return self.halted_reason

    def _debug(self, instr):
        sys.stderr.write(
            f"\n[step {self.steps:>6}] ip={self.ip:<4} instr={instr!r:<4} "
            f"pos={self.pos:<5} cell={self.cell():<4} hunger={self.hunger:<6} "
            f"dir={self.direction:+d}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run a GobbleScript (.gob) program -- an irrational, "
                     "self-devouring Brainfuck dialect."
    )
    parser.add_argument("file", help="path to a .gob source file")
    parser.add_argument("--hunger", type=int, default=DEFAULT_HUNGER,
                         help=f"starting Hunger (default {DEFAULT_HUNGER})")
    parser.add_argument("--seed", type=int, default=None,
                         help="random seed, for reproducible chaos")
    parser.add_argument("--input", type=str, default=None,
                         help="fixed input string fed to ',' instructions")
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS,
                         help="safety cap on executed instructions")
    parser.add_argument("-v", "--verbose", action="store_true",
                         help="print a step-by-step trace to stderr")
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    machine = GobbleMachine(
        source,
        hunger=args.hunger,
        verbose=args.verbose,
        input_text=args.input,
        seed=args.seed,
        max_steps=args.max_steps,
    )
    try:
        reason = machine.run()
    except GobbleError as e:
        sys.stderr.write(f"\n[GobbleScript] {e}\n")
        sys.exit(1)

    if reason == "starved":
        sys.stderr.write(
            f"\n[GobbleScript] The Gob ran out of Hunger and starved "
            f"after {machine.steps} steps. Try --hunger with a bigger number.\n"
        )
        sys.exit(2)
    elif reason == "step-limit":
        sys.stderr.write(
            f"\n[GobbleScript] Hit the step safety cap ({args.max_steps}). "
            f"Possible infinite loop -- raise --max-steps if this is intentional.\n"
        )
        sys.exit(3)
    # "finished" -> normal exit, no extra message


if __name__ == "__main__":
    main()
