# G&S Learn-O-Matic — auto-import review notes

All **13 Savoy operas** that the G&S Archive published as "web operas" are now in
the app. Trial by Jury and The Sorcerer were curated by hand with you; the other
**11 were auto-imported** by per-opera agents and validated (every track name
checked against the real MIDI files — no invented data). This file lists the
best-guesses and difficulties to review together.

## ✅ Resolved (fixes applied after review)
- **Engine fixes** (benefit every opera): a parser bug that let a malformed note
  (note-on with no note-off) ring forever until stop/start is fixed (it hit
  Princess Ida No. 8). Added two general, code-free override hooks in each song's
  `songs.json`: `partTracks` (assign a generically-named track like `Vocal` to the
  right part for *that* number) and `accompaniment` (treat an oddly-named track
  like `Staff-2` as piano for *that* number).
- **Iolanthe** — No. 16 piano restored (it was on non-breaking-space-named
  tracks); No. 14 → Private Willis only; No. 20 → Lord Chancellor only; duplicate
  No. 25 removed.
- **Patience** — No. 2: `Staff-1` mapped to **Lady Saphir + Altos** (both were
  missing).
- **Princess Ida** — No. 2 & No. 3 piano restored (`Treble Clef`/`Bass Clef`);
  No. 8 hanging note fixed; No. 10a: `Staff-1` = women (Sop + Alto), `Staff-2/3` =
  piano; No. 11 → **Lady Blanche**; No. 24: `Soprano I`→Soprano, `Soprano II`→Alto,
  Tenor/Bass correct, `Staff-3/4` = piano.
- **Ruddigore** — the reused `Vocal` track now resolves per song: No. 11 → **Mad
  Margaret**, No. 22 / 22a → **Robin / Sir Ruthven**. Plus No. 8 `Staff-1` →
  **Rose** (the Richard/Rose duet) and No. 19 `Staff-1` → **Robin / Sir Ruthven**
  (his interjections in the picture-gallery scene).
- **Yeomen of the Guard** — `Vocal` resolves per song: No. 1 Phoebe, No. 1a
  Wilfred, No. 10 Elsie, No. 11 Phoebe, No. 14 Jack Point, No. 16 & 19 Colonel
  Fairfax, No. 21 Dame Carruthers (+ `Staff-1` → Sergeant Meryll — *best-guess*
  for the "Rapture, rapture!" duet; worth a listen).
- **The Grand Duke** — No. 1b: `Staff-2` → **Alto**; No. 11: trivial `Staff-1`
  folded into the piano; No. 20: trimmed to the actual singers (**Julia &
  Ernest** + piano), spurious empty tracks ignored.
