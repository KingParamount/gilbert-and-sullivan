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

// Songs that include this part, each annotated with the track(s) it maps to and
// an optional friendly note (shared character / sung within a chorus line).
export function songsForPart(cfg, partId) {
  const part = getPart(cfg, partId);
  return cfg.songs
    .map((song) => {
      const matched = part.candidates.filter((c) => song.voiceTracks.includes(c));
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
  const accomp = cfg.accompaniment;
  const matched = part.candidates.filter((c) => song.voiceTracks.includes(c));
  const allVoices = song.voiceTracks;

  return {
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
    volume(track) {
      if (matched.includes(track)) return 1;
      if (accomp.includes(track)) return 0.7;
      return 0.55;
    },
  };
}
