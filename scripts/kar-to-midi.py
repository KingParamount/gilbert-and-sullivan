#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Rebuild a G&S Archive .kar as one MIDI track per named singer.

Deliberately smaller in scope than the MusicXML route it replaces. That one
tried to solve notation — bars, note values, dots, tuplets, anacruses — and
did it badly enough to be unusable, when Dorico solves notation superbly from
a plain MIDI file. So this writes MIDI, keeps the performance data exactly as
the archive holds it, and does only what the archive cannot do for itself:

  * give every named singer their own track (splitting combined and divisi
    staves, and dropping the phantom lyric crib)
  * put each singer's words on their own track where they can be identified
  * leave shared lyric lines shared, rather than inventing placements

Where several singers share one lyric line, the line is copied to all of them.
That is no worse than the .kar is today and it stops the tool guessing.

Output is usable in two places: import to Dorico to correct, or drop straight
into the app alongside build-songs-xml.py.

Usage:
    python3 scripts/kar-to-midi.py <opera-dir> <out-dir>
        [--libretto=DIR] [--score=FILE.pdf] [--abbrev=map.json]
"""
import sys, os, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from karlib import read_kar, write_smf
import karrules as R
import karcopy
import karidentify

import karparts as karmx


def _runs_of(crib, canonical, known, want):
    import karcopy
    raw = karcopy.runs(crib, known)
    fold = karidentify.fold_speakers({s for s, _y in raw if s}, canonical)
    return [(s, y) for s, y in raw if s and want in fold.get(s, [s])]


def convert(opera_dir, out_dir, libretto=None, score_pdf=None, abbrev=None):
    cfg = json.load(open(os.path.join(HERE, "..", "operas", opera_dir, "songs.json")))
    os.makedirs(out_dir, exist_ok=True)

    aliases, bodymap = {}, {}
    bm = os.path.join(HERE, "body-map.json")
    if os.path.exists(bm):
        bodymap = {k.upper(): v for k, v in json.load(open(bm)).get(opera_dir, {}).items()}
    for k, v in bodymap.items():
        if isinstance(v, list):
            aliases[k] = v
    for p in cfg.get("parts", []):
        for c in p.get("candidates", []):
            aliases[c] = c
        aliases[p["label"]] = p.get("candidates", [p["label"]])[0]

    report = [f"# {cfg['meta']['opera']} — per-singer MIDI", "",
              "Lyrics are COPIED from the merged lyric line, never invented. The",
              "merged line is kept in every file as a backup, so a number where",
              "attribution fails is no worse than the original .kar.", ""]
    totals = collections.Counter()

    for song in cfg["songs"]:
        src = os.path.join(HERE, "..", "operas", opera_dir, song["file"])
        if not os.path.exists(src):
            continue
        sc = read_kar(src)
        tol = max(1, sc.division // R.TOL_NUM)
        flags = []

        crib = sc.lyric_stave or R.find_phantom(sc, tol)
        parts = karmx.build_parts(sc, tol, flags, crib)

        # songs.json already records who a generic stave really is — Mikado's
        # "Braid the raven hair" has Staff-1/Staff-4/Vocal and a curated
        # partTracks entry naming Vocal as Pitti-Sing. Rename accordingly, so
        # the stave carries a singer's name and the lyric tag can find it.
        labels = {p["id"]: p["label"] for p in cfg.get("parts", [])}
        for pid, tracks in (song.get("partTracks") or {}).items():
            for xp in parts:
                if xp["name"] in tracks and pid in labels:
                    flags.append((0, labels[pid],
                                  f"stave '{xp['name']}' renamed to "
                                  f"'{labels[pid]}' per songs.json partTracks"))
                    xp["name"] = labels[pid]
        parts = karmx.catch_orphan_notes(sc, parts, tol, flags)
        names = [p["name"] for p in parts]
        resolver = R.Resolver([n for n in names if not karmx._is_accomp(n)], aliases)

        stats = collections.Counter()
        if crib:
            canonical = [x["label"] for x in cfg.get("parts", [])]
            known = (lambda n: True)
            assigned, renames, splits, notes_txt, stats, carve, from_crib = \
                karidentify.identify(crib, parts, tol, karmx._is_accomp,
                                     canonical, known)

            # Two staves must never end up with the same name. build_parts
            # splits "Boatswain/Ralph" into two identical staves, so both match
            # Ralph's runs equally and both would be renamed to him — leaving a
            # duplicate and no Boatswain.
            taken = set()
            for i, nm in sorted(renames.items()):
                if nm in taken:
                    flags.append((0, parts[i]["name"],
                                  f"stave '{parts[i]['name']}' also matches "
                                  f"'{nm}', who already has a stave — left under "
                                  f"its original name. CHECK which is which."))
                    continue
                taken.add(nm)
                if parts[i]["name"] != nm:
                    flags.append((0, nm, f"stave '{parts[i]['name']}' identified "
                                         f"as '{nm}' from the lyric line"))
                    parts[i]["name"] = nm
            for msg in notes_txt:
                flags.append((0, "?", msg))

            # Rebuild parts and assignments together, so a split never has to be
            # spliced into an index-keyed map (that arithmetic was wrong and
            # silently dropped most of the lyrics).
            spans = karidentify.run_spans(crib, canonical, known)
            rebuilt, rebuilt_assign = [], []
            for i, part in enumerate(parts):
                if i in splits:
                    for np_ in karidentify.split_part(part, splits[i], spans, tol):
                        rebuilt.append(np_)
                        rebuilt_assign.append(list(assigned.get(i, [])))
                else:
                    rebuilt.append(part)
                    rebuilt_assign.append(list(assigned.get(i, [])))
            # carved-out singers: a named character whose line lives inside a
            # chorus stave gets their own stave of just their notes
            for spk, src_i in carve.items():
                lo, hi = spans.get(spk, (0, 0))
                donor = parts[src_i]
                notes = [n for n in donor["notes"] if lo - tol <= n[0] <= hi + tol]
                if not notes:
                    continue
                rebuilt.append({"name": spk, "notes": notes, "src": donor["name"]})
                rebuilt_assign.append([sy for _sp, run in
                                       _runs_of(crib, canonical, known, spk)
                                       for sy in run])
                flags.append((lo, spk, f"'{spk}' has no stave of their own — one "
                                       f"was carved from '{donor['name']}' "
                                       f"({len(notes)} notes) where they sing. "
                                       f"CHECK the extent."))
            # nobody's stave fits at all: build from the crib, which carries
            # whoever is singing at the time
            for spk in from_crib:
                lo, hi = spans.get(spk, (0, 0))
                notes = [n for n in crib.notes if lo - tol <= n[0] <= hi + tol]
                if not notes:
                    continue
                rebuilt.append({"name": spk, "notes": notes, "src": "*crib*"})
                rebuilt_assign.append([sy for _sp, run in
                                       _runs_of(crib, canonical, known, spk)
                                       for sy in run])
                flags.append((lo, spk, f"'{spk}' matches no existing stave — one "
                                       f"was built from the lyric line's own notes "
                                       f"({len(notes)}). CHECK the pitches."))
            parts = rebuilt
            assigned = {i: v for i, v in enumerate(rebuilt_assign)}

            xparts = karmx.attach(parts, assigned, tol)
            xparts.append({"name": crib.name or "Lyrics",
                           "notes": [(t, d, p_, None) for t, d, p_ in crib.notes],
                           "raw_lyrics": list(crib.lyrics), "flags": []})
        else:
            xparts = karmx.attach(parts, {}, tol)
            inline = {t.name: t.lyrics for t in sc.tracks if t.lyrics}
            for xp, pt in zip(xparts, parts):
                own = inline.get(pt.get("src")) or inline.get(xp["name"])
                if own:
                    xp["raw_lyrics"] = list(own)
                    stats["kept inline"] += len(own)

        dst = os.path.join(out_dir, karmx.safe_filename(
            f"{song['id']} - {song['title']}") + ".mid")
        write_smf(dst, sc, xparts, title=song.get("title"))

        singers = [n for n in names if not karmx._is_accomp(n)]
        totals.update(stats)
        print(f"  {song['id']:12} {len(singers):2} singers | "
              f"{stats.get('named', 0):5} named, {stats.get('chorus', 0):5} chorus, "
              f"{stats.get('by rhythm', 0):5} rhythm, "
              f"{stats.get('left alone', 0):4} left")
        report.append(f"## {song['id']} — {song['title']}")
        report.append(f"* singers: {', '.join(singers)}")
        report.append(f"* syllables: {stats.get('named',0)} to a named singer, "
                      f"{stats.get('chorus',0)} to chorus, "
                      f"{stats.get('by rhythm',0)} by rhythm alone, "
                      f"{stats.get('left alone',0)} left on the backup line only")
        for _t, who, msg in flags:
            report.append(f"  * `{who}` — {msg}")
        report.append("")

    open(os.path.join(out_dir, "REPORT.md"), "w").write("\n".join(report) + "\n")
    tot = sum(totals[k] for k in ("named", "chorus", "by rhythm", "left alone"))
    if tot:
        for k in ("named", "chorus", "by rhythm", "left alone"):
            print(f"  {totals[k]:6} {k} ({100*totals[k]/tot:.0f}%)")



if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(libretto=None, score_pdf=None, abbrev=None)
    for a in sys.argv[1:]:
        if a.startswith("--libretto="):
            opts["libretto"] = a.split("=", 1)[1]
        elif a.startswith("--score="):
            opts["score_pdf"] = a.split("=", 1)[1]
        elif a.startswith("--abbrev="):
            opts["abbrev"] = json.load(open(a.split("=", 1)[1]))
    if len(args) < 2:
        sys.exit(__doc__)
    convert(args[0], args[1], **opts)
