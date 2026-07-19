#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Read per-character lyrics out of a VECTOR-ENGRAVED vocal score PDF.

This is the authoritative source the other inputs only approximate. The .kar
holds one lyric stream; the libretto holds each character's words but prints a
verse once where the score sings it four times. The engraved score holds what
is actually sung, per stave, syllabified as the composer set it.

It reads TEXT ONLY. No optical music recognition — notes come from the .kar,
which is reliable. A bitmap-scanned score is useless here and must be rejected
rather than OCR'd: a misread lyric looks like a word, and silently wrong text
would destroy the one property this pipeline currently guarantees, which is
that the words are right and only their placement is in doubt.

Layout model: each system carries a column of stave labels at the left margin
("S.", "A.", "PL.", "JU."), and each stave's lyrics sit in the horizontal band
between its own label and the next label down.
"""
import re, collections

LYRIC_BAND = 34.0     # pt below a stave label that its lyric row occupies


def lyric_style(doc, pages):
    """Find the (font, size) the engraver uses for LYRICS.

    Filtering lyrics by vocabulary is hopeless — a word list that removes "p",
    "ma" and "a" as dynamics also removes "I", "a" and the second half of
    "di-lem-ma". The engraving separates them properly: lyrics are set in the
    text face at one size, dynamics and tuplet digits in the music font,
    tempo in bold, bar numbers in italic. So filter by style, not by spelling.
    """
    counts = collections.Counter()
    for pno in pages:
        page = doc[pno]
        left = page.rect.width * 0.13
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for sp in ln["spans"]:
                    t = sp["text"].strip()
                    if len(t) < 2 or not any(c.isalpha() for c in t):
                        continue
                    if sp["bbox"][0] <= left:
                        continue                     # stave label column
                    font = sp["font"]
                    if "Opus" in font or font.endswith("-Bold") or \
                       font.endswith("-Italic") or t.isupper():
                        continue
                    counts[(font, round(sp["size"], 1))] += 1
    return counts.most_common(1)[0][0] if counts else None


def extract(doc, page_range, abbrev, left_frac=0.13, band_slack=8.0, style=None):
    """doc: fitz Document; page_range: iterable of 0-based page indices.
       abbrev: {LABEL (upper, no trailing dot): stave name}.
       -> {stave_name: [syllable, ...]} in reading order."""
    pages = list(page_range)
    if style is None:
        style = lyric_style(doc, pages)
    known = set(abbrev)
    out = collections.defaultdict(list)
    for pno in pages:
        page = doc[pno]
        left_edge = page.rect.width * left_frac

        labels = []
        for x0, y0, x1, y1, w, *_ in page.get_text("words"):
            key = w.strip().upper().rstrip(".")
            if x0 <= left_edge and key in known:
                labels.append((y0, abbrev[key]))
        if not labels:
            continue
        labels.sort()

        # A stave's lyric row sits a SHORT FIXED DISTANCE below its label —
        # measured at 19-24pt. Running the band down to the next label instead
        # is catastrophic on a piano-vocal page: the gap between two vocal
        # staves contains the whole piano reduction.
        bands = []
        for i, (y, name) in enumerate(labels):
            nxt = labels[i + 1][0] if i + 1 < len(labels) else page.rect.height
            lo, hi = y + band_slack, min(y + LYRIC_BAND, nxt - band_slack)
            if hi > lo:
                bands.append((lo, hi, name))

        buckets = collections.defaultdict(list)
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for sp in ln["spans"]:
                    t = sp["text"].strip()
                    if not t or (style and (sp["font"], round(sp["size"], 1)) != style):
                        continue
                    x0, y0 = sp["bbox"][0], sp["bbox"][1]
                    if x0 <= left_edge:
                        continue
                    for lo, hi, name in bands:
                        if lo <= y0 < hi:
                            buckets[(lo, name)].append((y0, x0, t))
                            break

        # SATB chorus is engraved on two staves with ONE shared lyric line, so
        # a soprano band is often empty while the alto below it carries the
        # words for both. Give the shared line to every chorus stave in the
        # bracket rather than losing a whole voice.
        got = {name for (_lo, name) in buckets}
        chorus = ["Soprano", "Alto", "Tenor", "Bass"]
        present = [n for (_y, n) in labels if n in chorus]
        shared = [buckets[k] for k in buckets if k[1] in chorus]
        for i, (_y, name) in enumerate(labels):
            if name in chorus and name not in got and shared:
                nearest = min(((abs(_y - k[0]), k) for k in buckets if k[1] in chorus),
                              default=(None, None))[1]
                if nearest:
                    buckets[(_y, name)] = list(buckets[nearest])

        for (lo, name), items in sorted(buckets.items()):
            items.sort(key=lambda t: (round(t[0] / 3) * 3, t[1]))
            for _y, _x, t in items:
                out[name] += t.split()
    return dict(out)


def number_pages(doc, first_page=0):
    """-> [(label, start_page_index)] from the 'No. 12' headings the engraver
       prints at the head of each number."""
    found = []
    for i in range(first_page, doc.page_count):
        for m in re.finditer(r'No\.\s*(\d+)\s*([a-z])?', doc[i].get_text()):
            lab = m.group(1) + (m.group(2) or "")
            if not found or found[-1][0] != lab:
                found.append((lab, i))
            break
    return found


def page_ranges(doc, order, first_page=0):
    """order: [(song_id, number_label)] in score order.
       -> {song_id: range(start, end)}"""
    marks = dict()
    for lab, idx in number_pages(doc, first_page):
        marks.setdefault(lab, idx)
    starts = []
    for sid, lab in order:
        if lab in marks:
            starts.append((sid, marks[lab]))
    out = {}
    for i, (sid, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else doc.page_count
        out[sid] = range(start, end)
    return out
