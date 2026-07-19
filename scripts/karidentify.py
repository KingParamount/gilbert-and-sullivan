#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Identify singers from the LYRIC LINE, not from the stave names.

Stave names across the archive are unreliable to the point of uselessness --
"Vocal", "Staff-1", "Staff-4", "SA", "TT" -- and no alias table fixes that,
because the information is not there. The merged lyric line names its
characters explicitly, so it is the source of truth: it says WHO sings, and
the staves only say WHEN.

  1. fold abbreviated speakers onto canonical character names
     ("RUD." and "RUDOLPH" are one person; the archive abbreviates once a
     character is established, and treating those as two people wrecks the
     identification)
  2. decide each character's stave over ALL their runs at once, since a single
     run in isolation usually fits several staves
  3. rename the stave to the character
  4. split a stave two characters share -- but ONLY when their runs are clearly
     disjoint in time. Splitting restructures the music rather than relabelling
     it, so a bad split is both hard to spot and annoying to undo; ambiguous
     cases stay whole and carry both names.
  5. route the words additively: naming decides labels, rhythm decides lyrics,
     and the two run independently -- principals and chorus frequently sing the
     same words, so identifying a stave must not stop it receiving a chorus run
     it genuinely matches.
"""
import collections
import karcopy
import karrules as R

CLAIM_THRESHOLD = 0.85      # coverage of a speaker's runs before a stave is theirs
MAX_STAVES = 3              # a "character" matching more staves is identifying nothing


SPLIT_RE = R.re.compile(r"\s*(?:&|,|\band\b)\s*", R.re.I)


def fold_speakers(speakers, canonical):
    """{raw speaker -> [canonical name, ...]}.

    A label may name several people at once — "JOS. & RALPH", "CAPT. & DICK".
    Treating that string as one character's name gives it a stave of its own
    and leaves the real singers without one, which is the opposite of useful:
    those words belong to Josephine AND to Ralph."""
    canon = {R.norm(c): c for c in canonical if c}
    out = {}
    for raw in speakers:
        key0 = raw.upper().rstrip(".").strip()
        if key0 not in R.COLLECTIVE and SPLIT_RE.search(raw):
            bits = [b for b in SPLIT_RE.split(raw) if b.strip()]
            if len(bits) > 1:
                folded = fold_speakers(set(bits), canonical)
                names = []
                for b in bits:
                    for nm in folded.get(b, []):
                        if nm not in names:
                            names.append(nm)
                out[raw] = names
                continue
        out[raw] = _fold_one(raw, canon, speakers)
    return out


def _fold_one(raw, canon, speakers):
    key = raw.upper().rstrip(".").strip()
    if key in R.COLLECTIVE:
        return [key]
    n = R.norm(key)
    if not n:
        return [key]
    if n in canon:
        return [canon[n]]
    hits = [c for k, c in canon.items()
            if len(n) >= 3 and (k.startswith(n) or n.startswith(k))]
    if len(hits) == 1:
        return hits
    # no curated name matched: fold onto the longest other raw speaker that
    # this one abbreviates ("RUD" -> "RUDOLPH" when both appear)
    sibs = [s for s in speakers
            if s is not raw and len(R.norm(s)) > len(n)
            and R.norm(s).startswith(n) and len(n) >= 3]
    return [max(sibs, key=len).upper().rstrip(".")] if sibs else [key]


def _mean_cover(onsets, runs_, tol):
    if not runs_:
        return 0.0
    tot = 0.0
    for run in runs_:
        ticks = [t for t, _r in run]
        hit = sum(1 for t in ticks if karcopy._covers(onsets, [t], tol))
        tot += hit / len(ticks) if ticks else 0
    return tot / len(runs_)


def _span(runs_):
    ticks = [t for run in runs_ for t, _r in run]
    return (min(ticks), max(ticks)) if ticks else (0, 0)


def identify(crib, parts, tol, accomp, canonical, is_known=None):
    """-> (assignments, renames, splits, flags_text, stats)"""
    onsets = {i: sorted({t for t, _d, _p in p["notes"]})
              for i, p in enumerate(parts) if not accomp(p["name"])}

    raw_runs = karcopy.runs(crib, is_known)
    speakers = [s for s, _y in raw_runs if s]
    fold = fold_speakers(set(speakers), canonical)

    by_speaker = collections.OrderedDict()
    unnamed = []
    for spk, syls in raw_runs:
        if spk:
            for nm in fold.get(spk, [spk]):
                by_speaker.setdefault(nm, []).append(syls)
        else:
            unnamed.append(syls)

    collective = {s for s in by_speaker if s.upper() in R.COLLECTIVE}
    principals = [s for s in by_speaker if s not in collective]

    # Every named singer gets a stave, always. Deleting or renaming a stave is
    # trivial for the proofer; CREATING one by hand is the expensive job, so
    # too many staves beats too few. A speaker who matches nothing confidently
    # still gets one, carved from the closest stave or, failing that, from the
    # crib itself — which always carries whoever is singing.
    claim, carve, from_crib = {}, {}, []
    for spk in principals:
        cover = {i: _mean_cover(o, by_speaker[spk], tol) for i, o in onsets.items()}
        best = max(cover.values(), default=0)
        if best < CLAIM_THRESHOLD:
            hopeful = [i for i, v in cover.items() if v >= 0.5]
            if hopeful:
                carve[spk] = max(hopeful, key=lambda i: cover[i])
            else:
                from_crib.append(spk)
            continue
        idxs = [i for i, v in cover.items() if v >= best - 1e-9]
        # Claiming a stave RENAMES it, so the singer must account for most of
        # what that stave sings. Olga has one line inside a seventy-bar chorus
        # part: renaming Sopranos to Olga would delete the chorus. Carve
        # instead, leaving the chorus stave intact.
        lo, hi = _span(by_speaker[spk])
        share = min((sum(1 for t in onsets[i] if lo <= t <= hi) /
                     max(1, len(onsets[i]))) for i in idxs) if idxs else 0
        if len(idxs) <= MAX_STAVES and share >= 0.5:
            claim[spk] = idxs
        elif idxs:
            # A named singer who matches the whole chorus at once, or who sings
            # only a line of a much longer part, has no stave of their own.
            # Carve one from the notes under their own runs and leave the
            # donor stave untouched.
            carve[spk] = min(idxs)

    owners = collections.defaultdict(list)
    for spk, idxs in claim.items():
        for i in idxs:
            owners[i].append(spk)

    renames, splits, notes_txt = {}, {}, []
    for i, spks in sorted(owners.items()):
        if len(spks) == 1:
            renames[i] = spks[0]
            continue
        spans = {s: _span(by_speaker[s]) for s in spks}
        ordered = sorted(spks, key=lambda s: spans[s])
        disjoint = all(spans[a][1] < spans[b][0]
                       for a, b in zip(ordered, ordered[1:]))
        if disjoint and len(spks) <= 3:
            splits[i] = ordered
            notes_txt.append(f"stave '{parts[i]['name']}' carries "
                             f"{' then '.join(ordered)} in turn — SPLIT into "
                             f"separate staves. Check the division.")
        else:
            renames[i] = "/".join(ordered)
            notes_txt.append(f"stave '{parts[i]['name']}' is claimed by "
                             f"{', '.join(ordered)} with overlapping lines — left "
                             f"as ONE stave named '{renames[i]}'. Split by hand.")

    claimed_by = {i: set(s) for i, s in owners.items()}
    assigned = collections.defaultdict(list)
    stats = collections.Counter()

    carved_names = set(carve)

    def route(run, speaker):
        ticks = [t for t, _r in run]
        tgt = set()
        if speaker in claim:
            tgt |= set(claim[speaker])
        # additive rhythm fallback: any stave that matches and is not somebody
        # else's — principals and chorus often sing the same words
        for i, o in onsets.items():
            if karcopy._covers(o, ticks, tol):
                others = claimed_by.get(i, set()) - {speaker}
                if not others:
                    tgt.add(i)
        return tgt

    for spk, runs_ in by_speaker.items():
        for run in runs_:
            tgt = route(run, spk)
            if not tgt:
                stats["left alone"] += len(run)
                continue
            for i in tgt:
                assigned[i] += run
            stats["named" if (spk in claim or spk in carve) else
                  ("chorus" if spk in collective else "by rhythm")] += len(run)

    for run in unnamed:
        tgt = route(run, None)
        if not tgt:
            stats["left alone"] += len(run)
            continue
        for i in tgt:
            assigned[i] += run
        stats["by rhythm"] += len(run)

    return assigned, renames, splits, notes_txt, stats, carve, from_crib


def run_spans(crib, canonical, is_known=None):
    """{canonical speaker: (first tick, last tick)} over the whole number."""
    raw = karcopy.runs(crib, is_known)
    fold = fold_speakers({s for s, _y in raw if s}, canonical)
    acc = collections.defaultdict(list)
    for spk, syls in raw:
        if spk:
            for nm in fold.get(spk, [spk]):
                acc[nm] += [t for t, _r in syls]
    return {k: (min(v), max(v)) for k, v in acc.items() if v}


def split_part(part, names, spans, tol):
    """One stave holding several characters -> one stave each.

    Each takes the notes inside their own run span; notes in nobody's span go
    to ALL of them, because a duplicated note is pruned in seconds and a lost
    one is never noticed."""
    windows = [spans.get(n, (0, 0)) for n in names]
    out = []
    for nm, (lo, hi) in zip(names, windows):
        mine = [n for n in part["notes"] if lo - tol <= n[0] <= hi + tol]
        nobody = [n for n in part["notes"]
                  if not any(l - tol <= n[0] <= h + tol for l, h in windows)]
        out.append({"name": nm, "notes": sorted(set(mine + nobody)),
                    "src": part.get("src")})
    return out
