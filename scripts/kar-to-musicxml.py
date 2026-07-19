#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""Outbound leg: G&S Archive .kar -> per-character MusicXML for human proofing.

This produces a DRAFT for a human to correct in Dorico, not a finished score.
Notation quality is explicitly not a goal — nothing is ever engraved from this.
What matters is that every singer has their own stave, every stave has the
right words, and everything the tool guessed is flagged in red so the proofer
knows where to look.

Usage:
    python3 scripts/kar-to-musicxml.py <opera-dir> <out-dir> [--libretto DIR]
    python3 scripts/kar-to-musicxml.py trial-by-jury /tmp/tbj-xml

Writes <out-dir>/<id> - <title>.musicxml plus a REPORT.md listing every flag.
"""
import sys, os, json, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from karlib import read_kar, write_musicxml, syllabify
import karrules as R
import karlibretto as LIB

HERE = os.path.dirname(os.path.abspath(__file__))
OPERAS = os.path.join(HERE, "..", "operas")

# Titles that legitimately are NOT the first sung line (rule 7 whitelist).
TITLE_EXEMPT = re.compile(
    r'\b(finale|overture|entr|act\s*(i{1,3}|[123])\b|reprise|exit|march|'
    r'dance|ballet|introduction|epilogue|curtain)\b', re.I)


def safe_filename(s):
    return re.sub(r'[<>:"/\\|?*]', "-", s).strip()[:80]


# ---------------------------------------------------------------------------
# Assemble the part list for one number (R3, R6)
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

def lyric_source(sc, tol):
    """The stave carrying the words, and the phantom stave to exclude from the
       cast (which may be the same one).

       Three cases seen in the archive:
         1. a stave literally named "Lyrics"          (tbj05, tbj12)
         2. a phantom under a generic name            (tbj04 -> "Staff-1")
         3. no phantom; a real singer carries the
            words inline and IS part of the cast      (tbj01 -> Soprano)
       Only 1 and 2 are removed from the cast."""
    ls = sc.lyric_stave
    if ls:
        return ls, ls
    ph = R.find_phantom(sc, tol)
    if ph:
        return ph, ph
    best = max(sc.singers, key=lambda t: len(t.lyrics), default=None)
    if best and len(best.lyrics) > 4:
        return best, None                  # genuine singer; keep it in the cast
    return None, None


def assign(sc, parts, resolver, tol, flags):
    """Attach each syllable of the lyric stream to the right part's notes.

    R2 is the governing principle: the lyric stave's own notes are ignored
    entirely. Syllables are matched to SINGER onsets by time."""
    src, _phantom = lyric_source(sc, tol)
    if src is None:
        return {}
    stream = R.segment_lyrics(src)

    # onset index per part
    onsets = {}
    for i, p in enumerate(parts):
        if p["name"] in ACCOMP_NAMES or _is_accomp(p["name"]):
            continue
        onsets[i] = sorted({t for t, _d, _p in p["notes"]})

    assigned = collections.defaultdict(list)   # part_index -> [(tick, raw)]
    last = None
    unresolved = collections.Counter()
    broadcast = collections.Counter()
    shaky = set()                              # parts whose words are a guess

    for tick, raw, speaker in stream:
        if raw in ("\r", "\n", "\r\n") or not raw.strip():
            continue
        sounding = [i for i, ons in onsets.items() if _near(ons, tick, tol)]
        targets, confident = resolver.resolve(speaker) if speaker else ([], False)
        if speaker and not confident:
            unresolved[speaker] += 1

        cand = [i for i in sounding
                if parts[i]["name"] in targets] if targets else list(sounding)

        if targets and not cand:
            # named singer isn't sounding here — trust the tag over the notes
            # only if that stave exists at all; otherwise fall back to sounding
            named = [i for i, p in enumerate(parts) if p["name"] in targets]
            if named:
                cand = named
                flags.append((tick, parts[named[0]]["name"],
                              f"R2/R4: '{speaker}' is tagged here but has no note "
                              f"at this point — syllable placed anyway, CHECK"))
            else:
                cand = list(sounding)

        if not cand:
            flags.append((tick, "?", f"orphan syllable {raw.strip()!r} — no singer "
                                     f"has a note here (missing stave?)"))
            continue

        if len(cand) == 1:
            pick = cand
        elif targets:
            pick = cand                       # the tag named them; trust it
        else:
            pick = cand                       # tutti assumption — see note above
            if not all(_is_chorus(parts[i]["name"]) for i in cand):
                broadcast[tuple(sorted(parts[i]["name"] for i in cand))] += 1
                shaky.update(cand)
        for i in pick:
            assigned[i].append((tick, raw))
        last = pick[0]

    for who, n in broadcast.most_common(6):
        flags.append((0, who[0], f"R4: {n} syllables given to ALL of "
                                 f"{', '.join(who)} because the lyric line names "
                                 f"nobody — if they sing DIFFERENT words here, the "
                                 f"other lines must come from the libretto"))
    assigned["__shaky__"] = shaky
    for spk, n in unresolved.most_common():
        flags.append((0, "?", f"R1: speaker tag '{spk}' ({n} syllables) did not "
                              f"match any stave — CHECK who this is"))
    return assigned


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


def attach(parts, assigned, tol):
    """Turn part['notes'] into the (tick,dur,pitch,lyric) form the writer wants,
       pairing each syllable with the note at its onset."""
    out = []
    for i, p in enumerate(parts):
        syls = sorted(assigned.get(i, []))
        texts = syllabify([raw for _t, raw in syls])
        by_tick = {}
        for (tick, _raw), (text, syl) in zip(syls, texts):
            if text:
                by_tick.setdefault(tick, (text, syl))
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

def apply_libretto(sc, parts, assigned, resolver, libretto_dir, page, tol, flags):
    structured = LIB.load_blocks(libretto_dir, page) if libretto_dir else []
    if structured:
        entries = LIB.flatten(structured)
    else:
        entries = [(spk, lines, False)
                   for spk, lines in (LIB.load(libretto_dir, page)
                                      if libretto_dir else [])]
    if not entries:
        return assigned
    src, _ph = lyric_source(sc, tol)
    dictionary = LIB.build_dictionary([raw for _t, raw in src.lyrics]) if src else {}

    shaky = assigned.get("__shaky__", set())
    text_for = collections.defaultdict(list)
    ensemble = set()                 # staves named inside a parallel-column block
    unmatched = collections.Counter()
    for speaker, lines, simul in entries:
        names, conf = resolver.resolve(speaker)
        if not names:
            unmatched[speaker] += 1
            continue
        for nm in names:
            text_for[nm].append(lines)
            if simul:
                ensemble.add(nm)

    for i, p in enumerate(parts):
        if _is_accomp(p["name"]):
            continue
        needs = (i in shaky) or not assigned.get(i) or p["name"] in ensemble
        if not needs or p["name"] not in text_for:
            continue
        onsets = sorted({t for t, _d, _pp in p["notes"]})
        lines = [ln for block in text_for[p["name"]] for ln in block]
        stream, line_ends = LIB.syllable_stream(lines, dictionary)
        if not stream or not onsets:
            continue
        placed = LIB.lay_across(stream, p["notes"], sc.division, line_ends)
        assigned[i] = [(tick, syl + (" " if ends else ""))
                       for tick, (syl, ends, _c) in placed]
        guessed = sum(1 for _t, (_s, _e, c) in placed if not c)
        flags.append((onsets[0], p["name"],
                      f"R4: {len(stream)} syllables of {p['name']}'s libretto text "
                      f"laid across {len(onsets)} notes"
                      + ("" if len(stream) == len(onsets) else
                         f" (COUNTS DIFFER — placement is stretched, RE-PLACE)")
                      + (f"; {guessed} syllable splits guessed" if guessed else "")))
    for spk, n in unmatched.most_common(8):
        flags.append((0, "?", f"R4: libretto speaker '{spk}' matched no stave "
                              f"— their words were NOT placed"))
    return assigned



# ---------------------------------------------------------------------------
# R13 — the archive sometimes omits a singer entirely (tbj10 has Bridesmaids
# in the libretto and in the words, but no Bridesmaids stave). The lyric crib
# carries the tune of WHOEVER is singing, so the notes it plays that no real
# stave claims are, by elimination, the missing singer's. Build a stave from
# them.
#
# This invents a part from a crib and is the most speculative rule here — but
# the alternative is a number arriving with a third of its cast absent, and an
# invented stave is visible and deletable in a way that an absence is not.
# ---------------------------------------------------------------------------

def add_missing_staves(sc, parts, blocks, resolver, bodymap, tol, flags):
    phantom = sc.lyric_stave or R.find_phantom(sc, tol)
    if not blocks:
        return parts
    have = {p["name"] for p in parts}
    create, principal = [], []
    for speaker, _lines in blocks:
        if resolver.resolve(speaker)[0]:
            continue
        rule = bodymap.get(speaker.upper())
        nm = speaker.title()
        if nm in have or nm in [x[0] for x in create] + [x[0] for x in principal]:
            continue
        if isinstance(rule, str) and rule.startswith("*principal:"):
            principal.append((nm, rule[len("*principal:"):].rstrip("*")))
        elif rule == "*create*" or (rule is None and _looks_like_a_name(speaker)):
            create.append((nm, None))
    if not create and not principal:
        return parts

    by_name = {p["name"]: p for p in parts}
    claimed = set()
    for p in parts:
        if _is_accomp(p["name"]):
            continue
        for t, _d, _pp in p["notes"]:
            claimed.add(t)
    orphan = [n for n in (phantom.notes if phantom else [])
              if not any(abs(n[0] - c) <= tol for c in claimed)]

    # R14 — a chorus member who steps out for a line and goes back in (Samuel
    # in "Pour, oh pour"). Their stave FOLLOWS THE CHORUS LINE for the whole
    # number and carries their solo on top: in pp01 Samuel's 149 onsets are 85
    # shared with the chorus plus 64 of his own. Build the same shape — the
    # mapped chorus voice's notes, plus the crib notes no one else claims.
    for nm, voice in principal:
        chorus = by_name.get(voice)
        if chorus is None:
            flags.append((0, "?", f"R14: '{nm}' is mapped to chorus voice "
                                  f"'{voice}', which this number has no stave for "
                                  f"— NOT created; fix scripts/body-map.json"))
            continue
        notes = sorted(set(chorus["notes"]) | set(orphan))
        parts.append({"name": nm, "notes": notes, "src": "*R14*"})
        flags.append((notes[0][0] if notes else 0, nm,
                      f"R14: '{nm}' has no stave — built one following the "
                      f"{voice} line ({len(chorus['notes'])} notes) plus "
                      f"{len(orphan)} unclaimed crib notes as their solo. CHECK "
                      f"which is chorus and which is solo, and the voice choice."))

    # R13 — a character the archive dropped entirely, with no chorus to follow.
    if create:
        if len(orphan) < 4:
            flags.append((0, "?", f"R13: libretto names "
                                  f"{', '.join(n for n, _ in create)} with no stave, "
                                  f"and the crib has no spare notes to build from "
                                  f"— THESE SINGERS ARE MISSING"))
        else:
            share = max(1, len(orphan) // len(create))
            for i, (nm, _v) in enumerate(create):
                chunk = orphan if len(create) == 1 else orphan[i * share:(i + 1) * share]
                if not chunk:
                    continue
                parts.append({"name": nm, "notes": list(chunk), "src": "*R13*"})
                flags.append((chunk[0][0], nm,
                              f"R13: '{nm}' has no stave in the archive file — one "
                              f"was BUILT from {len(chunk)} crib notes no other "
                              f"singer claims. CHECK the notes as well as the words."))
    return parts


def _looks_like_a_name(speaker):
    """A single capitalised word that is not a known collective — probably a
       character the transcriber dropped."""
    s = speaker.strip()
    return (s.upper() not in R.COLLECTIVE and " " not in s and s.isalpha()
            and len(s) > 2)


# ---------------------------------------------------------------------------
def convert_opera(opera_dir, out_dir, libretto_dir=None):
    cfg = json.load(open(os.path.join(OPERAS, opera_dir, "songs.json")))
    os.makedirs(out_dir, exist_ok=True)
    bodymap = {}
    bm_path = os.path.join(HERE, "body-map.json")
    if os.path.exists(bm_path):
        raw = json.load(open(bm_path)).get(opera_dir, {})
        bodymap = {k.upper(): v for k, v in raw.items()}
    aliases = {}
    for k, v in bodymap.items():
        if isinstance(v, list):
            aliases[k] = v
    for p in cfg.get("parts", []):
        for c in p.get("candidates", []):
            aliases[c] = c
        aliases[p["label"]] = p.get("candidates", [p["label"]])[0]

    report = [f"# {cfg['meta']['opera']} — kar → MusicXML draft report", ""]
    total_flags = 0

    for song in cfg["songs"]:
        src = os.path.join(OPERAS, opera_dir, song["file"])
        if not os.path.exists(src):
            report.append(f"## {song['id']} — SOURCE MISSING ({song['file']})\n")
            continue
        sc = read_kar(src)
        tol = max(1, sc.division // R.TOL_NUM)
        flags = []

        _src, phantom = lyric_source(sc, tol)
        if phantom is not None and not phantom.is_lyric_stave:
            flags.append((0, "?", f"R8: stave '{phantom.name}' is a lyric crib, "
                                  f"not a singer — dropped from the cast"))
        parts = build_parts(sc, tol, flags, phantom)
        names = [p["name"] for p in parts]
        resolver = R.Resolver([n for n in names if not _is_accomp(n)], aliases)
        blocks = [(spk, ln) for spk, ln, _s in
                  LIB.flatten(LIB.load_blocks(libretto_dir, song["id"]))] \
                 if libretto_dir else []
        parts = add_missing_staves(sc, parts, blocks, resolver, bodymap, tol, flags)
        names = [p["name"] for p in parts]
        resolver = R.Resolver([n for n in names if not _is_accomp(n)], aliases)
        assigned = assign(sc, parts, resolver, tol, flags)
        assigned = apply_libretto(sc, parts, assigned, resolver, libretto_dir,
                                  song["id"], tol, flags)
        assigned.pop("__shaky__", None)

        # rule 7: title should be the first sung line, finales excepted
        first = "".join(raw for _t, raw in sorted(
            (t, r) for i in assigned for t, r in assigned[i]))[:60]
        if not TITLE_EXEMPT.search(song.get("type", "") + " " + song["title"]):
            if first and R.norm(song["title"][:18]) not in R.norm(first):
                flags.append((0, "?", f"R7: title {song['title']!r} is not the first "
                                      f"sung line ({first.strip()[:40]!r}) — CHECK "
                                      f"the number is not misidentified"))

        xparts = attach(parts, assigned, tol)
        for tick, who, msg in flags:
            tgt = next((x for x in xparts if x["name"] == who), xparts[0] if xparts else None)
            if tgt is not None:
                tgt["flags"].append((tick, msg))

        title = f"No. {song.get('number', '?')} — {song['title']}"
        dst = os.path.join(out_dir, safe_filename(f"{song['id']} - {song['title']}")
                           + ".musicxml")
        write_musicxml(dst, sc, xparts, work_title=title)

        total_flags += len(flags)
        report.append(f"## {song['id']} — {song['title']}")
        report.append(f"* staves: {', '.join(n for n in names if not _is_accomp(n))}")
        if flags:
            report.append(f"* **{len(flags)} flag(s):**")
            for _t, who, msg in flags:
                report.append(f"  * `{who}` — {msg}")
        else:
            report.append("* no flags")
        report.append("")
        print(f"  {song['id']:14} {len(names):2} parts, {len(flags):3} flags -> "
              f"{os.path.basename(dst)}")

    open(os.path.join(out_dir, "REPORT.md"), "w").write("\n".join(report) + "\n")
    print(f"\n{total_flags} flags total; report written to {out_dir}/REPORT.md")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lib = None
    for a in sys.argv[1:]:
        if a.startswith("--libretto="):
            lib = a.split("=", 1)[1]
    if len(args) < 2:
        sys.exit(__doc__)
    convert_opera(args[0], args[1], lib)
