#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Read a G&S Archive karaoke file, write a Standard MIDI File.

Nothing here makes editorial decisions about who sings what — that is the job
of karidentify.py. This module only moves notes, time and words around without
losing anything.

An earlier version of this file also WROTE MusicXML, reconstructing bars, note
values, dots, tuplets and anacruses from the MIDI. It was ~250 lines and it
produced scores that were unusable in Dorico, because notation is genuinely
hard and Dorico already does it superbly from a plain MIDI file. Handing it
MIDI and letting it notate deleted that entire class of bug. If notation ever
seems necessary again, it isn't.
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
# Standard MIDI File writer
#
# The output format that made this project work. MIDI carries onsets,
# durations, pitches and lyrics — everything the app and Dorico actually need
# — and carries NO notation, so the whole class of bugs that made the
# MusicXML route unusable (articulation gaps read as rests, undeclared dots
# and tuplets, anacruses, meter changes off the barline) cannot arise.
#
# Durations are written EXACTLY as the archive holds them, 94-tick eighths and
# all. That is performance data; quantising it is Dorico's job and Dorico is
# very good at it. The one thing we do impose is note-OFF before note-ON at a
# shared tick, because the app's midi.js retriggers and would otherwise
# silence a repeated pitch instantly.
# ---------------------------------------------------------------------------

def _vlq_out(n):
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def _meta(mt, data):
    return b"\xff" + bytes([mt]) + _vlq_out(len(data)) + data


def _latin1(s):
    return (s.replace("\u2019", "'").replace("\u2018", "'")
             .replace("\u201c", '"').replace("\u201d", '"')
             .replace("\u2014", "--").replace("\u2013", "-")
             .encode("latin-1", "replace"))


def _chunk(events):
    """events: [(tick, priority, bytes)]; priority 0 meta, 1 note-off, 2 note-on."""
    events.sort(key=lambda e: (e[0], e[1]))
    body = bytearray()
    prev = 0
    for tick, _p, payload in events:
        body += _vlq_out(tick - prev) + payload
        prev = tick
    body += _vlq_out(0) + _meta(0x2F, b"")
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_smf(path, sc, parts, title=None):
    """parts: [{name, notes:[(tick,dur,pitch,lyric_or_None)]}].
       Keeps the source's tempo, time-signature and key-signature maps so a
       notation program bars the music the way the engraver did."""
    chunks = []
    cond = [(0, 0, _meta(0x03, _latin1(title or "Conductor")))]
    for tick, bpm in sc.tempos:
        us = int(round(60_000_000 / bpm))
        cond.append((tick, 0, _meta(0x51, struct.pack(">I", us)[1:])))
    for tick, num, den in sc.timesigs:
        p2 = max(0, den.bit_length() - 1)
        cond.append((tick, 0, _meta(0x58, bytes([num, p2, 24, 8]))))
    for tick, fifths, mode in sc.keysigs:
        cond.append((tick, 0, _meta(0x59, struct.pack("b", fifths) + bytes([mode]))))
    chunks.append(_chunk(cond))

    # Give every track its OWN MIDI channel (skipping 9, the GM drum channel).
    # Everything used to share channel 0, which made MuseScore merge tracks onto
    # one staff and pile several singers' words onto verse 1 of the same notes
    # ("smooshed" lyrics). Distinct channels keep the staves apart on import.
    # The app routes by track name, not channel, so this is invisible to it, and
    # Dorico imports channels cleanly too.
    CHANS = [c for c in range(16) if c != 9]
    for pi, p in enumerate(parts):
        ch = CHANS[pi % len(CHANS)]
        ev = [(0, 0, _meta(0x03, _latin1(p["name"])))]
        for tick, text in p.get("raw_lyrics", ()):
            ev.append((tick, 0, _meta(0x05, _latin1(text))))
        for item in sorted(p["notes"]):
            tick, dur, pitch = item[0], item[1], item[2]
            lyric = item[3] if len(item) > 3 else None
            if lyric:
                text = lyric[0] if isinstance(lyric, tuple) else lyric
                if text:
                    ev.append((tick, 0, _meta(0x05, _latin1(text))))
            ev.append((tick + max(1, dur), 1, bytes([0x80 | ch, pitch, 0])))
            ev.append((tick, 2, bytes([0x90 | ch, pitch, 80])))
        chunks.append(_chunk(ev))

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), sc.division)
    with open(path, "wb") as f:
        f.write(header + b"".join(chunks))
