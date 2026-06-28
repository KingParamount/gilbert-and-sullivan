#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Generate songs.json for each opera from its .kar files.

Track names are read straight out of the .kar files to compute each song's
`voiceTracks`. The part->track mapping (`parts`) and the human metadata
(`order`) are hand-curated per opera in OPERAS below — that's the bit that needs
judgement; everything else is derived from the files.

Usage:  python3 scripts/build-songs.py
"""
import struct, glob, os, json

HERE = os.path.dirname(__file__)
OPERAS_DIR = os.path.join(HERE, "..", "operas")

# ---------------------------------------------------------------------------
# Trial by Jury
# ---------------------------------------------------------------------------
TRIAL = {
    "dir": "trial-by-jury",
    "meta": {
        "opera": "Trial by Jury", "composer": "Arthur Sullivan", "librettist": "W. S. Gilbert",
        "credit": "MIDI/karaoke files courtesy of The Gilbert &amp; Sullivan Archive (gsarchive.net).",
    },
    "accompaniment": ["Right Hand", "Left Hand", "Tempo Track", "Tempo"],
    "choralTracks": ["Women", "Men", "Jury", "Bridesamaids"],
    "soloistTracks": [],
    "parts": [
        ("angelina", "Angelina", ["Plaintiff"]),
        ("edwin",    "Edwin",    ["Defendant", "Counsel/Defendant"]),
        ("judge",    "Judge",    ["Judge", "Usher/Judge", "Judge/Counsel"]),
        ("counsel",  "Counsel",  ["Counsel", "Counsel/Defendant", "Judge/Counsel"]),
        ("usher",    "Usher",    ["Usher", "Usher/Judge", "Vocal"]),
        ("foreman",  "Foreman",  ["Foreman"]),
        ("soprano",  "Soprano",  ["Soprano", "Sopranos", "Women", "Bridesamaids"]),
        ("alto",     "Alto",     ["Alto", "Altos", "Women", "Bridesamaids"]),
        ("tenor",    "Tenor",    ["Tenor", "Tenors", "Men", "Jury"]),
        ("bass",     "Bass",     ["Bass", "Basses", "Men", "Jury"]),
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

# ---------------------------------------------------------------------------
# The Sorcerer
# ---------------------------------------------------------------------------
SORCERER = {
    "dir": "the-sorcerer",
    "meta": {
        "opera": "The Sorcerer", "composer": "Arthur Sullivan", "librettist": "W. S. Gilbert",
        "credit": "MIDI/karaoke files courtesy of The Gilbert &amp; Sullivan Archive (gsarchive.net).",
    },
    "accompaniment": ["Right Hand", "Left Hand", "Piano RH", "Piano LH", "Tempo", "Tempo Track"],
    "choralTracks": [],
    "soloistTracks": ["Soloists"],
    "parts": [
        ("sir-marmaduke", "Sir Marmaduke",          ["Sir Marmaduke", "Sir. M", "Sir M./Dr. D."]),
        ("alexis",        "Alexis",                 ["Alexis", "Vocal", "Mr. Wells/Alexis", "Soloists"]),
        ("dr-daly",       "Dr Daly",                ["Dr Daly", "Dr. Daly", "Sir M./Dr. D."]),
        ("mr-wells",      "J. W. Wells",            ["Mr Wells", "Mr. Wells", "Mr. Wells/Alexis"]),
        ("lady-sangazure", "Lady Sangazure",        ["Lady Sangazure", "Lady S.", "Lady S./Mrs. P.", "Lady S. & Mrs. P", "Soloists"]),
        ("aline",         "Aline",                  ["Aline", "Aline & Constance", "Soloists"]),
        ("mrs-partlet",   "Mrs Partlet",            ["Mrs Partlet", "Mrs. Partlet", "Lady S./Mrs. P.", "Lady S. & Mrs. P"]),
        ("constance",     "Constance",              ["Constance", "Aline & Constance"]),
        ("soprano",       "Soprano",                ["Sopranos", "Soprano"]),
        ("alto",          "Alto",                   ["Altos", "Alto"]),
        ("tenor",         "Tenor",                  ["Tenors", "Tenor"]),
        ("bass",          "Bass",                   ["Basses", "Bass"]),
    ],
    "order": [  # overture (sorc00) deliberately omitted — nothing for a singer to learn
        ("sorc01",     "1",      "Ring forth, ye bells", "Introduction & Chorus"),
        ("sorc02",     "2",      "When he is here", "Recit. & Aria (Mrs. Partlet & Constance)"),
        ("sorc03",     "3",      "Time was when love and I were well acquainted", "Recit. & Ballad (Dr. Daly)"),
        ("sorc04",     "4",      "Recit. & Minuet", "Sir Marmaduke, Dr. Daly & Alexis"),
        ("sorc05",     "5",      "With heart and with voice", "Chorus"),
        ("sorc06",     "6",      "Oh, happy young heart", "Recit. & Aria (Aline)"),
        ("sorc07",     "7 & 8",  "Recit. & Chorus", "Lady Sangazure & Chorus"),
        ("sorc09",     "9",      "Welcome joy, adieu to sadness", "Duet (Lady Sangazure & Sir Marmaduke)"),
        ("sorc10",     "10",     "Ensemble", "Act I Ensemble"),
        ("sorc11",     "11",     "Love feeds on many kinds of food", "Ballad (Alexis)"),
        ("sorc12",     "12",     "My name is John Wellington Wells", "Patter Song (Mr. Wells)"),
        ("sorc13",     "13",     "Sprites of earth and air", "Incantation (Aline, Alexis & Mr. Wells)"),
        ("sorc14",     "14",     "Now to the banquet we press", "Finale Act I — 1884 version"),
        ("sorc14orig", "14",     "Now to the banquet we press", "Finale Act I — 1877 original"),
        ("sorc15",     "15",     "'Tis twelve, I think", "Trio & Chorus — 1884 version"),
        ("sorc1577",   "15",     "Happy are we in our loving frivolity", "Chorus — 1877 original"),
        ("sorc16",     "16",     "Ensemble", "Act II Ensemble — 1884 version"),
        ("sorc1677",   "16",     "Ensemble", "Act II Ensemble — 1877 original"),
        ("sorc17",     "17",     "Thou hast the power thy vaunted love", "Ballad (Alexis)"),
        ("sorc18",     "18",     "I rejoice that it's decided", "Quintette"),
        ("sorc19",     "19",     "Oh, I have wrought much evil with my spells!", "Recit. & Duet (Lady Sangazure & Mr. Wells)"),
        ("sorc20",     "20",     "Alexis! Doubt me not", "Recit. & Air (Aline)"),
        ("sorc21",     "21 & 22", "Oh, my voice is sad and low", "Song & Ensemble (Dr. Daly)"),
        ("sorc24",     "24",     "Finale", "Finale Act II"),
    ],
}

OPERAS = [TRIAL, SORCERER]


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


def build(opera):
    kar_dir = os.path.join(OPERAS_DIR, opera["dir"])
    universe = set()
    for _, _, cands in opera["parts"]:
        universe |= set(cands)

    songs = []
    for fid, num, title, typ in opera["order"]:
        names = track_names(os.path.join(kar_dir, fid + ".kar"))
        voice = [nm for (nm, notes) in names if nm in universe and notes > 0]
        songs.append({"id": fid, "number": num, "title": title, "type": typ,
                      "file": fid + ".kar", "voiceTracks": voice})

    out = {
        "meta": opera["meta"],
        "accompaniment": opera["accompaniment"],
        "choralTracks": opera["choralTracks"],
        "soloistTracks": opera["soloistTracks"],
        "parts": [{"id": i, "label": l, "candidates": c} for (i, l, c) in opera["parts"]],
        "songs": songs,
    }
    dst = os.path.join(kar_dir, "songs.json")
    json.dump(out, open(dst, "w"), indent=2)
    print("wrote", os.path.normpath(dst))

    # coverage report
    for pid, lab, cands in opera["parts"]:
        hits = [s["number"] for s in songs if set(cands) & set(s["voiceTracks"])]
        print(f"    {lab:16} -> {len(hits):2} songs: {', '.join(hits)}")


if __name__ == "__main__":
    for op in OPERAS:
        print("\n==", op["meta"]["opera"], "==")
        build(op)
