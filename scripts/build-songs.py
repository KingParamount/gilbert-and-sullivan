#!/usr/bin/env python3
"""Generate songs.json for an opera from its .kar files.

Reads the track names out of each .kar file and emits the per-song
`voiceTracks` list. The part->track mapping (CANDIDATES) and the human
metadata (TITLES) are hand-curated per opera below — that's the bit that needs
your judgement; everything else is derived from the files.

Usage:  python3 scripts/build-songs.py
"""
import struct, glob, os, json

KAR_DIR = os.path.join(os.path.dirname(__file__), "..", "operas", "trial-by-jury")

# --- logical part -> candidate MIDI track names (generous chorus mapping) ---
PARTS = [
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
]
ACCOMP = ["Right Hand", "Left Hand", "Tempo Track"]
CHORAL = ["Women", "Men", "Jury", "Bridesamaids"]

TITLES = {  # id: (number, title, type)
    "tbj01":  ("1",  "Hark, the hour of ten is sounding", "Opening Chorus"),
    "tbj01a": ("1a", "Now, Jury-men, hear my advice", "Solo & Recit. (Usher) / Edwin's entrance"),
    "tbj02":  ("2",  "When first my old, old love I knew", "Song & Chorus (Defendant)"),
    "tbj03":  ("3",  "All hail, great Judge!", "Chorus & Solo (Judge)"),
    "tbj04":  ("4",  "When I, good friends, was call'd to the bar", "Song (Judge)"),
    "tbj05":  ("5",  "Swear thou the Jury!", "Recitative (Counsel)"),
    "tbj06":  ("6",  "Comes the broken flower", "Chorus & Solo (Plaintiff)"),
    "tbj07":  ("7",  "Oh, never, never, never", "Scene"),
    "tbj08":  ("8",  "May it please you, my lud!", "Solo & Chorus (Counsel)"),
    "tbj09":  ("9",  "That she is reeling", "Scene"),
    "tbj10":  ("10", "Oh, gentlemen, listen, I pray", "Song (Defendant)"),
    "tbj11":  ("11", "That seems a reasonable proposition", "Scene"),
    "tbj12":  ("12", "A nice dilemma we have here", "Sestet (with Chorus)"),
    "tbj13":  ("13", "I love him, I love him", "Duet & Scene"),
    "tbj14":  ("14", "Oh, joy unbounded", "Finale"),
}
ORDER = ["tbj01", "tbj01a", "tbj02", "tbj03", "tbj04", "tbj05", "tbj06", "tbj07",
         "tbj08", "tbj09", "tbj10", "tbj11", "tbj12", "tbj13", "tbj14"]


def read_vlq(d, i):
    v = 0
    while True:
        b = d[i]; i += 1; v = (v << 7) | (b & 0x7f)
        if not b & 0x80:
            break
    return v, i


def track_names(path):
    """Return [(name, note_count)] for each track in a SMF."""
    d = open(path, "rb").read()
    fmt, ntrk, div = struct.unpack(">HHH", d[8:14])
    i = 14
    out = []
    for _ in range(ntrk):
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


def main():
    universe = set()
    for _, _, cands in PARTS:
        universe |= set(cands)

    songs = []
    for sid in ORDER:
        names = track_names(os.path.join(KAR_DIR, sid + ".kar"))
        voice = [nm for (nm, notes) in names if nm in universe and notes > 0]
        num, title, typ = TITLES[sid]
        songs.append({"id": sid, "number": num, "title": title, "type": typ,
                      "file": sid + ".kar", "voiceTracks": voice})

    out = {
        "meta": {
            "opera": "Trial by Jury", "composer": "Arthur Sullivan", "librettist": "W. S. Gilbert",
            "displayName": "Trial By Jury Learn-O-Matic 4000",
            "credit": "MIDI/karaoke files courtesy of The Gilbert &amp; Sullivan Archive (gsarchive.net).",
        },
        "accompaniment": ACCOMP,
        "choralTracks": CHORAL,
        "parts": [{"id": i, "label": l, "candidates": c} for (i, l, c) in PARTS],
        "songs": songs,
    }
    dst = os.path.join(KAR_DIR, "songs.json")
    json.dump(out, open(dst, "w"), indent=2)
    print("wrote", os.path.normpath(dst))


if __name__ == "__main__":
    main()
