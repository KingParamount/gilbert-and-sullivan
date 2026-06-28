# G&S Learn-O-Matic

A quick, friendly, web-based karaoke MIDI player to help singers learn their
parts — built first for Gilbert & Sullivan's *Trial by Jury*, but designed to be
reconfigured for other operas without touching the code.

## How it works

1. **Pick your part** (Angelina, Edwin, Judge, … Soprano, Alto, Tenor, Bass).
2. **Pick a song** — the list is filtered to numbers your part actually sings in.
3. **Practise** — the player plays the piano accompaniment **plus your part only**,
   with karaoke lyrics highlighted syllable-by-syllable. Slow it down, loop with
   the progress bar, mute the piano, or bring in all the other parts.

Everything is a static site: plain HTML + ES modules + CSS. No build step, no
framework, no server-side code. It runs as-is on GitHub Pages.

## Running locally

Because it uses ES modules and `fetch`, open it through a tiny web server
(not `file://`):

```sh
cd gilbert-and-sullivan
python3 -m http.server 8000
# then visit http://localhost:8000/
```

## Project layout

```
gilbert-and-sullivan/
  index.html
  css/style.css
  js/
    app.js      bootstrap — choose which opera to load
    opera.js    all opera/config-driven logic (filtering, audio routing)
    ui.js       renders the three stages and wires the controls
    player.js   sequencer/transport (play, pause, seek, speed) on the synth
    synth.js    sound engine — bundled sampled instruments, synth fallback
    midi.js     Standard MIDI File + .kar lyric parser
    lyrics.js   karaoke line/syllable builder
  vendor/
    WebAudioFontPlayer.js   sample player library (MIT)
  assets/instruments/
    piano.js    sampled acoustic grand (FluidR3 GM, ~1.2 MB)
    oboe.js     sampled oboe for the learner's line (FluidR3 GM, ~120 KB)
  operas/
    trial-by-jury/
      songs.json   the ONLY opera-specific data (see below)
      *.kar        the karaoke MIDI files
```

## Adding another opera

1. Make `operas/<your-opera>/`, drop the `.kar` files in.
2. Create `songs.json` describing it (see schema below). The
   `scripts/build-songs.py` generator (used for Trial by Jury) reads the track
   names straight out of the `.kar` files and is the easy way to start.
3. Point `OPERA` in `js/app.js` at the new folder (or extend the UI to offer a
   choice of operas).

### `songs.json` schema

```jsonc
{
  "meta": { "opera": "...", "composer": "...", "displayName": "...", "credit": "..." },
  "accompaniment": ["Right Hand", "Left Hand", "Tempo Track"], // never selectable; the "piano"
  "choralTracks":  ["Women", "Men", ...],                      // generic chorus lines (for friendly notes)
  "parts": [
    { "id": "alto", "label": "Alto", "candidates": ["Alto", "Altos", "Women"] } // logical part -> track names
  ],
  "songs": [
    { "id": "tbj01", "number": "1", "title": "...", "type": "Opening Chorus",
      "file": "tbj01.kar", "voiceTracks": ["Soprano","Alto","Tenor","Bass"] }   // singable tracks present
  ]
}
```

The `candidates` list is the mapping layer: a singer's logical part (e.g. "Alto")
maps to whatever the MIDI tracks are actually called in each number ("Alto",
"Altos", or the combined "Women" line). A song appears for a part when any of the
part's `candidates` is in that song's `voiceTracks`.

## Credits

MIDI / karaoke files courtesy of **The Gilbert & Sullivan Archive**
(https://www.gsarchive.net/). Please keep the credit in the page footer.

## Known limitations (by design)

- **Shared-character tracks**: in a few numbers two characters share one MIDI
  track (e.g. No. 3 "Usher/Judge"). Soloing one plays both — the song button
  shows a note saying so.
- **Chorus splits**: where the chorus is only "Women"/"Men", Soprano/Alto map to
  "Women" and Tenor/Bass to "Men" (a note says "sung within the Women line").
- **One lyric line per song**: the highlighted words follow the karaoke lyric
  track, which matches the soloist in solo numbers and the main line in choruses.
- **Sound**: bundled sampled instruments (a FluidR3 grand piano for the
  accompaniment, an oboe for the learner's line) played via WebAudioFont. If the
  samples ever fail to load, `synth.js` automatically falls back to a built-in
  oscillator synth so there is always sound. Swap the piano for a smaller
  sample set by changing one entry in `INSTRUMENTS` at the top of `synth.js`.
```
