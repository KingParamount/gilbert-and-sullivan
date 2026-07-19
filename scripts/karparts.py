#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Turn an archive .kar's tracks into one part per singer.

Structural work only — splitting combined and divisi staves, dropping the
lyric crib from the cast, and making sure no music is lost on the way. Who
sings which words is decided in karidentify.py; what the notes are is decided
here.
"""
import os, re, collections
import karrules as R

ACCOMP_NAMES = {"Right Hand", "Left Hand", "Tempo"}


def _is_accomp(name):
    return bool(R.re.search(r'piano|right hand|left hand|tempo|organ', name or "", R.re.I))
def _is_chorus(name):
    return bool(R.CHORUS_RE.match((name or "").strip()))
def _near(sorted_onsets, tick, tol):
    import bisect
    j = bisect.bisect_left(sorted_onsets, tick)
    for k in (j - 1, j):
        if 0 <= k < len(sorted_onsets) and abs(sorted_onsets[k] - tick) <= tol:
            return sorted_onsets[k]
    return None

def safe_filename(s):
    return re.sub(r'[<>:"/\\|?*]', "-", s).strip()[:80]


# ---------------------------------------------------------------------------
# Assemble the part list for one number (R3, R6)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def build_parts(sc, tol, flags, phantom=None):
    """-> [ {name, notes:[(tick,dur,pitch)], src} ] with combined and divisi
       staves already split into one full-length part per singer."""
    parts = []
    for tr in sc.singers:
        if tr is phantom:
            continue                       # R8: a lyric crib, not a singer
        # R6 first: chorus staves that carry two voices, or are labelled with a
        # collective ("Girls", "Men") that must become SATB.
        split = R.split_chorus_stave(tr, tol)
        if split:
            names = ", ".join(n for n, _v, _g in split)
            flags.append((tr.notes[0][0], tr.name,
                          f"R6: stave '{tr.name}' split into {names} — CHECK the "
                          f"voice assignment, and whether a third voice is needed"))
            for name, notes, _g in split:
                parts.append({"name": name, "notes": notes, "src": tr.name})
            continue
        # R3: "Boatswain/Ralph" -> two full-length staves. Without a reliable
        # way to divide the notes, both singers get the whole line and the
        # proofer deletes what isn't theirs — per the standing instruction that
        # wrong-but-pasteable beats absent.
        combo = R.combined_names(tr.name)
        if combo:
            flags.append((tr.notes[0][0], tr.name,
                          f"R3: combined stave '{tr.name}' duplicated to "
                          f"{', '.join(combo)} — DELETE the notes that are not "
                          f"each singer's (use the libretto)"))
            for nm in combo:
                parts.append({"name": nm, "notes": list(tr.notes), "src": tr.name})
            continue
        name = R.PLURAL.get(tr.name, tr.name)
        parts.append({"name": name, "notes": list(tr.notes), "src": tr.name})

    # accompaniment passes through untouched
    for tr in sc.tracks:
        if tr.is_accomp and tr.notes:
            parts.append({"name": tr.name, "notes": list(tr.notes), "src": tr.name})
    return parts


# ---------------------------------------------------------------------------
# Lyric assignment (R1, R2, R4, R5)
# ---------------------------------------------------------------------------
def catch_orphan_notes(sc, parts, tol, flags):
    """Never lose music.

    The lyric crib is dropped from the cast because it doubles the singers —
    but it doubles whoever is singing, so where the archive omitted a singer
    entirely the crib is the ONLY place that music exists. In gd17, 77 of
    Staff-2's 514 notes belong to no other stave. Dropping the crib silently
    deleted them.

    Anything left unclaimed becomes its own stave, loudly labelled, so a
    proofer renames it rather than never discovering it was gone.
    """
    phantom = sc.lyric_stave or R.find_phantom(sc, tol)
    if phantom is None:
        return parts
    # Compare by (tick, PITCH). Testing the tick alone treats a distinct line
    # that merely sounds at the same moment as already-covered, which is how
    # gd17 lost 77 notes: Staff-2 sings its own pitches underneath the chorus.
    claimed = set()
    for p in parts:
        for t, _d, pp in p["notes"]:
            claimed.add((t, pp))
    orphan = [n for n in phantom.notes if (n[0], n[2]) not in claimed]
    if not orphan:
        return parts
    parts.append({"name": "Unassigned", "notes": orphan, "src": "*orphan*"})
    flags.append((orphan[0][0], "Unassigned",
                  f"{len(orphan)} notes exist only in the lyric crib "
                  f"'{phantom.name}' and belong to no named singer — kept as an "
                  f"'Unassigned' stave. IDENTIFY the singer and rename it."))
    return parts
def attach(parts, assigned, tol):
    """Turn part['notes'] into the (tick,dur,pitch,lyric) form the writer wants,
       pairing each syllable with the note at its onset."""
    out = []
    for i, p in enumerate(parts):
        syls = sorted(assigned.get(i, []))
        # Raw syllables, verbatim. The archive marks a word end with a trailing
        # space ("sound" + "ing; ") and both the app's midi.js and Dorico's MIDI
        # import read that convention, so converting it to anything else would
        # only lose information.
        by_tick = {}
        for tick, raw in syls:
            if raw and raw.strip():
                by_tick.setdefault(tick, (raw, None))
        onsets = sorted({t for t, _d, _p in p["notes"]})
        notes = []
        used = set()
        for tick, dur, pitch in sorted(p["notes"]):
            lyr = None
            if tick not in used:
                hit = by_tick.get(tick)
                if hit is None:
                    for lt in list(by_tick):
                        if abs(lt - tick) <= tol and _near(onsets, lt, tol) == tick:
                            hit = by_tick.pop(lt); break
                if hit:
                    lyr = hit
                    used.add(tick)
            notes.append((tick, dur, pitch, lyr))
        out.append({"name": p["name"], "notes": notes, "flags": []})
    return out



# ---------------------------------------------------------------------------
# R4 — the archive holds one lyric stream; an ensemble needs several.
# For any stave whose words are a broadcast guess (or absent), prefer that
# character's OWN libretto text laid across their OWN notes.
# ---------------------------------------------------------------------------
