#!/usr/bin/env python3
# Gilbert & Sullivan Learn-O-Matic 4000
# Copyright (C) 2026 KingParamount and contributors
# SPDX-License-Identifier: MIT

"""The editorial layer: deciding who sings what.

Implements the agreed rules. Everything this module guesses is recorded as a
flag so it lands in the MusicXML as a visible red annotation — the standing
instruction is ALWAYS GUESS, NEVER LEAVE BLANK, because a wrong-but-pasteable
syllable is cheaper to fix than an empty stave is to fill.

  R1  speaker tags in the lyric line -> named staves, tags stripped
  R2  where the lyric stave and the singer stave disagree on notes, the
      SINGER stave wins (the lyric stave is a crib, not a source)
  R3  one stave per singer; no "Judge/Counsel" combos
  R4  one lyric line but several simultaneous texts -> consult the libretto
  R5  chorus principals who alternate solo and chorus singing
  R6  "Girls"/"Boys" split to SATB; divisi become FULL-LENGTH parts
"""
import re, unicodedata, bisect, collections

TOL_NUM = 16          # onset match tolerance = division/TOL_NUM

# Collective speaker labels -> the voice families they stand for.
COLLECTIVE = {
    "ALL": "*", "TUTTI": "*", "ENSEMBLE": "*", "BOTH": "*", "TRIO": "*",
    "QUARTET": "*", "QUINTET": "*", "SEXTET": "*", "DUET": "*",
    "CHORUS": "SATB", "FULL CHORUS": "SATB", "CHO": "SATB", "CH": "SATB",
    "CHOR": "SATB", "SEMI-CHORUS": "SATB", "SEMICHORUS": "SATB",
    "MEN": "TB", "BOYS": "TB", "MALE CHORUS": "TB", "GENTLEMEN": "TB",
    "WOMEN": "SA", "GIRLS": "SA", "LADIES": "SA", "FEMALE CHORUS": "SA",
    "MAIDENS": "SA", "SOPRANOS": "S", "ALTOS": "A", "CONTRALTOS": "A",
    "TENORS": "T", "BASSES": "B", "BARITONES": "B",
}
FAMILY = {"S": ["Soprano"], "A": ["Alto"], "T": ["Tenor"], "B": ["Bass"],
          "SA": ["Soprano", "Alto"], "TB": ["Tenor", "Bass"],
          "SATB": ["Soprano", "Alto", "Tenor", "Bass"]}

CHORUS_RE = re.compile(
    r'^(soprano|alto|contralto|tenor|bass|baritone)s?\s*(1|2|i|ii)?$', re.I)
SPLITTABLE = {
    "girls": ("Soprano", "Alto"), "women": ("Soprano", "Alto"),
    "ladies": ("Soprano", "Alto"), "female chorus": ("Soprano", "Alto"),
    "maidens": ("Soprano", "Alto"),
    "boys": ("Tenor", "Bass"), "men": ("Tenor", "Bass"),
    "male chorus": ("Tenor", "Bass"), "gentlemen": ("Tenor", "Bass"),
    # The Grand Duke transcriber used bare voice-pair abbreviations on a single
    # stave. TT/BB are a section divided against itself, not two sections.
    "sa": ("Soprano", "Alto"), "tb": ("Tenor", "Bass"),
    "ss": ("Soprano 1", "Soprano 2"), "aa": ("Alto 1", "Alto 2"),
    "tt": ("Tenor 1", "Tenor 2"), "bb": ("Bass 1", "Bass 2"),
}
PLURAL = {"Sopranos": "Soprano", "Altos": "Alto",
          "Tenors": "Tenor", "Basses": "Bass"}

# A syllable-initial speaker tag. Three forms occur in the archive:
#   "[JUDGE] Some words"   bracketed  (Trial, Pinafore, most operas)
#   "JUDGE: Some words"    colon
#   "RUDOLPH Come "        BARE ALL-CAPS, no punctuation at all — the whole of
#                          The Grand Duke, which is why it looked untagged.
# The bare form cannot be matched on shape alone without eating capitalised
# lyrics, so it is accepted only when the name is one we recognise.
TAG_RE = re.compile(r'^\s*(?:\[([^\]]{1,40})\]|([A-Z][A-Za-z\'&.\s]{0,28}?)\s*:)\s*')
BARE_RE = re.compile(r"^\s*([A-Z][A-Z'.\-]+(?:\s+[A-Z][A-Z'.\-]+){0,2})"
                     r"(?:\s+(?=[A-Za-z])|[.\s]*$)")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r'[^a-z0-9]', '', s.lower())


