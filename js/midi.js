// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

// midi.js — minimal Standard MIDI File (format 0/1) + .kar lyric parser.
// Returns absolute-tick note/lyric events plus a tempo map; no opera-specific
// knowledge lives here.

export function parseMidi(buffer) {
  const u = new Uint8Array(buffer);
  const dv = new DataView(buffer);
  let p = 0;

  const tag = (n) => { let s = ''; for (let i = 0; i < n; i++) s += String.fromCharCode(u[p++]); return s; };
  const u32 = () => { const v = dv.getUint32(p); p += 4; return v; };
  const u16 = () => { const v = dv.getUint16(p); p += 2; return v; };
  const vlq = () => { let v = 0, b; do { b = u[p++]; v = (v << 7) | (b & 0x7f); } while (b & 0x80); return v; };

  if (tag(4) !== 'MThd') throw new Error('Not a MIDI file');
  u32();                       // header length (always 6)
  const format = u16();
  const ntrk = u16();
  const division = u16();      // ticks per quarter note (assume metrical, not SMPTE)

  const tracks = [];
  const tempos = [];

  for (let t = 0; t < ntrk; t++) {
    if (tag(4) !== 'MTrk') { const len = u32(); p += len; continue; }
    const len = u32();
    const end = p + len;
    let tick = 0, status = 0, name = null;
    const notes = [], lyrics = [], open = {};

    while (p < end) {
      tick += vlq();
      let b = u[p];
      if (b & 0x80) { status = b; p++; } else { b = status; } // running status
      const hi = b & 0xf0, ch = b & 0x0f;

      if (b === 0xff) {                       // meta event
        const mt = u[p++];
        const l = vlq();
        const data = u.subarray(p, p + l); p += l;
        if (mt === 0x03 && name === null) name = decodeText(data);
        else if (mt === 0x51) tempos.push({ tick, us: (data[0] << 16) | (data[1] << 8) | data[2] });
        else if (mt === 0x05) lyrics.push({ tick, text: decodeText(data) });
        else if (mt === 0x2f) break;          // end of track
      } else if (b === 0xf0 || b === 0xf7) {  // sysex
        const l = vlq(); p += l;
      } else if (hi === 0x90) {               // note on
        const n = u[p++], v = u[p++];
        if (v > 0) {
          open[ch] = open[ch] || {};
          const stack = open[ch][n] = open[ch][n] || [];
          // Retrigger: if this pitch is already sounding (a malformed file with a
          // missing note-off), end the previous note here rather than letting a
          // later note-off pair into a giant, hanging note.
          while (stack.length) { const s = stack.shift(); notes.push({ tick: s.tick, dur: Math.max(1, tick - s.tick), midi: n, vel: s.v }); }
          stack.push({ tick, v });
        } else closeNote(open, ch, n, tick, notes);
      } else if (hi === 0x80) {               // note off
        const n = u[p++]; p++; closeNote(open, ch, n, tick, notes);
      } else if (hi === 0xa0 || hi === 0xb0 || hi === 0xe0) { p += 2; } // 2-byte channel msgs
      else if (hi === 0xc0 || hi === 0xd0) { p += 1; }                 // 1-byte channel msgs
      else { p++; }
    }
    p = end;
    tracks.push({ name: name || ('Track ' + t), notes, lyrics });
  }

  return { format, division, tracks, tempos };
}

function closeNote(open, ch, n, tick, notes) {
  const stack = open[ch] && open[ch][n];
  if (stack && stack.length) {
    const s = stack.shift();
    notes.push({ tick: s.tick, dur: Math.max(1, tick - s.tick), midi: n, vel: s.v });
  }
}

function decodeText(arr) {
  let s = '';
  for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i]); // latin-1
  return s;
}

// Build a tick -> seconds function honouring all tempo changes.
export function makeTickToSec(division, tempos) {
  const tl = tempos.slice().sort((a, b) => a.tick - b.tick);
  if (!tl.length || tl[0].tick > 0) tl.unshift({ tick: 0, us: 500000 }); // default 120bpm
  const segs = [];
  let sec = 0;
  for (let i = 0; i < tl.length; i++) {
    segs.push({ tick: tl[i].tick, sec, us: tl[i].us });
    if (i + 1 < tl.length) sec += ((tl[i + 1].tick - tl[i].tick) / division) * (tl[i].us / 1e6);
  }
  return (tick) => {
    let s = segs[0];
    for (let i = 0; i < segs.length; i++) { if (segs[i].tick <= tick) s = segs[i]; else break; }
    return s.sec + ((tick - s.tick) / division) * (s.us / 1e6);
  };
}
