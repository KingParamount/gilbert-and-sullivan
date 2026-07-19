#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Regenerate songs.json for an opera converted by kar-to-midi.py.

Like build-songs-xml.py (which did this for Trial by Jury from Dorico
exports), but driven by the tidied .kar files and generalised to any opera:
after the upgrade each track is named for its singer, so the part list can be
read straight off the files instead of being hand-curated per opera.

What is NOT taken from the files: the human metadata. Song numbers, titles,
types and the opera's credit line are read from the EXISTING songs.json,
because those were reviewed by hand and the MIDI knows nothing about them.

Writes songs.json into the MIDI directory, so each folder becomes a
self-contained drop-in — nothing in operas/ is touched until you copy it over.

Usage:
    python3 scripts/build-songs-midi.py <opera-dir> <midi-dir>
    python3 scripts/build-songs-midi.py --all <desktop-dir>
"""
import sys, os, json, re, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
OPERAS = os.path.join(HERE, "..", "operas")
sys.path.insert(0, HERE)
from karlib import read_kar

ACCOMP = re.compile(r'piano|right hand|left hand|tempo|^rh$|^lh$|organ', re.I)
CRIB = re.compile(r'^(lyrics|staff-?\d*|vocal|melody)$', re.I)
VOICE = re.compile(r'^(soprano|alto|contralto|tenor|bass|baritone)(\s*[12])?$', re.I)

# Trial by Jury was engraved by hand from MusicXML and its songs.json is the
# product of that work; regenerating it from .kar would throw that away.
PROTECTED = {"trial-by-jury"}


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def candidates_for(name, all_names):
    """Rule 6: picking "Bass 2" must also find songs that only have "Bass"."""
    out = [name]
    m = VOICE.match(name.strip())
    if m and m.group(2):
        base = m.group(1).title()
        if base in all_names or True:
            out.append(base)
    return out


def build(opera_dir, midi_dir):
    if opera_dir in PROTECTED:
        print(f"  refusing to regenerate {opera_dir} — hand-engraved, see PROTECTED")
        return
    old_path = os.path.join(OPERAS, opera_dir, "songs.json")
    old = json.load(open(old_path))
    by_id = {s["id"]: s for s in old["songs"]}

    files = {}
    for f in sorted(glob.glob(os.path.join(midi_dir, "*.mid"))):
        files[os.path.basename(f).split(" - ")[0]] = f
    if not files:
        print(f"  no .mid files in {midi_dir}")
        return

    names = collections.Counter()
    per_song = {}
    for sid, f in files.items():
        voice = []
        for t in read_kar(f).tracks:
            n = (t.name or "").strip()
            if not n or not t.notes or ACCOMP.search(n) or CRIB.match(n):
                continue
            voice.append(n)
            names[n] += 1
        per_song[sid] = voice

    all_names = set(names)
    parts = [{"id": slug(n), "label": n, "candidates": candidates_for(n, all_names)}
             for n in sorted(all_names, key=lambda x: (-names[x], x))]

    songs = []
    for s in old["songs"]:                       # keep the reviewed order
        sid = s["id"]
        if sid not in files:
            continue
        songs.append({"id": sid, "number": s.get("number", ""),
                      "title": s.get("title", ""), "type": s.get("type", ""),
                      "file": os.path.basename(files[sid]),
                      "voiceTracks": per_song[sid]})

    out = {"meta": old["meta"],
           "accompaniment": old.get("accompaniment", []),
           "choralTracks": [], "soloistTracks": [],
           "parts": parts, "songs": songs}
    dst = os.path.join(midi_dir, "songs.json")
    json.dump(out, open(dst, "w"), indent=2)
    print(f"  {old['meta']['opera']:24} {len(songs):3} songs, {len(parts):3} parts "
          f"-> {os.path.relpath(dst, os.path.expanduser('~'))}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--all":
        root = sys.argv[2]
        for d in sorted(glob.glob(os.path.join(root, "* MIDI"))):
            stem = os.path.basename(d)[:-5]
            match = [o for o in os.listdir(OPERAS)
                     if slug(o).replace('-', '') in slug(stem).replace('-', '')
                     or slug(stem).replace('-', '') in slug(o).replace('-', '')]
            if len(match) == 1:
                build(match[0], d)
            else:
                print(f"  ?? cannot map folder {stem!r} to an opera ({match})")
    elif len(sys.argv) >= 3:
        build(sys.argv[1], sys.argv[2])
    else:
        sys.exit(__doc__)
