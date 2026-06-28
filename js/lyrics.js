// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

// lyrics.js — turn a song's raw lyric events into karaoke lines.
// .kar convention: a line break is signalled by a leading carriage return /
// newline (these files emit a standalone "\r" event) or a '\'/'/' marker;
// '@' lines are metadata. Speaker tags like "[Judge]" are kept as-is.

export function buildLyrics(player) {
  // Pick the track carrying the most lyric events as the lyric source.
  const counts = {};
  player.lyrics.forEach((l) => { counts[l.track] = (counts[l.track] || 0) + 1; });
  let source = null, best = -1;
  for (const k in counts) if (counts[k] > best) { best = counts[k]; source = k; }

  const events = player.lyrics.filter((l) => l.track === source);
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
    syllables.push({ sec: e.sec, text: txt, line });
    started = true;
  });

  const lines = [];
  syllables.forEach((s, i) => {
    s.index = i;
    (lines[s.line] || (lines[s.line] = [])).push(s);
  });

  return { syllables, lines, hasLyrics: syllables.length > 0 };
}

// Index of the syllable currently being sung at position `pos` (seconds).
export function activeSyllable(lyrics, pos) {
  let idx = -1;
  const s = lyrics.syllables;
  for (let i = 0; i < s.length; i++) { if (s[i].sec <= pos + 0.02) idx = i; else break; }
  return idx;
}
