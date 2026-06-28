// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

// opera.js — all opera-specific reasoning lives here, driven entirely by the
// songs.json config. Swap in a different opera by pointing at a different
// config; nothing below names "Trial by Jury".

const CHORAL_DISPLAY = { Bridesamaids: 'Bridesmaids' }; // tidy up source typos for display
const VOICE_PARTS = ['Soprano', 'Alto', 'Tenor', 'Bass'];

export async function loadOpera(baseUrl) {
  const cfg = await (await fetch(baseUrl + '/songs.json')).json();
  cfg.baseUrl = baseUrl;
  return cfg;
}

export function getPart(cfg, partId) {
  return cfg.parts.find((p) => p.id === partId);
}

// Tracks in this song that belong to this part. Honours an optional per-song
// `partTracks` override ({ partId: [trackName, ...] }) for cases where a generic
// track name (e.g. "Vocal") means different soloists in different numbers.
export function matchedTracks(cfg, song, part) {
  let matched = part.candidates.filter((c) => song.voiceTracks.includes(c));
  const overrides = song.partTracks;
  if (overrides) {
    const claimed = new Set();
    for (const pid in overrides) for (const t of overrides[pid]) claimed.add(t);
    const mine = overrides[part.id] || [];
    // a track explicitly claimed by another part is not ours
    matched = matched.filter((t) => !claimed.has(t) || mine.includes(t));
    // add our explicitly-claimed tracks that are present in this song
    for (const t of mine) if (song.voiceTracks.includes(t) && !matched.includes(t)) matched.push(t);
  }
  return matched;
}

// Songs that include this part, each annotated with the track(s) it maps to and
// an optional friendly note (shared character / sung within a chorus line).
export function songsForPart(cfg, partId) {
  const part = getPart(cfg, partId);
  return cfg.songs
    .map((song) => {
      const matched = matchedTracks(cfg, song, part);
      if (!matched.length) return null;
      return { song, matched, note: noteFor(cfg, part, matched[0]) };
    })
    .filter(Boolean);
}

function noteFor(cfg, part, track) {
  if (/[/&]/.test(track)) {                       // two characters share this track
    const np = norm(part.label);
    const others = track.split(/[/&]/).map((s) => s.trim()).filter(Boolean)
      .filter((x) => { const nx = norm(x); return !(nx.includes(np) || np.includes(nx)); });
    return others.length ? 'shares a line with ' + others.map(display).join(' & ')
                         : 'shares a line with another character';
  }
  if ((cfg.soloistTracks || []).includes(track)) return 'combined soloists — includes other voices';
  if ((cfg.choralTracks || []).includes(track) && VOICE_PARTS.includes(part.label)) {
    return 'sung within the ' + display(track) + ' line';
  }
  return '';
}

const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
function display(track) { return CHORAL_DISPLAY[track] || track; }

// Build the audio routing for a chosen song + part, given live toggle options.
export function makeRouting(cfg, song, part, opts) {
  // per-song `accompaniment` extends the opera-wide list (for oddly-named piano
  // tracks like "Staff-2"/"Staff-3" that are piano only in certain numbers).
  const accomp = song.accompaniment ? cfg.accompaniment.concat(song.accompaniment) : cfg.accompaniment;
  const matched = matchedTracks(cfg, song, part);
  const allVoices = song.voiceTracks;

  return {
    leadTracks: matched,   // the part being learned (routed to the lead bus)
    audible(track) {
      if (accomp.includes(track)) return !opts.mutePiano;
      if (matched.includes(track)) return true;
      if (opts.playAll && allVoices.includes(track)) return true;
      return false;
    },
    timbre(track) {
      if (accomp.includes(track)) return 'piano';
      if (matched.includes(track)) return 'voice';
      return 'choir';
    },
  };
}
