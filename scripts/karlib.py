#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Shared plumbing for the .kar -> MusicXML outbound leg.

Reads a G&S Archive karaoke file (a format-1 SMF written by NoteWorthy
Composer) into a neutral structure, and writes MusicXML that Dorico will open.

Nothing here makes editorial decisions about *who sings what* — that is the
job of kar-to-musicxml.py. This module only moves notes and time around
without losing anything.

The archive files are uniformly 192 ticks per quarter and carry a real time
signature map (294/298 files) and key signature map (271/298), so measures and
barlines are recoverable rather than guessed.
"""
import struct, re

# ---------------------------------------------------------------------------
# Standard MIDI File reader
# ---------------------------------------------------------------------------

ACC_RE = re.compile(r'piano|right hand|left hand|tempo|^rh$|^lh$|^organ$', re.I)


def _vlq(d, i):
    v = 0
    while True:
        b = d[i]; i += 1; v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, i


class Track:
    __slots__ = ("name", "notes", "lyrics", "index")

    def __init__(self, name, index):
        self.name = name
        self.index = index
        self.notes = []       # [(tick, dur, pitch)]
        self.lyrics = []      # [(tick, text)]

    @property
    def is_accomp(self):
        return bool(self.name and ACC_RE.search(self.name))

    @property
    def is_lyric_stave(self):
        return bool(self.name and self.name.strip().lower() == "lyrics")

    def __repr__(self):
        return f"<Track {self.name!r} notes={len(self.notes)} lyr={len(self.lyrics)}>"


class Score:
    def __init__(self):
        self.division = 192
        self.timesigs = []    # [(tick, num, den)]
        self.keysigs = []     # [(tick, fifths, mode)]
        self.tempos = []      # [(tick, bpm)]
        self.tracks = []
        self.title = None

    @property
    def singers(self):
        return [t for t in self.tracks
                if t.notes and not t.is_accomp and not t.is_lyric_stave]

    @property
    def lyric_stave(self):
        for t in self.tracks:
            if t.is_lyric_stave and len(t.lyrics) > 4:
                return t
        return None

    @property
    def end_tick(self):
        e = 0
        for t in self.tracks:
            for tick, dur, _ in t.notes:
                e = max(e, tick + dur)
        return e


def read_kar(path):
    d = open(path, "rb").read()
    if d[:4] != b"MThd":
        raise ValueError(f"{path}: not a MIDI file")
    _fmt, ntrk, div = struct.unpack(">HHH", d[8:14])
    sc = Score()
    sc.division = div
    i = 14
    for ti in range(ntrk):
        if d[i:i + 4] != b"MTrk":
            break
        ln = struct.unpack(">I", d[i + 4:i + 8])[0]
        i += 8
        end = i + ln
        tick = 0
        status = 0
        tr = Track(None, ti)
        open_notes = {}                      # pitch -> (tick, index)
        while i < end:
            dt, i = _vlq(d, i)
            tick += dt
            b = d[i]
            if b & 0x80:
                status = b; i += 1
            else:
                b = status
            if b == 0xFF:
                mt = d[i]; i += 1
                l, i = _vlq(d, i)
                data = d[i:i + l]; i += l
                if mt == 0x03 and tr.name is None:
                    tr.name = data.decode("latin-1", "replace").strip()
                elif mt == 0x05:
                    tr.lyrics.append((tick, data.decode("latin-1", "replace")))
                elif mt == 0x58 and len(data) >= 2:
                    sc.timesigs.append((tick, data[0], 2 ** data[1]))
                elif mt == 0x59 and len(data) >= 2:
                    sc.keysigs.append((tick, struct.unpack("b", data[0:1])[0], data[1]))
                elif mt == 0x51 and len(data) >= 3:
                    us = (data[0] << 16) | (data[1] << 8) | data[2]
                    if us:
                        sc.tempos.append((tick, 60_000_000 / us))
            elif b in (0xF0, 0xF7):
                l, i = _vlq(d, i); i += l
            else:
                hi = b & 0xF0
                if hi in (0xC0, 0xD0):
                    i += 1
                    continue
                p, v = d[i], d[i + 1]; i += 2
                if hi == 0x90 and v > 0:
                    # retrigger: an unmatched re-strike closes the previous one
                    if p in open_notes:
                        st, idx = open_notes.pop(p)
                        tr.notes[idx] = (st, max(1, tick - st), p)
                    tr.notes.append((tick, 0, p))
                    open_notes[p] = (tick, len(tr.notes) - 1)
                elif hi in (0x80, 0x90):
                    if p in open_notes:
                        st, idx = open_notes.pop(p)
                        tr.notes[idx] = (st, max(1, tick - st), p)
        for p, (st, idx) in open_notes.items():      # unterminated at EOT
            tr.notes[idx] = (st, max(1, tick - st), p)
        tr.notes.sort(key=lambda n: (n[0], n[2]))
        tr.lyrics.sort(key=lambda l: l[0])
        sc.tracks.append(tr)
        i = end
    if not sc.timesigs:
        sc.timesigs = [(0, 4, 4)]
    if sc.timesigs[0][0] != 0:
        sc.timesigs.insert(0, (0, 4, 4))
    sc.timesigs.sort()
    sc.keysigs.sort()
    sc.tempos.sort()
    return sc


# ---------------------------------------------------------------------------
# Measure grid
# ---------------------------------------------------------------------------

def measure_grid(sc, end_tick):
    """[(start_tick, end_tick, num, den, is_new_sig, fifths_or_None)] covering
       0..end_tick. A time-signature change starts a new measure at that tick,
       which is how NoteWorthy writes them."""
    bars = []
    sigs = list(sc.timesigs)
    keys = {t: f for t, f, _m in sc.keysigs}
    for si, (stick, num, den) in enumerate(sigs):
        nxt = sigs[si + 1][0] if si + 1 < len(sigs) else None
        barlen = int(sc.division * 4 * num / den)
        if barlen <= 0:
            continue
        t = stick
        first = True
        while t < end_tick and (nxt is None or t < nxt):
            bend = t + barlen
            if nxt is not None:
                bend = min(bend, nxt)
            bars.append([t, bend, num, den, first, None])
            first = False
            t = bend
        if nxt is None and not bars:
            bars.append([stick, stick + barlen, num, den, True, None])
    # attach key changes to the bar they fall in
    for kt, f in sorted(keys.items()):
        for b in bars:
            if b[0] <= kt < b[1]:
                b[5] = f
                break
        else:
            if bars and kt >= bars[-1][1]:
                bars[-1][5] = f
    if bars and not any(b[5] is not None for b in bars):
        bars[0][5] = 0
    elif bars and bars[0][5] is None:
        bars[0][5] = 0
    return bars


# ---------------------------------------------------------------------------
# Pitch spelling  (notation quality is explicitly not a goal; this just has to
# be legal MusicXML that plays back on the right pitch)
# ---------------------------------------------------------------------------

SHARP = [("C", 0), ("C", 1), ("D", 0), ("D", 1), ("E", 0), ("F", 0),
         ("F", 1), ("G", 0), ("G", 1), ("A", 0), ("A", 1), ("B", 0)]
FLAT = [("C", 0), ("D", -1), ("D", 0), ("E", -1), ("E", 0), ("F", 0),
        ("G", -1), ("G", 0), ("A", -1), ("A", 0), ("B", -1), ("B", 0)]


def spell(midi, fifths):
    step, alter = (FLAT if (fifths or 0) < 0 else SHARP)[midi % 12]
    octave = midi // 12 - 1
    return step, alter, octave


# ---------------------------------------------------------------------------
# Note-type naming (Dorico wants <type>; it need not match the duration well)
# ---------------------------------------------------------------------------

TYPES = [(4.0, "whole"), (2.0, "half"), (1.0, "quarter"), (0.5, "eighth"),
         (0.25, "16th"), (0.125, "32nd"), (0.0625, "64th")]


def note_type(dur, division):
    q = dur / division
    for val, name in TYPES:
        if q >= val * 0.95:
            return name
    return "64th"


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# Syllable boundaries
#
# The archive encodes word ends as a TRAILING SPACE on the syllable
# ("sound" + "ing; " -> "sounding;").  MusicXML wants <syllabic> instead, and
# the inbound converter (musicxml-to-midi.py) reads <syllabic> to rebuild the
# spacing.  Getting this wrong silently destroys every melisma, so it is done
# in one place.
# ---------------------------------------------------------------------------

def syllabify(raw_syllables):
    """[raw archive syllable] -> [(clean_text, syllabic)] with syllabic in
       single/begin/middle/end."""
    out = []
    starting = True                       # next syllable starts a word
    for raw in raw_syllables:
        ends_word = raw.endswith(" ")
        text = raw.strip()
        if not text:
            out.append((None, None))
            continue
        if starting and ends_word:
            syl = "single"
        elif starting:
            syl = "begin"
        elif ends_word:
            syl = "end"
        else:
            syl = "middle"
        out.append((text, syl))
        starting = ends_word
    return out


# ---------------------------------------------------------------------------
# MusicXML writer
# ---------------------------------------------------------------------------

def write_musicxml(path, sc, parts, work_title=None):
    """parts: list of dicts
         name   : part name (becomes the MIDI track name on the way back)
         notes  : [(tick, dur, pitch, lyric)]  lyric = (text, syllabic) or None
         flags  : [(tick, text)] editorial annotations, shown above the stave
       Notes within a part may share an onset (chord); overlapping notes with
       DIFFERENT onsets are truncated at the next onset, and the caller is
       expected to have split real divisi into separate parts already."""
    end = max([sc.end_tick] + [t + d for p in parts for (t, d, _, _) in p["notes"]])
    bars = measure_grid(sc, max(end, 1))
    div = sc.division

    o = []
    o.append('<?xml version="1.0" encoding="UTF-8"?>')
    o.append('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 '
             'Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">')
    o.append('<score-partwise version="4.0">')
    if work_title:
        o.append(f'  <work><work-title>{esc(work_title)}</work-title></work>')
    o.append('  <identification><encoding>'
             '<software>Learn-O-Matic kar-to-musicxml</software>'
             '</encoding></identification>')
    o.append('  <part-list>')
    for i, p in enumerate(parts):
        o.append(f'    <score-part id="P{i + 1}">'
                 f'<part-name>{esc(p["name"])}</part-name></score-part>')
    o.append('  </part-list>')

    tempo_by_tick = {}
    for t, bpm in sc.tempos:
        tempo_by_tick.setdefault(t, bpm)

    for pi, p in enumerate(parts):
        o.append(f'  <part id="P{pi + 1}">')
        notes = sorted(p["notes"], key=lambda n: (n[0], -n[2]))
        flags = sorted(p.get("flags", []))
        ni = fi = 0
        carry = []                 # notes tied over the barline: (pitch, remaining)
        prev_fifths = None
        for bi, (bstart, bend, num, den, new_sig, fifths) in enumerate(bars):
            o.append(f'    <measure number="{bi + 1}">')
            attrs = []
            if bi == 0 or (fifths is not None and fifths != prev_fifths):
                f = fifths if fifths is not None else (prev_fifths or 0)
                attrs.append(f'<key><fifths>{f}</fifths></key>')
                prev_fifths = f
            if bi == 0:
                attrs.insert(0, f'<divisions>{div}</divisions>')
            if new_sig or bi == 0:
                attrs.append(f'<time><beats>{num}</beats>'
                             f'<beat-type>{den}</beat-type></time>')
            if bi == 0:
                clef = _clef_for(p)
                attrs.append(clef)
            if attrs:
                o.append('      <attributes>' + "".join(attrs) + '</attributes>')

            # tempo marks landing in this bar (first part only — the inbound
            # converter reads the tempo map from P1)
            if pi == 0:
                for tt in sorted(t for t in tempo_by_tick if bstart <= t < bend):
                    o.append(f'      <direction placement="above"><direction-type>'
                             f'<metronome><beat-unit>quarter</beat-unit>'
                             f'<per-minute>{round(tempo_by_tick[tt])}</per-minute>'
                             f'</metronome></direction-type>'
                             f'<sound tempo="{tempo_by_tick[tt]:.2f}"/></direction>')

            cursor = bstart

            # notes tied in from the previous bar
            if carry:
                span = min(min(c[1] for c in carry), bend - bstart)
                for k, (pitch, rem) in enumerate(carry):
                    step, alter, octv = spell(pitch, prev_fifths)
                    o.append(_note_xml(step, alter, octv, span, div,
                                       chord=(k > 0), tie_stop=True,
                                       tie_start=(rem > span), lyric=None))
                carry = [(pitch, rem - span) for pitch, rem in carry if rem - span > 0]
                cursor = bstart + span

            while ni < len(notes) and notes[ni][0] < bend:
                onset = notes[ni][0]
                if onset < cursor:                   # overlap: caller's problem
                    ni += 1
                    continue
                group = []
                while ni < len(notes) and notes[ni][0] == onset:
                    group.append(notes[ni]); ni += 1
                nxt_onset = notes[ni][0] if ni < len(notes) else None

                while fi < len(flags) and flags[fi][0] <= onset:
                    o.append(_flag_xml(flags[fi][1])); fi += 1

                if onset > cursor:
                    o.append(_rest_xml(onset - cursor, div))
                    cursor = onset

                dur = max(n[1] for n in group)
                if nxt_onset is not None:
                    dur = min(dur, nxt_onset - onset)
                dur = max(1, dur)
                span = min(dur, bend - onset)
                for k, (_t, _d, pitch, lyric) in enumerate(group):
                    step, alter, octv = spell(pitch, prev_fifths)
                    o.append(_note_xml(step, alter, octv, span, div,
                                       chord=(k > 0), tie_stop=False,
                                       tie_start=(dur > span),
                                       lyric=(lyric if k == 0 else None)))
                if dur > span:
                    carry = [(n[2], dur - span) for n in group]
                cursor = onset + span

            while fi < len(flags) and flags[fi][0] < bend:
                o.append(_flag_xml(flags[fi][1])); fi += 1

            if cursor < bend:
                o.append(_rest_xml(bend - cursor, div))
            o.append('    </measure>')
        o.append('  </part>')
    o.append('</score-partwise>')

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(o) + "\n")


def _clef_for(p):
    pitches = [n[2] for n in p["notes"]]
    avg = sum(pitches) / len(pitches) if pitches else 60
    if avg < 55:
        return '<clef><sign>F</sign><line>4</line></clef>'
    return '<clef><sign>G</sign><line>2</line></clef>'


def _flag_xml(text):
    return ('      <direction placement="above"><direction-type>'
            f'<words font-style="italic" color="#FF0000">{esc(text)}</words>'
            '</direction-type></direction>')


def _rest_xml(dur, div):
    return (f'      <note><rest/><duration>{int(dur)}</duration>'
            f'<voice>1</voice><type>{note_type(dur, div)}</type></note>')


def _note_xml(step, alter, octv, dur, div, chord, tie_stop, tie_start, lyric):
    x = ['      <note>']
    if chord:
        x.append('<chord/>')
    x.append(f'<pitch><step>{step}</step>')
    if alter:
        x.append(f'<alter>{alter}</alter>')
    x.append(f'<octave>{octv}</octave></pitch>')
    x.append(f'<duration>{int(dur)}</duration>')
    if tie_stop:
        x.append('<tie type="stop"/>')
    if tie_start:
        x.append('<tie type="start"/>')
    x.append(f'<voice>1</voice><type>{note_type(dur, div)}</type>')
    if tie_stop:
        x.append('<notations><tied type="stop"/></notations>')
    if tie_start:
        x.append('<notations><tied type="start"/></notations>')
    if lyric and lyric[0]:
        text, syl = lyric
        x.append(f'<lyric number="1"><syllabic>{syl}</syllabic>'
                 f'<text>{esc(text)}</text></lyric>')
    x.append('</note>')
    return "".join(x)

