// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: MIT

// lyrics.js — turn a song's raw lyric events into karaoke lines.
//
// Two source conventions coexist:
//  * Legacy .kar — every character's words are merged onto one dense track, and
//    line breaks are explicit standalone "\r"/"\n"/"\\"/"/" events. '@' lines are
//    metadata; speaker tags like "[Judge]" are kept.
//  * Per-character MusicXML .mid — each character has their OWN lyric track and
//    there are no break markers, so lines are inferred from phrasing. This lets
//    us show a MULTI-PART view: your line highlighted, the rest greyed-readable.
//
// Every builder returns the same shape:
//   { syllables, lines, hasLyrics }
// where `syllables` are YOUR highlightable syllables (sorted by time, each with
// .index and .line) and `lines` is the display timeline — each line is
//   { mine, label, syls }
// `mine` lines carry per-syllable objects (with .index) for karaoke highlight;
// other lines carry a single { text, index:null } word blob. `label` is the
// character name, set only when the singer changes from the line before.

export function buildLyrics(player, myTracks = [], voiceTracks = null) {
  const withLyrics = tracksWithOwnLyrics(player.lyrics, voiceTracks);
  if (withLyrics.length >= 2) return multiPart(player, myTracks || [], withLyrics, voiceTracks);

  // legacy / single-part: prefer the part's own words, else the densest track.
  const events = pickSource(player.lyrics, myTracks);
  return assemble(segment(events));
}

// ---- source selection ------------------------------------------------------

// Voice tracks that carry their own words (per-character files). Piano / Tempo
// have no lyrics and drop out; a legacy merged-lyric .kar yields none of these.
function tracksWithOwnLyrics(all, voiceTracks) {
  const counts = {};
  all.forEach((l) => { counts[l.track] = (counts[l.track] || 0) + 1; });
  const tracks = voiceTracks || Object.keys(counts);
  return tracks.filter((t) => counts[t]);
}

// Prefer the words on the chosen part's own tracks; fall back to the single
// densest lyric track for legacy merged-lyric .kar files.
function pickSource(all, leadTracks) {
  if (leadTracks && leadTracks.length) {
    const own = all.filter((l) => leadTracks.includes(l.track));
    if (own.length) return own;
  }
  const counts = {};
  all.forEach((l) => { counts[l.track] = (counts[l.track] || 0) + 1; });
  let source = null, best = -1;
  for (const k in counts) if (counts[k] > best) { best = counts[k]; source = k; }
  return all.filter((l) => l.track === source);
}

// ---- line segmentation -----------------------------------------------------

function segment(events) {
  const hasMarkers = events.some((e) => /^[\r\n\\/]/.test(e.text));
  return hasMarkers ? byMarkers(events) : byPhrase(events);
}

// Legacy: line breaks are explicit marker events.
function byMarkers(events) {
  const syllables = [];
  let line = 0;
  let started = false;
  events.forEach((e) => {
    let txt = e.text;
    if (txt[0] === '@') return;                 // metadata line, skip
    let newLine = false;
    while (txt && (txt[0] === '\r' || txt[0] === '\n' || txt[0] === '\\' || txt[0] === '/')) {
      newLine = true; txt = txt.slice(1);
    }
    if (newLine && started) line++;
    txt = txt.replace(/[\r\n]+/g, ' ');         // tidy any stray line endings mid-syllable
    if (txt.trim() === '') return;              // pure line-break event
    syllables.push({ sec: e.sec, end: e.end, text: txt, line });
    started = true;
  });
  return syllables;
}

// Per-character files carry no break markers: start a new line at sentence-
// ending punctuation, at a poetic-line comma followed by a breath, or after a
// long gap — but only ever at a word boundary, and with a hard length cap.
const GAP = 1.5;      // base seconds between syllables that forces a new line
const MAX_SYL = 16;   // longest line before a forced wrap

