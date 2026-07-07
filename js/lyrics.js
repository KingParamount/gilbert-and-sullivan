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
  blocks = leadWithMyPart(blocks);

  const syllables = [];               // YOUR syllables (shared with their lines)
  const lines = [];
  let prevSlots = null, prevEnd = null;
  blocks.forEach((b) => {
    const slots = labelSlots(b.tracks, order, myTracks);
    // Between contiguous lines, only announce who JOINED (+) or LEFT (−) rather
    // than restating the whole cast; a break in the singing forces a restatement.
    const contiguous = prevEnd != null && (b.start - prevEnd) <= RESTATE_GAP;
    const showLabel = labelDelta(contiguous ? prevSlots : null, slots);
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

// "My part leads": your lines are always shown; another character's line is kept
// only if it BEGINS while you are resting (a genuine turn-taking cue) and does
// not overlap a cue already kept — so six voices in counterpoint never stack up.
function leadWithMyPart(blocks) {
  const mine = blocks.filter((b) => b.mine);
  if (!mine.length) return blocks;                 // you don't sing here — show all
  const busy = mergeIntervals(mine.map((b) => [b.start, b.end]));
  const kept = [];
  let lastOtherEnd = -Infinity;
  for (const b of blocks) {                         // already sorted by start
    if (b.mine) { kept.push(b); continue; }
    if (!within(b.start, busy) && b.start >= lastOtherEnd) {
      kept.push(b);
      lastOtherEnd = b.end;
    }
  }
  return kept;
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
    const hit = key && out.find((o) => o.key === key && Math.abs(o.start - b.start) < 1.2);
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

const RESTATE_GAP = 2.0;   // a silence longer than this restarts the cast label

// Break a group singing the same words into ordered label "slots". The part
// being learned is always named first and never folded into a group. The rest
// collapse: chorus S+A -> "Women", T+B -> "Men", any mix -> "Chorus"; principals
// 1-2 named, 3+ -> "Principals". Longest is three slots: [Your Part, Principals,
// Chorus]. Returning slots (not a string) lets us diff cast changes below.
function labelSlots(tracks, order, myTracks = []) {
  const uniq = [...new Set(tracks)].sort((a, b) => order.indexOf(a) - order.indexOf(b));
  const mine = uniq.filter((t) => myTracks.includes(t));
  const others = uniq.filter((t) => !myTracks.includes(t));
  const principals = others.filter((t) => !isChorusVoice(t));
  const chorus = others.filter((t) => isChorusVoice(t));

  const slots = [...mine];                          // your part, always first
  if (principals.length === 1) slots.push(principals[0]);
  else if (principals.length === 2) slots.push(principals.join(' & '));
  else if (principals.length >= 3) slots.push('Principals');
  if (chorus.length) slots.push(collapseChorus(chorus));
  return slots;
}

// The label to actually show, given the previous line's slots. Unchanged cast ->
// nothing; a pure join or departure -> "+ …" / "− …"; a wholly new group (or a
// tangled change) -> the full cast restated.
function labelDelta(prev, curr) {
  const join = (a) => a.join(', ');
  if (!prev) return join(curr);
  if (prev.join('|') === curr.join('|')) return null;      // same cast: say nothing
  const added = curr.filter((s) => !prev.includes(s));
  const removed = prev.filter((s) => !curr.includes(s));
  if (!curr.some((s) => prev.includes(s))) return join(curr);   // no overlap: new group
  if (added.length && !removed.length) return '+ ' + join(added);
  if (removed.length && !added.length) return '− ' + join(removed);
  return join(curr);                                        // messy change: restate
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