# ---------------------------------------------------------------------------
# R8 — find the phantom lyric-carrier stave WITHOUT trusting its name.
#
# It is usually called "Lyrics", but not always: in tbj04 it is "Staff-1", and
# the generic-named staves are commonest in exactly the operas that were
# transcribed most carelessly. Getting this wrong is catastrophic rather than
# untidy — the phantom sounds under every singer, so it captures the entire
# lyric stream and every real character is left silent.
#
# The giveaway is not the name but the SHAPE: a phantom shadows whoever is
# singing at the time, so it doubles staves that never sound together (the
# Judge in his verses, the chorus in theirs). A genuine stave that happens to
# carry the words — a chorus Soprano line, say — only ever doubles staves that
# sing WITH it.
# ---------------------------------------------------------------------------

def find_phantom(sc, tol):
    best = None
    for cand in sc.singers:
        if len(cand.lyrics) < 8:
            continue
        others = [t for t in sc.singers if t is not cand]
        if len(others) < 2:
            continue
        onsets = {t.name: sorted({x for x, _d, _p in t.notes}) for t in others}
        groups = collections.Counter()
        alone = 0
        for tick, _d, _p in cand.notes:
            who = frozenset(n for n, o in onsets.items() if _near(o, tick, tol))
            if not who:
                alone += 1
            else:
                groups[who] += 1
        total = len(cand.notes)
        if not total or alone / total > 0.10:
            continue                  # sings on its own too often to be a shadow
        # does it double mutually-exclusive groups of singers?
        sets = [s for s, n in groups.items() if n >= max(3, 0.05 * total)]
        disjoint = any(not (a & b) for i, a in enumerate(sets) for b in sets[i + 1:])
        if not disjoint:
            continue
        score = (len(cand.lyrics), -alone)
        if best is None or score > best[0]:
            best = (score, cand)
    return best[1] if best else None


def _near(sorted_onsets, tick, tol):
    j = bisect.bisect_left(sorted_onsets, tick)
    for k in (j - 1, j):
        if 0 <= k < len(sorted_onsets) and abs(sorted_onsets[k] - tick) <= tol:
            return True
    return False


# ---------------------------------------------------------------------------
# R1 — pull the lyric stave apart into speaker-attributed syllables
# ---------------------------------------------------------------------------

def segment_lyrics(lyric_track, is_known=None):
    """[(tick, raw_syllable)] -> [(tick, raw_syllable, speaker_or_None)],
       with the bracketed/colon speaker tag stripped off the syllable text.
       The speaker persists until the next tag (or a line break resets nothing
       — the archive tags only at changes of singer)."""
    out = []
    speaker = None
    for tick, raw in lyric_track.lyrics:
        if raw in ("\r", "\n", "\r\n"):
            out.append((tick, raw, speaker))
            continue
        m = TAG_RE.match(raw)
        if m:
            tag = (m.group(1) or m.group(2) or "").strip().rstrip(".").strip()
            if tag and not _looks_like_a_word(tag, raw):
                speaker = tag.upper()
                raw = raw[m.end():]
                if not raw.strip():
                    continue
        elif is_known is not None:
            b = BARE_RE.match(raw)
            if b:
                cand = b.group(1).strip().rstrip(".").strip()
                # only strip it if it names somebody; otherwise it is a lyric
                if len(cand) > 1 and is_known(cand):
                    speaker = cand.upper()
                    raw = raw[b.end():]
                    if not raw.strip():
                        continue
        out.append((tick, raw, speaker))
    return out


def _looks_like_a_word(tag, raw):
    """Guard against eating a real lyric. "Ah:" is a tag; "Oh, I love him" is
       not — but neither should a capitalised sung word be treated as a name."""
    if raw.lstrip().startswith("["):
        return False                       # bracketed form is unambiguous
    return len(tag) > 28


# ---------------------------------------------------------------------------
# Name resolution: a libretto/tag speaker -> the stave name(s) it refers to
# ---------------------------------------------------------------------------