function byPhrase(events) {
  const syllables = [];
  let line = 0, sinceBreak = 0;
  let prevSec = null, prevText = '';
  events.forEach((e) => {
    if (e.text[0] === '@') return;
    const txt = e.text.replace(/[\r\n]+/g, ' ');
    if (txt.trim() === '') return;
    if (prevSec !== null) {
      const gap = e.sec - prevSec;
      const sentenceEnd = /[.!?;:]["')]?\s*$/.test(prevText);
      const poeticComma = /,["')]?\s*$/.test(prevText) && gap >= GAP;
      // mid-word syllables have no trailing space, so a held/tied syllable can't
      // strand the rest of its word onto the next line.
      const wordEnd = /\s$/.test(prevText);
      if (wordEnd && (sentenceEnd || poeticComma || gap >= GAP || sinceBreak >= MAX_SYL)) {
        line++; sinceBreak = 0;
      }
    }
    syllables.push({ sec: e.sec, end: e.end, text: txt, line });
    sinceBreak++;
    prevSec = e.sec; prevText = txt;
  });
  return syllables;
}

function groupLines(syllables) {
  const lines = [];
  syllables.forEach((s) => { (lines[s.line] || (lines[s.line] = [])).push(s); });
  return lines.filter(Boolean);
}

// ---- single-part assembly (legacy shape) -----------------------------------

function assemble(syllables) {
  const map = new Map();          // compact the (possibly sparse) line numbers
  let next = 0;
  syllables.forEach((s) => { if (!map.has(s.line)) map.set(s.line, next++); });
  syllables.forEach((s, i) => { s.index = i; s.line = map.get(s.line); });
  const grouped = [];
  syllables.forEach((s) => { (grouped[s.line] || (grouped[s.line] = [])).push(s); });
  const lines = grouped.map((syls) => ({ mine: true, label: null, syls, start: syls[0].sec }));
  return { syllables, lines, hasLyrics: syllables.length > 0 };
}

// ---- multi-part timeline ---------------------------------------------------

function multiPart(player, myTracks, withLyrics, voiceTracks) {
  const order = voiceTracks || withLyrics;
  const rank = (t) => { const i = order.indexOf(t); return i < 0 ? 999 : i; };

  // one block per (character, phrase)
  let blocks = [];
  withLyrics.forEach((track) => {
    groupLines(segment(player.lyrics.filter((l) => l.track === track))).forEach((syls) => {
      blocks.push({
        tracks: [track], syls, mine: myTracks.includes(track),
        start: syls[0].sec,
        end: Math.max(...syls.map((s) => s.end != null ? s.end : s.sec)),
      });
    });
  });

  blocks = mergeUnison(blocks);
  blocks.sort((a, b) => (a.start - b.start) ||
    (Math.min(...a.tracks.map(rank)) - Math.min(...b.tracks.map(rank))));
  blocks = leadWithMyPart(blocks, player, myTracks);

  const syllables = [];               // YOUR syllables (shared with their lines)
  const lines = [];
  let prevSlots = null, prevEnd = null;
  blocks.forEach((b) => {
    const slots = labelSlots(b.tracks, order, myTracks);
    // Between contiguous lines, only announce who JOINED (+) or LEFT (−) rather
    // than restating the whole cast. A break in the singing normally forces a
    // restatement — BUT if the very same singer simply carries on after a rest
    // (a soloist phrasing their song), don't re-announce them every line.
    const contiguous = prevEnd != null && (b.start - prevEnd) <= RESTATE_GAP;
    const sameCast = prevSlots && prevSlots.join('|') === slots.join('|');
    const showLabel = labelDelta((contiguous || sameCast) ? prevSlots : null, slots);
    prevSlots = slots; prevEnd = b.end;
    if (b.mine) {
      const syls = b.syls.map((s) => {
        const o = { text: s.text, sec: s.sec, end: s.end, line: lines.length, index: 0 };
        syllables.push(o);
        return o;
      });
      lines.push({ mine: true, label: showLabel, syls, start: b.start });
    } else {
      lines.push({ mine: false, label: showLabel, start: b.start,
        syls: [{ text: b.syls.map((s) => s.text).join(''), index: null }] });
    }
  });

  syllables.sort((a, b) => a.sec - b.sec);
  syllables.forEach((o, i) => { o.index = i; });
  return { syllables, lines, hasLyrics: lines.length > 0 };
}

// "My part leads": your lines are always shown. When you are NOT singing we show
// exactly ONE other voice at a time — never a wall of nine counter-lines. An
// other line qualifies if you are actually resting through a real part of it
// (not merely if it happens to START in a rest — that dropped voices whose
// phrase began under your singing and carried on past it), and it is kept only
// if it does not overlap an other line we already kept (the one-at-a-time rule).
function leadWithMyPart(blocks, player, myTracks) {
  const mine = blocks.filter((b) => b.mine);
  if (!mine.length) return blocks;                 // you don't sing here — show all
  // "Busy" = when you are ACTUALLY singing, taken from your notes — not from
  // lyric-block end times, which over-run a phrase into the following rest (a
  // held syllable's end scan grabs the next phrase's onset) and would wrongly
  // mask another singer's verse sung during your silence.
  const my = new Set(myTracks || []);
  const notes = (player.events || []).filter((e) => my.has(e.track));
  const busy = mergeIntervals(
    notes.length ? notes.map((e) => [e.sec, e.sec + e.dur])
                 : mine.map((b) => [b.start, b.end]));   // fallback if no note data
  const voiceKey = (b) => [...new Set(b.tracks)].sort().join('|');
  const kept = [];
  let last = null;                                  // last OTHER block we kept
  for (const b of blocks) {                         // already sorted by start
    if (b.mine) { kept.push(b); continue; }
    if (uncovered([b.start, b.end], busy) < 0.5) continue;   // you sing over it — hide
    // One voice at a time: skip a line only if a DIFFERENT voice is already
    // showing across this moment. A singer's OWN consecutive lines never clash
    // (the held note ending one phrase overlaps the next — that must not drop
    // every other line), so a soloist's whole verse comes through intact.
    if (last && b.start < last.end - 0.05 && voiceKey(b) !== voiceKey(last)) continue;
    kept.push(b);
    last = b;
  }
  return kept;
}

// Seconds of interval `iv` that lie OUTSIDE the (sorted, merged) `busy` set —
// i.e. how long you are resting while this line sings.
function uncovered(iv, busy) {
  let free = iv[1] - iv[0];
  for (const [s, e] of busy) {
    const lo = Math.max(iv[0], s), hi = Math.min(iv[1], e);
    if (hi > lo) free -= (hi - lo);
  }
  return free;
}

function mergeIntervals(intervals) {
  const s = intervals.slice().sort((a, b) => a[0] - b[0]);
  const out = [];
  for (const iv of s) {
    const last = out[out.length - 1];
    if (last && iv[0] <= last[1] + 0.05) last[1] = Math.max(last[1], iv[1]);
    else out.push(iv.slice());
  }
  return out;
}

function within(t, intervals) {
  return intervals.some(([s, e]) => t >= s - 0.05 && t < e);
}

// Fold blocks that sing identical words at (nearly) the same moment into one
// line — e.g. an SATB chorus in unison — so it reads once, not four times.
function mergeUnison(blocks) {
  const norm = (b) => b.syls.map((s) => s.text).join('').replace(/[^a-z]/gi, '').toLowerCase();
  const sorted = blocks.slice().sort((a, b) => a.start - b.start);
  const out = [];
  sorted.forEach((b) => {
    const key = norm(b);
    // Fold two voices' identical words when their lines actually OVERLAP in time
    // (not just start close together) — two singers phrase the same patter with
    // slightly different bar-lines, so a start-only test folded them in some
    // places and not others, which is why a unison partner flickered in and out.
    const hit = key && out.find((o) => o.key === key && o.start < b.end + 0.4 && b.start < o.end + 0.4);
    if (hit) {
      hit.tracks.push(...b.tracks);
      if (b.mine && !hit.mine) { hit.syls = b.syls; hit.end = b.end; }  // prefer your own timing
      hit.mine = hit.mine || b.mine;
    } else {
      out.push({ ...b, key });
    }
  });
  return out;
}

const WOMEN = /^(Soprano|Mezzo|Alto|Contralto)/i;
const MEN = /^(Tenor|Bariton|Bass)/i;
const isChorusVoice = (t) => WOMEN.test(t) || MEN.test(t);
// Fold a divisi stave onto its part name: "Alto 1"/"Alto 2" -> "Alto",
// "Sopranos II" -> "Sopranos". Leaves undivided names ("Robin") untouched.
const baseVoice = (t) => t.replace(/\s+(?:\d+|I{1,3}|IV|V)$/i, '').trim() || t;

const RESTATE_GAP = 2.0;   // a silence longer than this restarts the cast label

// Break a group singing the same words into ordered label "slots". The part
// being learned is always named first and never folded into a group. The rest
// collapse: chorus S+A -> "Women", T+B -> "Men", any mix -> "Chorus"; principals
// 1-2 named, 3+ -> "Principals". Longest is three slots: [Your Part, Principals,
// Chorus]. Returning slots (not a string) lets us diff cast changes below.
function labelSlots(tracks, order, myTracks = []) {
  const uniq = [...new Set(tracks)].sort((a, b) => order.indexOf(a) - order.indexOf(b));
  const mine = uniq.filter((t) => myTracks.includes(t));

  // If YOU are singing this line, it is labelled with your part and nothing
  // else — never your part plus whoever happens to sing it with you. You only
  // ever see another name when someone sings while you are resting. Divisi fold
  // so two staves of your line read as the part ("Alto", not "Alto 1, Alto 2").
  if (mine.length) return [...new Set(mine.map(baseVoice))];

  // Otherwise this is someone else's line, sung during your rest: name them,
  // collapsed to a single group where they are a chorus.
  const others = uniq;
  const principals = others.filter((t) => !isChorusVoice(t));
  const chorus = others.filter((t) => isChorusVoice(t));
  const slots = [];
  if (principals.length === 1) slots.push(principals[0]);
  else if (principals.length === 2) slots.push(principals.join(' & '));
  else if (principals.length >= 3) slots.push('Principals');
  if (chorus.length) slots.push(collapseChorus(chorus));
  return slots;
}

// The label to actually show, given the previous line's slots. If the singer(s)
// are unchanged, say nothing; otherwise just name who is singing now. (No "+ …"
// / "− …" running deltas — they read as noise.)
function labelDelta(prev, curr) {
  if (prev && prev.join('|') === curr.join('|')) return null;   // same singer(s): say nothing
  return curr.join(', ');                                       // changed: name who sings now
}

function collapseChorus(parts) {
  const women = parts.filter((t) => WOMEN.test(t));
  const men = parts.filter((t) => MEN.test(t));
  if (women.length && men.length) return 'Chorus';   // mixed voices (S/B, A/T/B, …)
  if (women.length >= 2) return 'Women';             // Soprano + Alto (+ divisi)
  if (men.length >= 2) return 'Men';                 // Tenor + Bass (+ divisi)
  return parts[0];                                    // a single voice part: name it
}

// ---- playhead --------------------------------------------------------------

// Index of the syllable currently being sung at position `pos` (seconds).
export function activeSyllable(lyrics, pos) {
  let idx = -1;
  const s = lyrics.syllables;
  for (let i = 0; i < s.length; i++) { if (s[i].sec <= pos + 0.02) idx = i; else break; }
  return idx;
}
