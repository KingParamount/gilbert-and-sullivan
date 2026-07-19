#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Copy lyrics from the archive's merged lyric line onto the singers' own staves.

COPY, never synthesise. Every syllable written out came from the source file
and sits on a tick where that singer genuinely has a note. Nothing is invented,
stretched or laid across a note-run to fit — an earlier version did all three
and produced confident nonsense.

Two ways a run of syllables finds its singer:

  1. a [CHARACTER] tag in the lyric line names them (most operas tag at every
     change of singer; The Grand Duke tags nothing at all);
  2. failing that, a stave must match the run's RHYTHM — a note onset at every
     syllable in the run, not merely one at the moment it starts. A singer
     holding a minim through a run of quavers shares the tick and not the words.

If neither settles it, the run is left alone. That is safe because the merged
lyric line is KEPT in the output, so an unassigned run is no worse than the
file is today, whereas a wrong guess actively misleads a proofer.
"""
import collections, bisect
import karrules as R


def runs(crib, is_known=None):
    """Split the lyric line into phrases: [(speaker, [(tick, raw), ...])].
       Breaks on the archive's own line breaks and on any change of speaker."""
    out = []
    cur, spk = [], None
    for tick, raw, speaker in R.segment_lyrics(crib, is_known):
        if raw in ("\r", "\n", "\r\n"):
            if cur:
                out.append((spk, cur)); cur = []
            continue
        if not raw.strip():
            continue
        if speaker != spk and cur:
            out.append((spk, cur)); cur = []
        spk = speaker
        cur.append((tick, raw))
    if cur:
        out.append((spk, cur))
    return out


def _covers(onsets, ticks, tol):
    """Does this stave have a note at EVERY syllable of the run?"""
    for t in ticks:
        i = bisect.bisect_left(onsets, t)
        if not any(0 <= k < len(onsets) and abs(onsets[k] - t) <= tol
                   for k in (i - 1, i)):
            return False
    return True


def copy_lyrics(crib, parts, resolver, tol, flags, accomp, soloists=()):
    """-> {part_index: [(tick, raw_syllable)]}

    soloists: stave names known to be a named character, so that a collective
    tag which resolves to nothing (CHORUS in a number whose chorus staves are
    called Staff-1 and Staff-4) can fall back to everyone who is NOT one."""
    def is_known(name):
        return bool(resolver.resolve(name)[0]) or name.upper() in R.COLLECTIVE
    soloists = set(soloists)
    onsets = {i: sorted({t for t, _d, _p in p["notes"]})
              for i, p in enumerate(parts) if not accomp(p["name"])}
    assigned = collections.defaultdict(list)
    stats = collections.Counter()
    unknown = collections.Counter()

    for speaker, syls in runs(crib, is_known):
        ticks = [t for t, _r in syls]
        targets = []
        if speaker:
            named, ok = resolver.resolve(speaker)
            if named:
                targets = [i for i, p in enumerate(parts) if p["name"] in named]
                # a tag still has to be plausible: keep only staves that sing here
                sung = [i for i in targets if i in onsets
                        and _covers(onsets[i], ticks, tol)]
                targets = sung or targets
                stats["by tag"] += len(syls)
            elif speaker.upper().rstrip(".") in R.COLLECTIVE:
                # a collective with no matching voice-part stave: the chorus is
                # whoever is left once the named soloists are set aside
                pool = {i: o for i, o in onsets.items()
                        if parts[i]["name"] not in soloists}
                targets = [i for i, o in pool.items() if _covers(o, ticks, tol)]
                if targets:
                    stats["by tag"] += len(syls)
                else:
                    unknown[speaker] += 1
            else:
                unknown[speaker] += 1

        if not targets:
            targets = [i for i, ons in onsets.items() if _covers(ons, ticks, tol)]
            if not targets:
                stats["left alone (nobody matches the rhythm)"] += len(syls)
                continue
            stats["by rhythm"] += len(syls)

        for i in targets:
            assigned[i] += syls

    for spk, n in unknown.most_common(8):
        flags.append((0, "?", f"speaker tag '{spk}' ({n} runs) matched no stave "
                              f"— those lyrics were left on the backup line only"))
    return assigned, stats