class Resolver:
    def __init__(self, stave_names, aliases=None):
        self.staves = list(stave_names)
        self.by_norm = {norm(s): s for s in self.staves}
        self.aliases = {norm(k): v for k, v in (aliases or {}).items()}

    def resolve(self, speaker):
        """-> (list_of_stave_names, confident_bool)"""
        if not speaker:
            return [], False
        if re.search(r'[,&]|\band\b', speaker, re.I):
            # NB the split must be case-insensitive too: "PEERS AND FAIRIES"
            # matched the search but not a case-sensitive split, so the split
            # returned the string unchanged and this recursed until the stack
            # blew. Guard on making progress rather than trusting the patterns
            # to agree.
            bits = [b.strip() for b in
                    re.split(r'\s*(?:[,&]|\band\b)\s*', speaker, flags=re.I)
                    if b.strip()]
            if len(bits) > 1 or (bits and bits[0] != speaker.strip()):
                hits, conf = [], True
                for bit in bits:
                    h, c = self.resolve(bit)
                    hits += [x for x in h if x not in hits]
                    conf = conf and c
                if hits:
                    return hits, conf
        key = norm(speaker)
        if key in self.aliases:
            want = self.aliases[key]
            want = [want] if isinstance(want, str) else want
            return [w for w in want if w in self.staves], True
        up = speaker.upper().strip()
        if up in COLLECTIVE:
            fam = COLLECTIVE[up]
            if fam == "*":
                return list(self.staves), True
            want = FAMILY[fam]
            hit = [s for s in self.staves if s in want or PLURAL.get(s) in want]
            return hit, bool(hit)
        if key in self.by_norm:
            return [self.by_norm[key]], True
        # abbreviation: "KAT." -> Katisha, "SGT" -> Sergeant
        cands = [s for s in self.staves if norm(s).startswith(key) and len(key) >= 3]
        if len(cands) == 1:
            return cands, True
        # surname/forename fragment: "LADY S." -> "Lady Sangazure"
        parts = [p for p in re.split(r'[^A-Za-z]+', speaker) if len(p) > 2]
        if parts:
            cands = [s for s in self.staves
                     if all(norm(p) in norm(s) for p in parts)]
            if len(cands) == 1:
                return cands, True
        return [], False


# ---------------------------------------------------------------------------
# R6 — chorus staves: split combined and divisi staves into full-length parts
# ---------------------------------------------------------------------------

def split_chorus_stave(track, tol):
    """Return [(new_name, notes, note_on_guess_bool)] or None if no split is
       needed. Per R6 every returned part spans the WHOLE number — unison
       passages are duplicated into each, not left in one stave."""
    key = (track.name or "").strip().lower()
    target = SPLITTABLE.get(key)
    divisi = _max_simultaneity(track, tol)
    if target is None and divisi < 2:
        return None
    if target is None and not CHORUS_RE.match((track.name or "").strip()):
        return None          # a named body ("Jury"), not a chorus voice
    if target is None:
        # a plain "Bass" stave that divides -> Bass 1 / Bass 2
        base = PLURAL.get(track.name, track.name)
        if divisi > 3:
            return None                    # not a voice split; leave alone
        target = tuple(f"{base} {i + 1}" for i in range(divisi))
    n = max(len(target), divisi)
    if n > len(target):
        # e.g. "Girls" dividing three ways — Soprano/Alto is not enough voices,
        # and one short voice means every extra chord note is silently dropped.
        base = list(target)
        extra = 2
        while len(base) < n:
            base.append(f"{target[-1]} {extra}")
            extra += 1
        target = tuple(base)
    voices = [[] for _ in range(len(target))]
    guessed = _max_simultaneity(track, tol) > len(SPLITTABLE.get(key, ())) \
        if key in SPLITTABLE else False
    for onset, group in _chord_groups(track, tol):
        pitches = sorted((p for _t, _d, p in group), reverse=True)
        durs = {p: d for _t, d, p in group}
        for vi in range(len(target)):
            pitch = pitches[vi] if vi < len(pitches) else pitches[-1]
            voices[vi].append((onset, durs[pitch], pitch))
    return [(target[i], voices[i], guessed) for i in range(len(target))]


def _chord_groups(track, tol):
    groups = []
    for tick, dur, pitch in sorted(track.notes):
        if groups and tick - groups[-1][0] <= tol:
            groups[-1][1].append((tick, dur, pitch))
        else:
            groups.append((tick, [(tick, dur, pitch)]))
    return groups


def _max_simultaneity(track, tol):
    return max((len(g) for _t, g in _chord_groups(track, tol)), default=0)


# ---------------------------------------------------------------------------
# R3 — combined staves ("Boatswain/Ralph", "Sir J/Mrs. C")
# ---------------------------------------------------------------------------

COMBINED_RE = re.compile(r'\s*[/&+]\s*')


def combined_names(stave_name):
    if not stave_name or not COMBINED_RE.search(stave_name):
        return None
    bits = [b.strip() for b in COMBINED_RE.split(stave_name) if b.strip()]
    return bits if len(bits) > 1 else None
