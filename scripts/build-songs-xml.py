#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Generate songs.json for an opera converted from per-character MusicXML.

Unlike build-songs.py (which reads generic .kar tracks and needs a hand-curated
candidate map), the MusicXML-derived .mid files already name each track after
the character, so `voiceTracks` is read straight off the files and each part's
`candidates` is just its own score label. Only the human metadata (part labels,
song order/titles) is curated below.

Usage:  python3 scripts/build-songs-xml.py
"""
import os, json, struct


HERE = os.path.dirname(__file__)
OPERAS_DIR = os.path.join(HERE, "..", "operas")


def read_vlq(d, i):
    v = 0
    while True:
        b = d[i]; i += 1; v = (v << 7) | (b & 0x7f)
        if not b & 0x80:
            break
    return v, i


def track_names(path):
    """Return [(name, note_count)] for each track in a Standard MIDI File."""
    d = open(path, "rb").read()
    _, ntrk, _ = struct.unpack(">HHH", d[8:14])
    i = 14
    out = []
    for _ in range(ntrk):
        if d[i:i + 4] != b"MTrk":
            break
        ln = struct.unpack(">I", d[i + 4:i + 8])[0]
        i += 8; end = i + ln; status = 0; nm = None; notes = 0
        while i < end:
            _, i = read_vlq(d, i); b = d[i]
            if b & 0x80:
                status = b; i += 1
            else:
                b = status
            if b == 0xFF:
                mt = d[i]; i += 1; l, i = read_vlq(d, i); data = d[i:i + l]; i += l
                if mt == 0x03 and nm is None:
                    nm = data.decode("latin1", "replace")
            elif b in (0xF0, 0xF7):
                l, i = read_vlq(d, i); i += l
            else:
                hi = b & 0xF0
                if hi == 0x90:
                    notes += 1
                i += 1 if hi in (0xC0, 0xD0) else 2
        out.append((nm, notes))
    return out


# ---------------------------------------------------------------------------
TRIAL = {
    "dir": "trial-by-jury",
    "meta": {
        "opera": "Trial by Jury", "composer": "Arthur Sullivan", "librettist": "W. S. Gilbert",
        "credit": "Engraved from the score by KingParamount; after The Gilbert &amp; Sullivan Archive (gsarchive.net).",
    },
    "accompaniment": ["Right Hand", "Left Hand", "Tempo"],
    "choralTracks": [],
    "soloistTracks": [],
    # (part id, dropdown label, [exact track name(s)])  — character names as the
    # score labels them; the leads keep their friendly stage names.
    "parts": [
        ("angelina", "Angelina", ["Plaintiff"]),
        ("edwin",    "Edwin",    ["Defendant"]),
        ("judge",    "Judge",    ["Judge"]),
        ("counsel",  "Counsel",  ["Counsel"]),
        ("usher",    "Usher",    ["Usher"]),
        ("foreman",  "Foreman",  ["Foreman"]),
        ("soprano",  "Soprano",  ["Soprano"]),
        ("alto",     "Alto",     ["Alto"]),
        ("tenor",    "Tenor",    ["Tenor"]),
        ("bass",     "Bass",     ["Bass"]),
    ],
    "order": [  # (file id, number, title, type)
        ("tbj01",  "1",  "Hark, the hour of ten is sounding", "Opening Chorus"),
        ("tbj01a", "1a", "Now, Jury-men, hear my advice", "Solo & Recit. (Usher) / Edwin's entrance"),
        ("tbj02",  "2",  "When first my old, old love I knew", "Song & Chorus (Defendant)"),
        ("tbj03",  "3",  "All hail, great Judge!", "Chorus & Solo (Judge)"),
        ("tbj04",  "4",  "When I, good friends, was call'd to the bar", "Song (Judge)"),
        ("tbj05",  "5",  "Swear thou the Jury!", "Recitative (Counsel)"),
        ("tbj06",  "6",  "Comes the broken flower", "Chorus & Solo (Plaintiff)"),
        ("tbj07",  "7",  "Oh, never, never, never", "Scene"),
        ("tbj08",  "8",  "May it please you, my lud!", "Solo & Chorus (Counsel)"),
        ("tbj09",  "9",  "That she is reeling", "Scene"),
        ("tbj10",  "10", "Oh, gentlemen, listen, I pray", "Song (Defendant)"),
        ("tbj11",  "11", "That seems a reasonable proposition", "Scene"),
        ("tbj12",  "12", "A nice dilemma we have here", "Sestet (with Chorus)"),
        ("tbj13",  "13", "I love him, I love him", "Duet & Scene"),
        ("tbj14",  "14", "Oh, joy unbounded", "Finale"),
    ],
}


def build(opera):
    mid_dir = os.path.join(OPERAS_DIR, opera["dir"])
    universe = set()
    for _, _, cands in opera["parts"]:
        universe |= set(cands)

    songs = []
    for fid, num, title, typ in opera["order"]:
        names = track_names(os.path.join(mid_dir, fid + ".mid"))
        voice = [nm for (nm, notes) in names if nm in universe and notes > 0]
        songs.append({"id": fid, "number": num, "title": title, "type": typ,
                      "file": fid + ".mid", "voiceTracks": voice})

    out = {
        "meta": opera["meta"],
        "accompaniment": opera["accompaniment"],
        "choralTracks": opera["choralTracks"],
        "soloistTracks": opera["soloistTracks"],
        "parts": [{"id": i, "label": l, "candidates": c} for (i, l, c) in opera["parts"]],
        "songs": songs,
    }
    dst = os.path.join(mid_dir, "songs.json")
    json.dump(out, open(dst, "w"), indent=2)
    print("wrote", os.path.normpath(dst))

    for pid, lab, cands in opera["parts"]:
        hits = [s["number"] for s in songs if set(cands) & set(s["voiceTracks"])]
        print(f"    {lab:10} -> {len(hits):2} songs: {', '.join(hits)}")


if __name__ == "__main__":
    print("==", TRIAL["meta"]["opera"], "==")
    build(TRIAL)
