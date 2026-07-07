#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Convert per-character MusicXML full scores (Dorico export) into Standard MIDI
Files that the Learn-O-Matic player already understands.

One MusicXML `<part>` (= one named character/piano stave) becomes one named MIDI
track (meta 0x03 = the character label), carrying that character's notes and
per-note lyric events (meta 0x05) rebuilt from <text>/<syllabic>. A leading
conductor track carries the tempo map (bare <sound tempo> lives only in P1).

This is an OFFLINE build tool. It reads no opera-specific config; the character
label IS the track name, which is exactly what songs.json/opera.js route on.

Staves named "Lyrics" (Dorico cue/reduction artefacts) and empty staves are
dropped. Grace notes are skipped; tied notes are merged into one sung note.

Usage:
    python3 scripts/musicxml-to-midi.py <src-dir> <out-dir> [file.musicxml ...]
If no explicit files are given, every *.musicxml in <src-dir> is converted.
"""
import sys, os, re, glob, struct
import xml.etree.ElementTree as ET

PPQ = 480            # MIDI ticks per quarter note in the output
VELOCITY = 80
DROP_PARTS = {"Lyrics"}
HYPHENATE = False    # True -> "Ju-ry-men"; False -> syllables abut, space at word end

# Dorico labels the chorus plural in some numbers, singular in others; the app
# routes on an exact track name, so normalise to one form across the opera.
NAME_MAP = {"Sopranos": "Soprano", "Altos": "Alto",
            "Tenors": "Tenor", "Basses": "Bass"}

STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


# ---------------------------------------------------------------------------
# filename  "Trial by Jury No. 5 - Full score ..."  ->  "tbj05"
# ---------------------------------------------------------------------------
def file_id(path):
    base = os.path.basename(path)
    m = re.search(r"Jury\s+(?:No\.\s*)?(\d+)([a-z]?)", base, re.I)
    if not m:
        return None
    return "tbj%02d%s" % (int(m.group(1)), m.group(2).lower())


# ---------------------------------------------------------------------------
# Parse one <part> into timed notes: [(tick, dur_ticks, midi, lyric_or_None)]
# plus, for the conductor part, the tempo changes [(tick, bpm)].
# Positions are tracked in QUARTER NOTES (float) so a mid-piece <divisions>
# change can't corrupt the timeline; converted to PPQ ticks at the end.
# ---------------------------------------------------------------------------
def parse_part(part, divisions):
    notes = []          # dicts: {q, dq, midi, lyric, tie_open}
    tempos = []
    cursor = 0.0        # absolute position, in quarter notes
    last_onset = 0.0    # onset of the most recent non-chord note (for chords)
    pending = {}        # midi -> index in `notes` awaiting a tie continuation

    for m in part.findall("measure"):
        for el in m:
            tag = el.tag
            if tag == "attributes":
                d = el.findtext("divisions")
                if d:
                    divisions = int(d)
            elif tag == "sound" and el.get("tempo"):
                tempos.append((cursor, float(el.get("tempo"))))
            elif tag == "direction":
                snd = el.find(".//sound")
                if snd is not None and snd.get("tempo"):
                    tempos.append((cursor, float(snd.get("tempo"))))
            elif tag == "backup":
                cursor -= int(el.findtext("duration")) / divisions
            elif tag == "forward":
                cursor += int(el.findtext("duration")) / divisions
            elif tag == "note":
                if el.find("grace") is not None:
                    continue                       # ornament, no duration — skip
                dur_txt = el.findtext("duration")
                dq = (int(dur_txt) / divisions) if dur_txt else 0.0
                is_chord = el.find("chord") is not None
                if is_chord:
                    onset = last_onset
                else:
                    onset = cursor
                    cursor += dq
                    last_onset = onset
                if el.find("rest") is not None:
                    continue
                p = el.find("pitch")
                if p is None:
                    continue
                midi = ((int(p.findtext("octave")) + 1) * 12
                        + STEP[p.findtext("step")]
                        + int(p.findtext("alter") or 0))
                ties = {t.get("type") for t in el.findall("tie")}
                lyric = read_lyric(el)

                # merge tied notes: a note that continues a tie extends the held
                # note rather than re-articulating the pitch. BUT only when it
                # carries no lyric — a tie-continuation with its own syllable is a
                # re-articulation, so it must stay a separate sung note.
                if "stop" in ties and midi in pending and lyric is None:
                    notes[pending[midi]]["dq"] += dq
                    if "start" not in ties:
                        del pending[midi]
                    continue
                if "stop" in ties and midi in pending:
                    del pending[midi]           # syllable re-articulates the pitch

                notes.append({"q": onset, "dq": dq, "midi": midi, "lyric": lyric})
                if "start" in ties:
                    pending[midi] = len(notes) - 1

    ev = [(round(n["q"] * PPQ), max(1, round(n["dq"] * PPQ)), n["midi"], n["lyric"])
          for n in notes]
    tm = [(round(q * PPQ), bpm) for q, bpm in tempos]
    return ev, tm


def read_lyric(note):
    lyr = note.find("lyric")
    if lyr is None:
        return None
    txt = lyr.findtext("text")
    if txt is None:
        return None
    txt = re.sub(r"\[[^\]]*\]", "", txt).strip()   # drop stray [Speaker] tags
    if not txt:
        return None
    syl = lyr.findtext("syllabic") or "single"
    if syl in ("single", "end"):
        return txt + " "                       # word boundary
    return (txt + "-") if HYPHENATE else txt   # mid-word: abut or hyphenate


# ---------------------------------------------------------------------------
# Standard MIDI File (format 1) writer
# ---------------------------------------------------------------------------
def vlq(n):
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def latin1(s):
    return (s.replace("’", "'").replace("‘", "'")
             .replace("“", '"').replace("”", '"')
             .replace("—", "--").replace("–", "-")
             .encode("latin-1", "replace"))


def meta(mt, data):
    return b"\xff" + bytes([mt]) + vlq(len(data)) + data


def track_chunk(events):
    """events: list of (tick, priority, bytes). At a shared tick the order is
       meta/lyric (0), then note-OFF (1), then note-ON (2) — offs must precede
       ons so a pitch re-struck on the same tick isn't instantly silenced by the
       previous note's off (which would collide under midi.js's retrigger)."""
    events.sort(key=lambda e: (e[0], e[1]))
    body = bytearray()
    prev = 0
    for tick, _prio, payload in events:
        body += vlq(tick - prev) + payload
        prev = tick
    body += vlq(0) + meta(0x2F, b"")           # end of track
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def build_smf(name, tempos, tracks):
    """tracks: list of (track_name, [(tick,dur,midi,lyric)])."""
    chunks = []

    # conductor track: tempo map (named "Tempo" so opera.js treats it as accomp)
    cond = [(0, 0, meta(0x03, b"Tempo"))]
    for tick, bpm in tempos:
        us = int(round(60_000_000 / bpm))
        cond.append((tick, 0, meta(0x51, struct.pack(">I", us)[1:])))
    chunks.append(track_chunk(cond))

    for tname, evs in tracks:
        te = [(0, 0, meta(0x03, latin1(tname)))]
        for tick, dur, midi, lyric in evs:
            if lyric:
                te.append((tick, 0, meta(0x05, latin1(lyric))))
            te.append((tick + dur, 1, bytes([0x80, midi, 0])))      # note-off first
            te.append((tick, 2, bytes([0x90, midi, VELOCITY])))     # then note-on
        chunks.append(track_chunk(te))

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), PPQ)
    return header + b"".join(chunks)


# ---------------------------------------------------------------------------
def convert(path, out_dir):
    fid = file_id(path)
    if not fid:
        print("  ?? skip (no number in name):", os.path.basename(path))
        return
    root = ET.parse(path).getroot()
    id2name = {sp.get("id"): (sp.findtext("part-name") or "").strip()
               for sp in root.iter("score-part")}

    # tempo map comes from the first part only (that is where Dorico writes it)
    first = root.find("part")
    _, tempos = parse_part(first, 4)

    tracks = []
    dropped = []
    for part in root.findall("part"):
        name = id2name.get(part.get("id"), part.get("id"))
        name = NAME_MAP.get(name, name)
        if name in DROP_PARTS:
            dropped.append(name)
            continue
        evs, _ = parse_part(part, 4)
        if not evs:
            dropped.append(name + "(empty)")
            continue
        tracks.append((name, evs))

    smf = build_smf(fid, tempos, tracks)
    dst = os.path.join(out_dir, fid + ".mid")
    with open(dst, "wb") as f:
        f.write(smf)
    voice = [n for n, _ in tracks]
    print(f"  {fid}: {len(tracks)} tracks, {len(tempos)} tempo marks -> {fid}.mid")
    print(f"       tracks: {', '.join(voice)}")
    if dropped:
        print(f"       dropped: {', '.join(dropped)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    files = sys.argv[3:] or sorted(glob.glob(os.path.join(src, "*.musicxml")))
    if sys.argv[3:]:
        files = [f if os.path.isabs(f) else os.path.join(src, f) for f in files]
    for f in files:
        convert(f, out)
