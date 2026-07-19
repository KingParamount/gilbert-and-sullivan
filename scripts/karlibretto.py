#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""R4/R5 — recover the words the archive file cannot hold.

The archive .kar carries ONE lyric stream, so in an ensemble where six people
sing six different texts it can only ever hold one of them. The libretto is
the only source for the rest. This module lays a character's libretto text
across that character's own notes.

The result is explicitly a GUESS about placement — the words will be right and
the syllable-to-note alignment will often be wrong. That is the intended
trade: the proofer re-places syllables rather than typing them.
"""
import os, re, json, collections

VOWELS = "aeiouy"


def load_blocks(libretto_dir, page_code):
    """Structured view (R11): the JSON sidecar, which records where the archive
       typesets voices in PARALLEL COLUMNS — the machine-readable marker of an
       ensemble in which characters sing different words at the same time.
       -> [{"type": "solo"|"simultaneous"|"stage", ...}] or []."""
    path = os.path.join(libretto_dir, page_code + ".json")
    if not os.path.exists(path):
        return []
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return []


def flatten(blocks):
    """Structured blocks -> [(speaker, [lines], simultaneous_bool)]."""
    out = []
    for b in blocks:
        if b.get("type") == "simultaneous":
            for v in b.get("voices", []):
                spk = v.get("speaker")
                if spk and v.get("lines"):
                    out.append((spk, v["lines"], True))
        elif b.get("type") == "solo":
            if b.get("speaker") and b.get("lines"):
                out.append((b["speaker"], b["lines"], False))
    return out


def load(libretto_dir, page_code):
    """-> [(speaker_label, [verse_line, ...])] in performance order, or []."""
    path = os.path.join(libretto_dir, page_code + ".txt")
    if not os.path.exists(path):
        return []
    out = []
    speaker = None
    buf = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#"):
            continue
        if not line.strip():
            continue
        if line.startswith("[") and line.endswith("]"):
            continue                                  # stage direction
        if _is_speaker(line):
            if speaker and buf:
                out.append((speaker, list(buf)))
            speaker = line.strip().rstrip(".").strip()
            buf = []
        elif speaker:
            buf.append(line.strip())
    if speaker and buf:
        out.append((speaker, list(buf)))
    return out


def _is_speaker(line):
    s = line.strip()
    if not s or len(s) > 60:
        return False
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


# ---------------------------------------------------------------------------
# Syllable splitting.
#
# The archive's own lyric stream is the best dictionary available: it already
# breaks the words of THIS number into the syllables the composer set
# ("di" + "lem" + "ma"). Anything it doesn't cover falls back to a crude
# vowel-group split, which is wrong often enough to be worth flagging but
# still leaves the proofer pasting rather than typing.
# ---------------------------------------------------------------------------

def build_dictionary(raw_syllables):
    """[raw archive syllable] -> {word: [syllables]} for the words in this number."""
    words = {}
    cur = []
    for raw in raw_syllables:
        if raw in ("\r", "\n") or not raw.strip():
            continue
        cur.append(raw)
        if raw.endswith(" "):
            syls = [s.strip() for s in cur if s.strip()]
            key = _key("".join(syls))
            if key and key not in words:
                words[key] = syls
            cur = []
    return words


def _key(w):
    return re.sub(r"[^a-z']", "", w.lower())


def split_word(word, dictionary):
    """-> ([syllables], confident_bool)"""
    key = _key(word)
    if not key:
        return ([word], True)
    if key in dictionary:
        return (_restore_case(word, dictionary[key]), True)
    return (_guess_syllables(word), False)


def _restore_case(word, syls):
    """Reuse the dictionary's split but the libretto's own spelling/case."""
    out = []
    i = 0
    for s in syls:
        n = len(s)
        out.append(word[i:i + n] or s)
        i += n
    if i < len(word):
        out[-1] = out[-1] + word[i:]
    return [s for s in out if s]


def _guess_syllables(word):
    groups = []
    cur = ""
    prev_v = False
    for ch in word:
        v = ch.lower() in VOWELS
        if v and not prev_v and cur:
            groups.append(cur); cur = ch
        else:
            cur += ch
        prev_v = v
    if cur:
        groups.append(cur)
    while len(groups) > 1 and len(groups[-1]) <= 1:
        tail = groups.pop()
        groups[-1] += tail
    return groups or [word]


# ---------------------------------------------------------------------------
def syllable_stream(lines, dictionary):
    """[verse_line] -> ([(syllable, ends_word, confident)], {line_end_indices})"""
    if isinstance(lines, str):
        lines = [lines]
    out = []
    ends = set()
    for text in lines:
        _syllables_of(text, dictionary, out)
        if out:
            ends.add(len(out) - 1)
    return out, ends


def _syllables_of(text, dictionary, out):
    for word in re.findall(r"[A-Za-z']+[.,;:!?\-]*", text):
        core = word.rstrip(".,;:!?-")
        tail = word[len(core):]
        syls, conf = split_word(core, dictionary)
        for i, s in enumerate(syls):
            last = i == len(syls) - 1
            out.append((s + (tail if last else ""), last, conf))
    return out


def phrases(notes, gap):
    """Split a character's notes into sung phrases at rests of >= `gap` ticks.

    Phrases are the natural alignment unit: a libretto line is sung in one
    breath, and a rest is where the next line starts. Aligning phrase-to-line
    keeps a counting error local to one phrase instead of shifting every
    remaining syllable in the number."""
    out = []
    cur = []
    prev_end = None
    for tick, dur, _p in sorted(notes):
        if prev_end is not None and tick - prev_end >= gap and cur:
            out.append(cur); cur = []
        cur.append(tick)
        prev_end = max(prev_end or 0, tick + dur)
    if cur:
        out.append(cur)
    return [sorted(set(p)) for p in out]


def lay_across(syllables, notes, gap, line_ends=()):
    """Place syllables on a character's notes, phrase by phrase.

    Walks the phrases in order, filling each with the next run of syllables.
    Where a verse-line boundary falls near the end of a phrase, the break is
    snapped to it — that is the case the archive gets right and the one a
    proofer notices first. Counts rarely match exactly, so leftover syllables
    are stacked onto the phrase's last note rather than silently dropped."""
    ph = phrases(notes, gap)
    if not syllables or not ph:
        return []
    ends = set(line_ends)
    out = []
    i = 0
    n = len(syllables)
    for pi, onsets in enumerate(ph):
        if i >= n:
            break
        k = len(onsets)
        remaining_phrases = len(ph) - pi
        take = k
        # snap to a nearby line boundary so verse lines stay whole
        for cand in range(max(1, k - 2), min(n - i, k + 3)):
            if (i + cand - 1) in ends:
                take = cand
                break
        if remaining_phrases == 1:
            take = n - i                       # last phrase absorbs the rest
        take = max(1, min(take, n - i))
        chunk = syllables[i:i + take]
        for j, onset in enumerate(onsets):
            if j < len(chunk):
                out.append((onset, chunk[j]))
        if len(chunk) > k and onsets:
            for extra in chunk[k:]:
                out.append((onsets[-1], extra))
        i += take
    while i < n and out:
        out.append((out[-1][0], syllables[i])); i += 1
    return out