- **The Mikado** — No. 4 "Young man, despair": `Staff-2` → **Ko-Ko**, `Staff-3` →
  **Pish-Tush**, `Vocal` → **Pooh-Bah**; No. 14 "Braid the raven hair": `Vocal` →
  **Pitti-Sing** (and the two no longer leak into each other's number).
- **The Yeomen of the Guard** — added a **1st Yeoman** part (Finale Act 1 only).
  The Act 1 Finale (No. 12) uses *staging-position* tracks, not character tracks;
  mapped `Centre` → Meryll/Fairfax/Lieutenant/Point, `Left Centre` → Wilfred/Elsie,
  `Right Centre` → 1st Yeoman/2nd Yeoman/Phoebe, and `Alto` also → Dame Carruthers.
  Each is flagged "includes other voices" since the staging lines are shared.

## Cross-cutting things to know
- **Song order is reliable everywhere.** The printed **"No. X" labels are
  best-guess** for operas whose source files are named by *page* rather than
  musical number — The Mikado, The Gondoliers, Utopia, and parts of Ruddigore /
  Grand Duke. The numbers may not match your vocal score even though the order is
  right.
- **Titles** are mostly the *actual opening sung line* (speaker tag stripped),
  with famous titles used where the agent was confident. **"Type" labels** (e.g.
  "Song (Ko-Ko)") are best-guess.
- **A generic "Vocal" track** is reused for different soloists in some operas
  (Iolanthe, Ruddigore, Yeomen). Those solo numbers may show under more than one
  principal, or sit unmapped — they need a per-song assignment. Flagged per opera.
- **Some unnamed "Staff-N" lines** couldn't be mapped to specific voices, so a few
  numbers have incomplete part coverage (e.g. the Patience Act II finale chorus).
- **Minor characters with no separate MIDI track are omitted** as parts (e.g.
  Isabel in Pirates, Fleta in Iolanthe, Ruth in Ruddigore, Sacharissa/Chloe/Ada in
  Ida, several in Utopia & Grand Duke). They only sing within ensemble lines.
- **Pirates "Poor wand'ring one!"** (No. 8) was a single-track (MIDI format 0)
  file with no per-part isolation — now **replaced** with a format-1 file (Mabel
  / Sopranos / Altos isolate), with the karaoke words **grafted back in** from the
  original archive file (time-aligned to the Mabel line, rebroken on punctuation).
- **Iolanthe** includes a byte-identical duplicate of the Act II finale and a cut
  song ("Fold your flapping wings") — you may want those removed.
- Everything is reversible: each opera is just a folder + `songs.json`, and the
  generator (`scripts/build-songs.py`) only hand-curates Trial & Sorcerer; the
  rest live as data you can edit freely.

---


# H.M.S. Pinafore — curation flags

## Merged-variant principal decisions
- **Sir Joseph Porter**: merged `Sir Joseph` + combined tracks.
- **Captain Corcoran**: merged `Captain Corcoran`, `Captain`, `Captain C.`, and generic `Vocal` (pin04 — see below).
- **Ralph Rackstraw**: merged `Ralph` + `Boatswain/Ralph`.
- **Dick Deadeye**: merged `Deadeye`, `Dick Deadeye`, `Soprano/Deadeye`.
- **Boatswain (Bill Bobstay)**: merged `Boatswain`, `Bo'sun`, `Boatswain/Ralph`, `Bo's'n/Sir J.`.
- **Cousin Hebe**: merged `Cousin Hebe` + `Hebe`.
- **Little Buttercup**: merged `Buttercup`, `Altos/Buttercup`, `Sir J/Mrs. C` (Mrs. Cripps = Little Buttercup).

## Combined-track resolutions ("/")
- `Boatswain/Ralph` (pin03) → Boatswain + Ralph.
- `Bo's'n/Sir J.` (pin18) → Boatswain + Sir Joseph.
- `Soprano/Deadeye` (pin19) → Soprano section + Dick Deadeye.
- `Altos/Buttercup` (pin19) → Alto section + Little Buttercup.
- `Sir J/Mrs. C` (pin20) → Sir Joseph + Little Buttercup (Mrs. Cripps). **Assumed Mrs. C = Mrs. Cripps**; reasonably confident from the libretto.

## Generic Vocal / Soloist handling
- `Vocal` (pin04 only): carries the Captain's solo ("My gallant crew, good morning") — assigned to Captain Corcoran and kept in pin04 voiceTracks. Used only once, so no inconsistency, but FLAGGED as a generic name.
- `Soloist` (pin21): generic lump = Josephine, Hebe, Ralph & Dick ("Oh joy, oh rapture"). Listed in `soloistTracks` and added to candidates of those four principals; kept in pin21 voiceTracks.

## Excluded generic lyric / staff tracks (not parts, not in voiceTracks)
- `Lyrics` (the dedicated lyric track in most files) — excluded everywhere.
- `Staff-1` is the lyric carrier (highest lyric count) in pin04a, pin08, pin09, pin09a, pin10, pin14, pin17, and is a 0-note placeholder in pin20 — excluded as generic.
- `Staff-2` is the lyric carrier in pin20 — excluded. **pin03 `Staff-2` has 152 notes but 0 lyrics** (an un-labelled vocal/inner line); excluded as a generic Staff track. FLAGGED — may be a real chorus inner part.
- `Staff-1` in pin21 (2 notes) excluded as negligible/generic.

## Chorus mapping
- `Contraltos` → Alto. `Bass`/`Basses`/`Basses 1`/`Basses 2` → Bass. `Tenor`/`Tenors` → Tenor.
- No generic "Women"/"Sailors"/"Chorus" lump tracks exist (all chorus is explicit SATB or named combined tracks), so `choralTracks` is empty and no generous women→S+A / men→T+B duplication was needed.

## Numbering / titles
- Filenames `pinNN` map directly to musical numbers, confirmed by in-file title tracks ("Pinafore No. 4", "No. 9a", etc.). Used those numbers. `pin04a`→4a, `pin09a`→9a.
- **No. 7 is absent** (the barge chorus "Gaily tripping / Sir Joseph's barge"); pin06 jumps to pin08. Numbers left as-is (no renumbering needed). FLAGGED.
- Titles taken from `firstLines` with SPEAKER tags stripped; types are best-guess descriptors.
- pin20 type/personnel guessed (Trio & Chorus); only the combined `Sir J/Mrs. C` solo track is present besides SATB.

## Format
- All files are MIDI format 1. No format-0 files.

---

# Iolanthe — curation flags

## Blank / junk track handling
- **iolanthe_16.kar** has two piano tracks named with non-breaking spaces: `"    "` (4× NBSP, 1394 notes) and `" "` (1 NBSP, 850 notes). Per rule 2 these blank/whitespace names were ignored entirely (treated as accompaniment, not added anywhere).
- **iolanthe_06.kar** "Drum roll" (100 notes) ignored as junk.
- Title-only header tracks (0 notes, e.g. "Iolanthe No 1 - Opening Chorus...") ignored.
- Generic "Lyrics" tracks (words-only) excluded from voiceTracks everywhere.

## Trailing whitespace (exact-match)
- **iolanthe_21.kar** track is `"Lord Tolloller "` — trailing char is a NON-BREAKING SPACE (0xA0), not a regular space. Copied exactly into the song's voiceTracks and into the Earl Tolloller part candidates alongside the normal `"Lord Tolloller"`.

## Staff-1 / Staff-2 (dual role) — UNCERTAIN
- `Staff-1` is the **lyrics/melody guide** track in iolanthe_04, _15, _21 (carries the lyrics), but an **instrumental staff** (notes, 0 lyrics) in iolanthe_14. `Staff-2` is a tiny instrumental staff in _14 and _20.
- Decision: added both `Staff-1` and `Staff-2` to `accompaniment` so they are never treated as solo voices. They are excluded from all voiceTracks. Flagging because "Staff-1" doubles as a lyric track in some songs.

## Part merges
- Queen of the Fairies merged from `"Queen"` and `"Fairy Queen"`.
- Earl Tolloller merged from `"Lord Tolloller"` + `"Lord Tolloller "` (NBSP).
- Private Willis candidates = `"Sentry"` (+ `"Vocal"`, see below).
- Alto candidates merge `"Altos"` + `"Contraltos"`. Tenor merges `"Tenors"/"Tenors I"/"Tenors II"`. Bass merges `"Basses"/"Basses I"/"Basses II"`. Only plural `"Sopranos"` occurs (no singular forms in this opera).

## Generic chorus tracks (generous SATB mapping)
- `choralTracks` = ["Fairies","Ladies' Chorus","Men's Chorus","Chorus"].
- Generous part candidates: `Fairies` & `Ladies' Chorus` → Soprano + Alto; `Men's Chorus` → Tenor + Bass; `Chorus` (iolanthe_18) → all four SATB. These names also appear in the relevant songs' voiceTracks as-is.

## Combined tracks (iolanthe_13.kar)
- `"Phyllis / Leila"` → added to BOTH Phyllis and Leila candidates.
- `"Iolanthe / Celia"` → added to BOTH Iolanthe and Celia candidates.
- Kept as literal combined strings in song 13's voiceTracks.

## "Vocal" handling — COLLISION, needs review
- `"Vocal"` is a generic soloist track used for two DIFFERENT principals:
  - iolanthe_14 (firstLine "WILLIS: When all night long...") → **Private Willis**.
  - iolanthe_20 (firstLine "Love, unrequited..." Nightmare Song) → **Lord Chancellor**.
- Resolved per song via firstLines, but since the same string "Vocal" maps to two parts, it was added to BOTH Private Willis and Lord Chancellor candidates. The app cannot disambiguate "Vocal" by name alone — per-song mapping (file → part) is required. soloistTracks left empty.

## Fleta — omitted
- Fleta is a named principal but has NO track in any file; omitted from parts (validation requires real candidates). Flagging in case a Fleta line is expected.

## Guessed numbers / titles
- **flapping_wings.kar**: no number in filename → number set to "?" (FLAG). Identified as Strephon's cut Act II song "Fold your flapping wings" (recit. firstLine "My bill has now been read a second time"). Marked as cut/alternate.
- **iolanthe.kar**: byte-identical duplicate of iolanthe_25.kar (internal title "Iolanthe No. 25 Act II Finale"); assigned number "25", marked alternate/duplicate.
- Combined-number files: iolanthe_08-11 → number "8-11"; iolanthe_23-24 → "23-24"; iolanthe_04a → "4a". All taken from filenames (not inferred).
- Titles derived from firstLines (speaker tags stripped); types kept short. Numbers came from filenames (no inferred numbers except flapping_wings).

---

# Patience — curation flags

## Combined-track resolutions (rule 5)
- `Jane/Angela` (pat09) → added to candidates of **Jane** and **Angela**.
- `Maj/Bun/Gros` (pat09) → added to candidates of **Major**, **Bunthorne**, **Grosvenor**.

## Generic "Vocal" handling (rule 6)
- `Vocal` (pat14, "Love is a plaintive song") → this is **Patience**'s Act II solo. Added `Vocal` to Patience candidates and listed in `soloistTracks`. voiceTracks kept as `["Vocal"]`.

## Chorus / merges
- `Contraltos` and `Altos` both → **Alto** part.
- Generic `Chorus` (pat01, pat02a) → choralTracks; mapped generously to all four SATB parts.
- Generic `Maidens` (pat13) → choralTracks; mapped to Soprano + Alto.
- Generic `Dragoons` (pat04) → choralTracks; mapped to Tenor + Bass.
- Only plural names appear (`Sopranos`, `Tenors`, `Basses`) — no singular variants present.

## Numbering / order
- Numbers taken directly from filenames (pat01..pat20). Performance order = filename order; alternates (`pat02a`, `pat08a`) placed immediately after their parent and numbered `2a` / `8a`.
- **Discrepancy:** embedded MIDI title tracks for Act II conflict with filenames:
  - pat10 & pat12 both labelled "Patience No.2-01"; pat11 "Patience 2-02" (Act II internal numbering 1,2…).
  - pat19 labelled "Patience No. 18" (dup of pat18); pat20 labelled "Patience No. 17" (dup of pat17).
  - Used filename-derived numbers; did NOT infer from page numbers. True libretto musical numbers for Act II may differ — flagged.

## Excluded tracks (junk / lyric / generic staves)
- Lyric tracks excluded from voiceTracks: `Lyrics`, `Lyric`, and `Staff-1` where it carries the words (pat01 lyrics294, pat02a, pat16 lyrics241).
- `Conductor` (pat03–pat08, mostly 0–2 notes) treated as junk.
- Title marker tracks "Patience No. X" (0 notes) excluded.
- **Staff-N tracks with vocal notes but no lyrics — uncertain, EXCLUDED from voiceTracks:**
  - pat02 `Staff-1` (132 notes, 0 lyrics) — unmapped extra vocal staff.
  - pat20 `Staff-1`..`Staff-4` (~120 notes each) — almost certainly the SATB chorus of the Act II finale, but unnamed/unmappable to specific parts. Flagged; finale chorus is therefore NOT represented in voiceTracks for pat20.

## Titles / types
- Titles taken from opening lyric line (speaker tag stripped). pat02 titled from its recit line ("Still brooding…"); the aria proper is "I cannot tell what this love may be."
- Types are short editorial descriptors inferred from firstLines/voice tracks.

---

# Princess Ida — Curation Flags

## Typo / variant merges
- **Psyche / Pysche / Lady Psyche** merged into `lady-psyche`. The typo "Pysche" only ever appears inside the combined track string `"Melissa, Pysche"` (pi_20) — there is no standalone "Pysche" track, so that exact combined string is listed in candidates rather than a bare "Pysche".
- **Princess Ida**: "Ida" (pi_010, pi_022, pi_20) and "Princess Ida" (pi_014, pi_026) merged.
- **King Gama**: "King Gama" (pi_006) and "Gama" (pi_007, pi_023) merged.
- **Lady Blanche**: "Blanche" (pi_017) and "Lady Blanche" (pi_018) merged.
- Chorus variants merged: Sopranos/Soprano/Soprano I/Soprano II → Soprano; Altos/Alto/Contraltos/Contralto → Alto; Tenors/Tenor → Tenor; Basses/Bass → Bass.

## Duplicate "Melissa"
- "Melissa" appears as a separate solo track in pi_016, pi_017 AND pi_021 (plus the combined pi_20 track). All treated as the same person `melissa`. No conflict — confirmed single character.

## Combined tracks ("/" or "&")
- `"Melissa, Pysche"` (pi_20, Act II finale) added to candidates of BOTH `melissa` and `lady-psyche`. Kept as the literal voiceTrack string in pi_20.

## Treble Clef / Bass Clef junk
- pi_002 and pi_003 contain "Treble Clef" / "Bass Clef" tracks (high note counts). Per rules these are NOT voices — they are piano staves. Ignored entirely (not added to accompaniment, parts, or voiceTracks).

## Generic "Girls" / "Ladies" / "Women" / "Men"
- Listed in `choralTracks`. Generously mapped: Girls/Ladies/Women → candidates of BOTH Soprano and Alto; Men → BOTH Tenor and Bass. They also remain as literal voiceTracks in their songs (pi_006 Ladies/Men, pi_023 Ladies, pi_025 Girls/Men, pi_20 Women/Men).

## Solos / Vocal handling
- "Solos" (pi_008, Act II opening, only 56 notes) is a generic lump track → listed in `soloistTracks` and kept as a voiceTrack of pi_008. Likely carries Psyche's brief solo line plus others. No generic "Vocal" tracks exist in this opera.

## Generic "Staff" tracks (ambiguous — review)
- **pi_010a** ("And thus to empyrean height", alternate Act II chorus): has NO Right Hand/Left Hand tracks; tracks are "Staff" (carries lyrics → treated as lyric track, excluded) and "Staff-1/Staff-2/Staff-3". The three numbered staffs were taken as the choral voiceTracks but CANNOT be mapped to specific SATB parts (generic names). FLAG for manual voice assignment.
- **pi_011** ("Come mighty Must", Lady Blanche solo): the only vocal track is generically named "Staff-1" (carries the lyrics). Listed as the song's voiceTrack but NOT added to Lady Blanche's candidates (generic name). FLAG.
- **pi_024** ("When anger spreads his wing"): lyric/melody track is oddly named **"Tempo"** (notes 396, lyrics 204) — excluded as the lyric track. "Staff-3" (570) and "Staff-4" (776) are high-note piano staves → treated as accompaniment (not voiceTracks). Vocal parts: Soprano I, Soprano II, Tenor, Bass.
- "Staff-2" (pi_008) and "Staff-1" (pi_016, pi_025) are the lyric/karaoke tracks (carry lyrics) → excluded from voiceTracks.

## Guessed / inferred numbers & titles
- All song numbers taken directly from filenames (pi_001…pi_026, pi_13, pi_20). Note inconsistent zero-padding: pi_13 = No. 13 (sits between pi_012 and pi_014), pi_20 = No. 20 (between pi_019 and pi_021). No. 5 is absent from the source files.
- **pi_023** firstLines was EMPTY in the analysis. Title "Whene'er I spoke" was taken from the track/file name (verified in the .kar header: Gama's Act III song). FLAG title source.
- pi_010a marked as an alternate version (No. "10a").
- pi_001, pi_002 etc. titles taken from opening sung line (SPEAKER tag stripped); types are short editorial labels.

## Characters with no dedicated tracks (omitted from parts)
- **Sacharissa, Chloe, Ada** are listed principals but appear in NO track name anywhere in the .kar set (they only sing within choral/ensemble lines). Omitted from `parts` because there are no real candidate strings to attach. FLAG if standalone part entries are required.

---

# Ruddigore — Curation Flags

## Character merges (per instructions)
- **Robin Oakapple = Sir Ruthven Murgatroyd** — same character. Single part `robin-oakapple` labelled "Robin Oakapple / Sir Ruthven", candidates ["Robin","Sir Ruthven"]. Both strings appear as real tracks (Robin in Act I, Sir Ruthven after he assumes the title in Act II, e.g. rudd18, rudd21).
- **Sir Despard Murgatroyd** — candidates ["Sir Despard","Despard"]. "Sir Despard" in most files; bare "Despard" only in rudd24.
- **Dame Hannah** — candidates ["Hannah","Dame Hannah"]. "Hannah" in rudd02, "Dame Hannah" in rudd15/rudd25.

## Accompaniment naming variants
This opera uses many piano-track spellings, all included in `accompaniment`:
- "Right Hand"/"Left Hand" (most files), "R.Hand"/"L.Hand" (rudd14), "Piano R. H."/"Piano L.H." (rudd12-13), "Piano RH"/"Piano LH" (rudd24), plus "Tempo".

## Combined tracks
- **"Rose / Zorah"** (rudd15 Finale Act I) — added to candidates of BOTH `rose-maybud` and `zorah`.

## "Vocal" handling (soloistTracks, ambiguous — NOT assigned to a part)
"Vocal" is a generic soloist track mapping to a DIFFERENT character per song, so it is left in `soloistTracks` only (not added to any part's candidates, unlike The Sorcerer where Vocal was always Alexis). Per-song resolution:
- rudd11 "Cheerily carols the lark" — Vocal = **Mad Margaret** (her Act I entrance song).
- rudd22 / rudd22a "Away, Remorse!" — Vocal = **Robin / Sir Ruthven**.

## "Staff-1" junk track
"Staff-1" appears with note content in some files but is a generic/unlabelled staff, not a real character:
- rudd02: Staff-1 (576 notes, 312 lyrics) is the melody+lyric carrier — treated as the lyric track, excluded.
- rudd08: Staff-1 (206 notes, 0 lyrics) is an unlabelled second voice — almost certainly **Rose** (No.8 "The battle's roar is over" is a Richard & Rose duet). EXCLUDED from voiceTracks as junk; only "Richard" is mapped. Rose's line is effectively unlabelled here — review if Rose isolation is wanted.
- rudd19: Staff-1 (56 notes) — trivial, excluded.

## Number / title inference
- **rudd25**: filename implies No.25 but embedded title is "No26 - There grew a little flower". Used number **"26"** (matches Dame Hannah's ballad in standard scores). Filename/number mismatch flagged.
- **rudd22 & rudd22a**: BOTH carry embedded title "Ruddigore No. 23" but the lyric is "Away, Remorse!" which is **No.22** in standard scores (No.23 is the separate "I once was a very abandoned person", = rudd23). Assigned number "22" to both and treated rudd22a as an **alternate version**. The embedded "No. 23" appears to be a labelling error in the source MIDI.
- **rudd27**: embedded title "No27b - Original Finale Act II" — this is the **original (cut) finale**, marked type "Finale Act II (original version)". No revised-finale file is present in the set.
- "5 & 6" (rudd056) and "12 & 13" (rudd12-13) are combined-number files per filename; numbers taken directly, no inference needed.

## Parts with no track (omitted)
- **Ruth** — listed as a principal in the brief but NO track named "Ruth" exists in any file. Part omitted (rule: parts must have real candidates). Add later if a Ruth track surfaces.

## Bridesmaids (generous mapping)
- "Bridesmaids" = professional bridesmaids (women's chorus). Added to BOTH `soprano` and `alto` candidates, and listed as a generic `choralTracks` entry. Real track only in rudd02; elsewhere the women split into Sopranos/Contraltos.

---

# The Gondoliers — curation flags

## Musical numbers (inferred / confirmed)
- Filenames are bare page-style numbers (`101`, `212a`, etc.), so performance order and the
  sequential musical numbers were inferred from filename order. Most were CONFIRMED by the
  numbers embedded in each file's title track (e.g. `Gondoliers No. 2`, `No17 - In a
  contemplative fashion`, `gond 10`). `101` = No. 1 ("List and learn"), the Act I opening chorus.
- `212a.kar` title track says "Gondoliers No. 22a"; `212b.kar` title track says
  "Gondoliers No. 12b" — the "12b" is a typo for **22b** (it is the second half of the Act II
  finale, following 22a). Numbered 22a / 22b accordingly.
- `000.kar` is the Overture (no vocal tracks); given number "0" with empty voiceTracks.

## Spelling / character flags
- **"Guilia" → "Giulia"**: the track named `Guilia` (in 101) is a transposition typo for the
  contadina **Giulia**. Mapped as part id `giulia`, label "Giulia", candidate `Guilia`.
  (Not Gianetta — Gianetta has her own correct track in the same file.)
- **Francesco** added as a principal part though NOT in the supplied part list — he has a real
  solo track `Francesco` (328 notes) in 101. Fiametta and Inez have NO tracks anywhere, so no
  parts were created for them.

## Divisi / chorus mapping
- Soprano part absorbs: Sops, Sopranos, Soprano, Sopranos 1, Sopranos 2, Soprano 1, Soprano 2.
- Alto: Altos, Alto. Tenor: Tenors, Tenor, Tenors 1, Tenors 2. Bass: Basses, Bass, Basses 1, Basses 2.
- No literal combined ("/" or "&") vocal tracks exist in this opera; each singer has a discrete track.
- No generic "Chorus" tracks exist, so `choralTracks` is empty (all chorus lines are explicit SATB
  tracks mapped to parts, mirroring the-sorcerer). The "generous contadine→S+A / gondoliers→T+B"
  rule was not needed since every song carries explicit per-voice SATB tracks.

## Vocal / soloist handling
- No generic `Vocal` or `Soloists` lump tracks exist → `soloistTracks` is empty. No Vocal
  reassignment needed.

## "Staff" tracks (treated as accompaniment)
- Tracks named `Staff`, `Staff-1`, `Staff-3` are ambiguous. They behave as piano/extra staves
  (e.g. 203 "Take a pair of sparkling eyes" = Marco solo + Staff/Staff-3 = two piano staves; 204
  has Staff + Staff-1 alongside SATB). NOTE: in 101 `Staff-1` actually carries the karaoke
  melody+lyrics (4538 notes / 2435 lyrics). All Staff* tracks were placed in `accompaniment` and
  excluded from voiceTracks. Revisit if a Staff track is wanted as a singable line.
- `Drum` (102) ignored as junk per rules; `Lyrics` lyric-only tracks excluded from voiceTracks.

## Guessed / first-line titles
- Most titles taken from the opening sung line (SPEAKER tag stripped). Known canonical titles used
  for: "I stole the Prince" (6), "Take a pair of sparkling eyes" (13), "Dance a cachucha" (15),
  "In a contemplative fashion" (17), "I am a courtier grave and serious"/Gavotte (21).
- 107-8 (Nos. 7 & 8): titled from the recit first line "But, bless my heart, consider my
  position!" — GUESSED grouping/type (Recit. & Quintet); verify against vocal score.
- Song `type` fields (e.g. "Quartet", "Finale Act I") are best-effort and should be sanity-checked.

---

# The Grand Duke — curation flags

## Name merges
- **Rudolf / Rudolph** merged into ONE part `rudolph` (Rudolph, Grand Duke). "Rudolf" appears in gd09; "Rudolph" in gd10/gd12/gd28. Both listed as candidates.
- **Dr Tannhäuser** mapped from track name "Notary" (gd06, gd07, gd12, gd28). Label uses the role name; only "Notary" exists as a track.
- **Herald** = Viscount Mentschikoff (gd22 only).

## Chorus abbreviation mapping (per rules)
- **SA** (gd18, gd20, gd22) → added to BOTH Soprano and Alto candidates; kept in `choralTracks`.
- **TB** (gd18, gd20, gd22) → added to BOTH Tenor and Bass candidates; kept in `choralTracks`.
- **TT** (gd25) → Tenor; **BB** (gd25) → Bass.
- **Women** (gd14, gd27) → BOTH Soprano and Alto; **Men** (gd14, gd27) → BOTH Tenor and Bass. Kept in `choralTracks`.
- gd29 uses singular "Soprano/Alto/Tenor/Bass" (vs. plural elsewhere) → all added to chorus candidates.

## Combined tracks (added to each person's candidates)
- **"Ernest/Ludwig"** (gd05) → candidates of both Ernest and Ludwig.
- **"Baroness/Julia"** (gd18) → candidates of both Baroness and Julia.

## "Vocal" handling
- gd11 has a generic **"Vocal"** track (no per-part split). firstLines = "RUDOLPH When you find you're a broken-down critter…" → assigned "Vocal" to **Rudolph** candidates. CONFIRM Rudolph is the sole singer.

## Ambiguous "Staff" tracks (REVIEW)
- "Staff-1"/"Staff-2" with high lyric counts are the karaoke **lyric** track and were EXCLUDED as generic-lyric: gd09 (Staff-1), gd11 (Staff-2), gd14 (Staff-1), gd17 (Staff-2).
- "Staff" tracks with 0 lyrics are unidentified vocal lines and were KEPT in voiceTracks without a part mapping:
  - gd01b **Staff-2** (186 notes) — likely the Altos line (no "Altos" track present in this file). Verify.
  - gd20 **Staff-1** and **Staff-2** (~287 notes each, alongside SA/TB) — likely chorus doublings. Verify; they map to no part.
- gd11 "Staff-1" had only 2 notes → treated as junk, excluded.

## Numbers / titles
- All `number` values taken from filenames (not guessed), EXCEPT:
- **gd22**: file titled "Grand Duke 22 to 24" → number set to **"22-24"** (covers Nos. 22–24). Confirm scope/splitting.
- Titles derived from firstLines opening line (SPEAKER tag stripped). gd15 opening line is recitative ("Yes, Ludwig and his Julia are mated!") used as title.

## Parts with NO tracks (omitted from parts list)
- Olga, Gretchen, Bertha, Elsa, Martha, and Dr Tannhäuser-as-"Tannhäuser" have no dedicated tracks in any .kar file → not included as parts. Their lines are inside the generic "Lyrics" tracks only.

## Accompaniment
- Non-vocal tracks collected: Right Hand, Left Hand, Piano right, Piano left, Piano 1, Piano 2, piano, piano-2, piano-3, Tempo, Tempo Track. Tempo tracks with 2 notes (gd05/06/07/09/10) treated as junk and excluded.
- "Grand Duke No. X" header tracks (0 notes) ignored as junk.

---

# The Mikado — curation flags

## Numbers inferred from filename order
- Musical `number` values (1–26) were assigned **sequentially from filename order**, NOT from the published score. Filenames encode act+number (e.g. `101` = Act 1 No. 1, `213` = Act 2 finale), so performance order is reliable, but the sequential 1–26 numbering collapses the act-internal numbering and the `a` suffixes. The internal track title strings carry the real published numbers (e.g. "No. 20 - Duet", "No. 22 - Song") and these often disagree with my sequential numbering — Act 2 track titles are internally renumbered (Act 2 No. 1–12) while published numbering continues No. 12 onward. Treat `number` as a display ordinal only.
- `104a` and `105a` are short additional/encore numbers (recit before Pooh-Bah duet; Ko-Ko's "little list"), not alternate versions. Kept as separate songs with their own sequential numbers (5 and 7).

## "Vocal" generic-soloist handling (rule 6)
- `104.kar` ("Young man, despair"): track **"Vocal"** (508 notes, 0 lyrics) is the generic melody line. firstLine attributed to POOH, so "Vocal" assigned to **Pooh-Bah** candidates. The song is actually a trio (Pooh-Bah/Pish-Tush/Ko-Ko); the other two voices appear only as ambiguous "Staff-2"/"Staff-3" (see below). UNCERTAIN.
- `201.kar` ("Braid the raven hair"): track **"Vocal"** (324 notes, 3 lyrics) assigned to **Pitti-Sing** (she sings the solo within this chorus). UNCERTAIN — could be a generic chorus-soprano lead.
- "Vocal" listed once in `soloistTracks` (it is a generic lump track).

## Ambiguous "Staff-N" tracks
- `104.kar`: "Staff-2" (156) and "Staff-3" (156) have notes but no lyrics and no named owner. Included as voiceTracks (likely the Pish-Tush/Ko-Ko lines of the trio) but they map to NO part candidate. Flag.
- `201.kar`: "Staff-1" (150) and "Staff-4" (360) similarly unnamed vocal staves; included as voiceTracks, no part mapping. ("Staff-2" 510/243 was the lyric track and excluded.)
- Note: in `101.kar`/`213.kar` the highest-lyric "Staff-2"/"Staff-1" tracks were treated as the words-only lyric track and EXCLUDED from voiceTracks.

## Generic chorus combined tracks (rule 4, GENEROUS)
- `205.kar` has generic **"Women"** and **"Men"** tracks. Per rules: "Women" added to BOTH Soprano and Alto candidates; "Men" added to BOTH Tenor and Bass candidates. Both also listed in `choralTracks`. They remain in that song's voiceTracks verbatim.

## Guessed / normalized titles
- Titles taken from firstLines opening line with SPEAKER tags stripped, or famous title where clearer:
  - `101` "If you want to know who we are" (opening men's chorus)
  - `105a` "As some day it may happen (I've got a little list)"
  - `107` "Three little maids from school"
  - `205` "Miya sama (Entrance of the Mikado)" — firstLine was the Japanese chorus text; title contextualized.
  - `206` "A more humane Mikado"
  - `211` "On a tree by a river (Tit-Willow)"
- `203.kar` had a `null` title track name (junk, ignored).

## No combined principal ("/" or "&") tracks present
- Unlike The Sorcerer, no combined principal voice tracks (e.g. "X & Y") exist in this data; only the generic "Women"/"Men" chorus combos handled above.

## Lyric tracks excluded (words-only)
- "Lyrics" excluded everywhere; in `101`/`201`/`213` the high-lyric "Staff-2"/"Staff-1" served as the lyric track and were excluded.

---

# Flags — The Pirates of Penzance

## FORMAT-0 file (per-part separation impossible)
- **pp08.kar** ("Poor wand'ring one!", No. 8) is **MIDI format 0**: a single merged track named
  "Pirates No. 8" (4108 notes, 194 lyrics) containing Mabel's solo + the female chorus all together.
  No separate voice tracks exist, so **voiceTracks = []**. This song cannot be split per-part for
  rehearsal. Per rule 4, "Pirates No. 8" is also listed as a candidate for both Tenor and Bass (men's
  chorus mapping), though in practice the merged track is dominated by Mabel/female lines.

## Merges (principals with name variants)
- **Frederic**: candidates "Frederic" (pp18_19, pp21_2, pp27) + "Fred" (pp06_7, pp11, pp14, pp20).
- **Major-General Stanley**: "Major-General" (pp27) + "Major General" (pp12, pp13, pp14, pp16_17).
- **Samuel**: "Samuel" (pp01, pp12, pp27) + "Sam" (pp14).
- **The Pirate King**: track is "King" everywhere.
- **Sergeant of Police**: track is "Sergeant".

## Combined tracks (added to each person's candidates)
- **"Edith & Kate"** (pp27) added to both Edith and Kate candidates. Their voiceTracks in pp27 are
  represented by this single combined track.

## Missing principal
- **Isabel**: NO track appears in any file (she has no solo music in these MIDIs). Part omitted because
  validation requires >=1 real candidate. Flag for awareness if Isabel coverage is expected.

## Ambiguous / generic tracks
- **"Staff-10"** in pp27 (348 notes, no lyrics, pitch range 39-62 = bass register). pp27 has Sopranos,
  Altos, Tenors but no named Bass track; pitch analysis confirms Staff-10 is the **Bass chorus** line.
  Included in pp27 voiceTracks and added to the Bass part candidates. Identity inferred (not labelled).
- **Lyric tracks** (words only — excluded from parts/voiceTracks): "Lyrics", "Lyrics." (pp14),
  "Staff-1" (the lyric track in pp01 and pp12).
- **Empty label/conductor tracks** ignored: "Pirates No. 1"…"Pirates No. 8", "Pirates Nos 16 & 17",
  etc. (0-note marker tracks; pp08's is the exception — it is the actual format-0 music track).

## Chorus mapping (generous, per rule 4)
- "Chorus Soprano"/"Sopranos" -> Soprano; "Chorus Alto"/"Altos" -> Alto.
- "Chorus Tenor"/"Tenor"/"Tenors"/"Pirates Tenor"/"Pirates Tenor 1"/"Pirates Tenor 2" -> Tenor.
- "Chorus Bass"/"Bass"/"Basses"/"Police Baritone"/"Police Bass"/"Pirates Bass 1 and 2" -> Bass.
- Mixed/men's lumps to BOTH halves: "Girls"/"Chorus of Girls" -> Soprano + Alto;
  "Pirates" -> Tenor + Bass; "Pirates No. 8" -> Tenor + Bass.
- Generic chorus lumps listed in choralTracks: "Girls", "Chorus of Girls", "Pirates".

## Numbers / order
- Filenames (pp01, pp02, …, pp27) are **G&S musical numbers, NOT page numbers** — confirmed by the
  internal marker-track names (e.g. "Pirates Nos 16 & 17", "Pirates Nos. 25 & 26", "Pirates Nos 27 & 28").
  Multi-number files mapped accordingly: pp06_7 -> "6 & 7", pp16_17 -> "16 & 17", pp18_19 -> "18 & 19",
  pp21_2 -> "21 & 22", pp25 -> "25 & 26", pp27 -> "27 & 28". Order is by number; no inference needed.
- Gaps in numbering (4, 9, 10, 26 missing as standalone files) correspond to dialogue/spoken numbers or
  numbers folded into adjacent files — expected, not an error.

## Titles
- Taken from real opening sung words (firstLines), leading SPEAKER tag stripped, e.g.
  "FRED: Stop, ladies, pray!" -> "Stop, ladies, pray!". pp02 normalised "Fred'ric" -> "Frederic" and
  pp16_17 "lion hearted" -> "lion-hearted" for readability.

## Vocal / soloist handling
- No generic "Vocal" or "Soloists" lump track exists in this opera; soloistTracks = [].

---

# Flags — The Yeomen of the Guard

## Staging junk (Centre / Left Centre / Right Centre)
- `yg112.kar` (Finale Act I) contains "Left Centre" (624 notes), "Centre" (1134), "Right Centre" (514). Per rules these are staging positions, NOT voices — excluded from voiceTracks/parts/accompaniment. The real chorus voices "Soprano/Alto/Tenor/Bass" were kept instead.
- No "Conductor"/"Drum" tracks present. Blank/header title tracks (notes 0) all dropped.

## Lyric tracks (words-only, excluded)
Generic lyric/display tracks carrying the libretto were excluded from voiceTracks:
"Lyrics" (yg103,104,106,108,112,213,215,217,219,220,222), "Staff-1" (yg218),
"Staff-2" (yg107,221). These carry lyrics meta but are not singer-specific.

## Part merges (chorus)
- Soprano <= Soprano, Sopranos, Sop 1, Sop 2
- Alto <= Alto, Contraltos
- Tenor <= Tenor, Tenors, Tenor 1, Tenor 2, Ten
- Bass <= Bass, Basses, Bass 1, Bass 2
- yeomen_02 has BOTH plain SATB and divisi (Tenor 1/2, Bass 1/2) — all included as real voices.
- Principal merges: Fairfax/Colonel Fairfax; Meryll/Sergeant Meryll; Shadbolt/Wilfred.

## Combined ("/" or "&") tracks
- None found in this opera. Rule 5 not triggered.

## Generic "Vocal" handling (in soloistTracks; per-song soloist below)
"Vocal" is reused for SIX different soloists across the opera, so it was NOT added to
any single principal's candidates (that would mis-map it). It lives in soloistTracks.
Per-song intended soloist (judged from firstLines / known repertoire):
- yeomen_01 "When maiden loves" -> PHOEBE
- yeomen_01a "When jealous torments" -> WILFRED (alternate number)
- yg110 "'Tis done! I am a bride!" -> ELSIE
- yg111 "Were I thy bride" -> PHOEBE
- yg214 "Oh! a private buffoon" -> POINT
- yg216 "Free from his fetters grim" -> FAIRFAX (only one Vocal track though this is
  scored as a quartet — other voices not separated in this file)
- yg219 "A man who would woo a fair maid" -> FAIRFAX (3rd voice; Elsie & Phoebe are
  named tracks, "Vocal" = Fairfax per firstLines)

## "Staff" generic track
- yg103a "A laughing boy but yesterday" (alternate Meryll ballad): the vocal melody is
  carried by track "Staff" (380 notes + lyrics); "Staff-1"/"Staff-2" (1236/872 notes,
  no lyrics) are piano RH/LH. "Staff" appears ONLY in this song, so it was mapped to
  Sergeant Meryll (added to candidates). Low confidence on the Staff vs Staff-1/2 split.

## yg221 "Rapture, rapture!" duet — UNRESOLVED generic tracks
- Duet of Dame Carruthers & Sergeant Meryll. The two singing tracks are generic:
  "Vocal" (468 notes) and "Staff-1" (420 notes). Could not reliably tell which is which.
  Both kept in voiceTracks; neither mapped to a principal's candidates. Needs manual
  assignment (Dame Carruthers / Sergeant Meryll).

## yeomen_01a extra track
- "Staff-1" (150 notes, no lyrics) alongside Wilfred's "Vocal" in this solo — likely a
  counter-melody/echo with no named singer; excluded from voiceTracks.

## Guessed / derived titles
Most titles taken from firstLines opening line (SPEAKER tag stripped) or known titles
("Is life a boon?", "I have a song to sing, O!", "Were I thy bride"). Numbers derived
from filenames: yeomen_01->1, _01a->1a, _02->2, yg103->3, yg103a->3a, ... yg222->22
(Act II numbers 13-22). 1a and 3a marked as alternates.

---

# Flags — Utopia, Limited (`utopia-limited`)

## Part / track merges
- **Fitzbattleaxe typo + variant merge**: `Capt. Fitzbattleaxe` (007, 008, 014), `Fitzbattleaxe` (012, 013), and the misspelling `Firzbattleaxe` (009) were all merged into the single part **Captain Fitzbattleaxe**. The typo "Firzbattleaxe" appears only in 009.
- **King Paramount**: `Paramount` (004a) and `King` (011, 014, 017, 018, 023, 026) merged. The generic `Vocal` track in 005 (the King's number "First you're born") was also assigned to King — see Vocal note below.
- **Mr Goldbury**: `Goldbury` (021) and `Mr. Goldbury` (014, 022) merged.

## Chorus assumptions
- **"Flowers" = men's chorus** (011 finale): the Flowers of Progress are male characters, so the `Flowers` track was resolved to **Tenor + Bass** (not soprano/alto). Assumption flagged per instructions. `Flowers` also kept in `choralTracks`.
- **"Troopers"** (007, 008) treated as men's chorus → Tenor + Bass; also in `choralTracks`.
- **"Women"** standalone (004) treated as women's chorus → Soprano + Alto; also in `choralTracks`.

## Combined "/" tracks (002)
- **`Women/Scaphio`** → added to candidates of **Soprano**, **Alto** (Women = women's chorus) and **Scaphio**.
- **`Men/Phantis`** → added to candidates of **Tenor**, **Bass** (Men = men's chorus) and **Phantis**.

## Generic "Vocal" handling
- 005 has a generic `Vocal` track (notes 874 / lyrics 511). firstLines show the King ("First you're born…"), so `Vocal` was assigned to **King Paramount** and listed as a voiceTrack for 005. Flagged as an inference.

## Musical numbers inferred from filenames
- Filenames are bare page/index numbers (e.g. `004a`, `011`, `023`). Numbers were inferred from filename order: 1, 2, 3, 4, 4a, 4b, 4c, 5, 6, 7, 8, 9, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22, "23 & 24", 25, 26.
- Embedded MIDI header track names are unreliable: many read "Act 1 No 1" regardless of actual number (e.g. 003, 004, 018, 019), and 017 had a `null` header. 023 header says "Nos. 23 & 24" → used "23 & 24". Gaps in filenames (no 010, 015, 016, 024) left as gaps.

## Anonymous "Staff" tracks
- `Staff-2` (002) and `Staff-1` (014) carry the lyrics and were treated as the lyric track (excluded from voiceTracks).
- `Staff-1` with notes but **no lyrics** appears in 019 (282 notes) and 020 (606 notes). These are unlabeled vocal lines (020 firstLine "ALL…" suggests a third voice, possibly the King). They could not be mapped to a named part and were **excluded** from voiceTracks. If a third voice is needed for these numbers, revisit.

## Guessed / derived titles
- All titles derived from the opening firstLine (speaker tag stripped) since no canonical title metadata is present. Notably approximate: 004 ("La, la, la, la"), 014 ("Society has quite forsaken…"), 017 ("This ceremonial our wish displays"). 023 combines Nos. 23 & 24 under Lady Sophy's recit opening line.

## Principals with no tracks (omitted from parts)
- **Tarara, Calynx, Salata, Melene** have zero matching tracks anywhere in the dataset, so no part entries were created for them (validation requires real candidates). Add them if/when tracks surface.

---
