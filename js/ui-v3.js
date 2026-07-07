// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: MIT

// ui.js — renders the opera chooser + the three stages (pick part -> pick song
// -> practise) and wires the practice player. Big, friendly, forgiving.

import { Synth } from './synth-v2.js';
import { Player } from './player-v2.js';
import { loadOpera, songsForPart, getPart, makeRouting, matchedTracks } from './opera-v2.js';
import { buildLyrics, activeSyllable } from './lyrics-v2.js';

const $ = (id) => document.getElementById(id);
const LAST_OPERA_KEY = 'gands.lastOpera';

export function initApp(manifest) {
  const synth = new Synth();
  const state = {
    manifest,
    cfg: null,          // current opera config (songs.json)
    partId: null,
    song: null,
    player: null,
    lyrics: null,
    opts: { mutePiano: false, otherParts: true, speed: 1, volume: 0.85, pianoVolume: 0.8, otherVolume: 0.5 },
    raf: null,
  };
  let lastHi = '';     // key of the current highlight state (syllable + singing?)
  let lastLine = -1;   // index of the display line currently scrolled to

  // Start decoding the sampled instruments straight away (shared across operas).
  synth.ensure();
  const warming = $('warming');
  if (warming) { warming.hidden = false; synth.whenSettled(() => { warming.hidden = true; }); }

  // ---- opera chooser (the title dropdown) -----------------------------------
  $('brand').textContent = manifest.brand;
  const select = $('opera-select');
  select.innerHTML = '';
  manifest.operas.forEach((o) => {
    const opt = document.createElement('option');
    opt.value = o.id; opt.textContent = o.name;
    select.appendChild(opt);
  });
  select.onchange = () => selectOpera(select.value);

  const start = manifest.operas.find((o) => o.id === safeGet(LAST_OPERA_KEY)) ? safeGet(LAST_OPERA_KEY) : manifest.default;
  select.value = start;
  selectOpera(start, false);   // initial load: don't scroll, keep the header in view

  function selectOpera(id, scroll = true) {
    const entry = manifest.operas.find((o) => o.id === id) || manifest.operas[0];
    safeSet(LAST_OPERA_KEY, entry.id);
    select.value = entry.id;
    document.title = entry.name + ' ' + manifest.brand;

    teardownPlayer();
    state.partId = null;
    state.song = null;
    hide('stage-song');
    hide('stage-player');

    loadOpera(entry.dir).then((cfg) => {
      state.cfg = cfg;
      $('credit').innerHTML = cfg.meta.credit;
      renderPartButtons();
      show('stage-part');
      if (scroll) scrollToStage('stage-part');
    }).catch((err) => {
      console.error(err);
      $('part-buttons').innerHTML = '<p class="empty">Sorry — this opera failed to load.</p>';
      show('stage-part');
    });
  }

  // ---- Stage 1: parts -------------------------------------------------------
  function renderPartButtons() {
    const box = $('part-buttons');
    box.innerHTML = '';
    state.cfg.parts.forEach((part) => {
      const b = bigButton(part.label, () => choosePart(part.id));
      b.dataset.part = part.id;
      box.appendChild(b);
    });
  }

  function choosePart(partId) {
    state.partId = partId;
    state.song = null;
    highlight('part-buttons', (b) => b.dataset.part === partId);
    show('stage-song');
    hide('stage-player');
    teardownPlayer();
    renderSongButtons();
    renderCrumbs();
    scrollToStage('stage-song');
  }

  // ---- Stage 2: songs -------------------------------------------------------
  function renderSongButtons() {
    const box = $('song-buttons');
    box.innerHTML = '';
    const list = songsForPart(state.cfg, state.partId);
    if (!list.length) {
      box.innerHTML = '<p class="empty">This part doesn’t sing in any number. Pick another part above.</p>';
      return;
    }
    list.forEach(({ song, note }) => {
      const b = document.createElement('button');
      b.className = 'big song';
      b.dataset.song = song.id;
      b.innerHTML =
        `<span class="num">No. ${escapeHtml(song.number)}</span>` +
        `<span class="songtitle">${escapeHtml(song.title)}</span>` +
        `<span class="songtype">${escapeHtml(song.type)}</span>` +
        (note ? `<span class="songnote">${escapeHtml(note)}</span>` : '');
      b.onclick = () => chooseSong(song);
      box.appendChild(b);
    });
  }

  function chooseSong(song) {
    state.song = song;
    highlight('song-buttons', (b) => b.dataset.song === song.id);
    renderCrumbs();
    openPlayer(song);
    scrollToStage('stage-player');
  }

  // ---- Breadcrumbs ----------------------------------------------------------
  function renderCrumbs() {
    const part = getPart(state.cfg, state.partId);
    const crumbs = $('crumbs');
    crumbs.innerHTML = '';
    crumbs.appendChild(crumb('▶ Part: ' + part.label + ' (change)', () => {
      hide('stage-player'); teardownPlayer();
      highlight('song-buttons', () => false);
      state.song = null;
      scrollToStage('stage-part');
    }));
    if (state.song) {
      crumbs.appendChild(crumb('♫ Song: No. ' + state.song.number + ' (change)', () => {
        hide('stage-player'); teardownPlayer();
        highlight('song-buttons', () => false);
        state.song = null;
        scrollToStage('stage-song');
      }));
    }
  }

  // ---- Stage 3: practice player --------------------------------------------
  function openPlayer(song) {
    teardownPlayer();
    show('stage-player');
    const player = new Player(synth);
    state.player = player;
    applyRouting();
    synth.setMasterVolume(state.opts.volume);
    synth.setPianoVolume(state.opts.pianoVolume);
    synth.setOtherVolume(state.opts.otherVolume);
    $('volume').value = state.opts.volume;
    $('piano-volume').value = state.opts.pianoVolume;
    $('other-volume').value = state.opts.otherVolume;
    setToggle('btn-mute-piano', !state.opts.mutePiano, 'Piano ON', 'Piano OFF');
    setToggle('btn-play-all', state.opts.otherParts, 'Other Parts ON', 'Other Parts OFF');

    $('lyrics').innerHTML = '<p class="loading">Loading the music…</p>';
    setPlayIcon(false);

    player.loadUrl(state.cfg.baseUrl + '/' + song.file).then(() => {
      if (state.player !== player) return; // user moved on while loading
      const part = getPart(state.cfg, state.partId);
      state.lyrics = buildLyrics(player, matchedTracks(state.cfg, song, part), song.voiceTracks);
      player.onEnd = () => { setPlayIcon(false); cancelRaf(); renderPlayhead(); };
      renderLyricsStatic();
      renderPlayhead();
    }).catch((err) => {
      $('lyrics').innerHTML = '<p class="loading">Sorry — that number wouldn’t load.</p>';
      console.error(err);
    });

    bindTransport();
  }

  function applyRouting() {
    if (!state.player) return;
    const part = getPart(state.cfg, state.partId);
    const r = makeRouting(state.cfg, state.song, part, state.opts);
    state.player.audible = r.audible;
    state.player.timbre = r.timbre;
    synth.setLeadTracks(r.leadTracks);
    synth.setPianoTracks(r.pianoTracks);
  }

  // Reflect a toggle's current state: label text + gold "off" styling.
  function setToggle(id, on, onText, offText) {
    const btn = $(id);
    btn.classList.toggle('off', !on);
    btn.querySelector('.lbl').textContent = on ? onText : offText;
  }

  function bindTransport() {
    $('btn-play').onclick = () => {
      state.player.toggle();
      setPlayIcon(state.player.playing);
      if (state.player.playing) startRaf(); else cancelRaf();
    };
    $('btn-restart').onclick = () => { state.player.restart(); renderPlayhead(); };
    $('btn-back').onclick = () => { state.player.skip(-10); renderPlayhead(); };
    $('btn-fwd').onclick = () => { state.player.skip(10); renderPlayhead(); };

    $('seek').oninput = (e) => {
      const pos = (e.target.value / 1000) * state.player.duration;
      state.player.seek(pos);
      renderPlayhead();
    };

    $('volume').oninput = (e) => {
      state.opts.volume = +e.target.value;
      synth.setMasterVolume(state.opts.volume);
    };

    $('piano-volume').oninput = (e) => {
      state.opts.pianoVolume = +e.target.value;
      synth.setPianoVolume(state.opts.pianoVolume);
    };

    $('other-volume').oninput = (e) => {
      state.opts.otherVolume = +e.target.value;
      synth.setOtherVolume(state.opts.otherVolume);
    };

    $('btn-mute-piano').onclick = () => {
      state.opts.mutePiano = !state.opts.mutePiano;
      setToggle('btn-mute-piano', !state.opts.mutePiano, 'Piano ON', 'Piano OFF');
      applyRouting();
      state.player.reschedule();
    };

    $('btn-play-all').onclick = () => {
      state.opts.otherParts = !state.opts.otherParts;
      setToggle('btn-play-all', state.opts.otherParts, 'Other Parts ON', 'Other Parts OFF');
      applyRouting();
      state.player.reschedule();
    };

    document.querySelectorAll('#speeds button').forEach((btn) => {
      btn.onclick = () => {
        state.opts.speed = +btn.dataset.speed;
        state.player.setSpeed(state.opts.speed);
        highlight('speeds', (b) => b === btn);
      };
    });
  }

  // ---- Lyric + playhead rendering ------------------------------------------
  function renderLyricsStatic() {
    const box = $('lyrics');
    if (!state.lyrics || !state.lyrics.hasLyrics) {
      box.innerHTML = '<p class="loading">(This number has no printed words — just play along.)</p>';
      return;
    }
    box.innerHTML = '';
    state.lyrics.lines.forEach((line, li) => {
      if (!line) return;
      const div = document.createElement('div');
      div.className = 'lyric-line' + (line.mine ? ' mine' : ' other');
      div.dataset.line = li;
      if (line.label) {
        const tag = document.createElement('span');
        tag.className = 'speaker';
        tag.textContent = line.label;
        div.appendChild(tag);
      }
      line.syls.forEach((syl) => {
        const span = document.createElement('span');
        if (line.mine) {
          span.className = 'syl';
          span.dataset.index = syl.index;
        } else {
          span.className = 'word';
        }
        span.textContent = syl.text;
        div.appendChild(span);
      });
      box.appendChild(div);
    });
  }

  function renderPlayhead() {
    const player = state.player;
    if (!player) return;
    const pos = player.getPosition();
    const frac = player.duration ? pos / player.duration : 0;
    $('seek').value = Math.round(frac * 1000);
    $('time-now').textContent = fmt(pos);
    $('time-tot').textContent = fmt(player.duration);

    if (state.lyrics && state.lyrics.hasLyrics) {
      const active = activeSyllable(state.lyrics, pos);
      const cur = state.lyrics.syllables[active];
      // your syllable is gold only while it is actually sounding; once its note
      // (or melisma) is over it settles to the sung grey like everything else.
      const singing = cur && pos < (cur.end != null ? cur.end : Infinity);
      const hiKey = active + '|' + (singing ? 1 : 0);
      if (hiKey !== lastHi) {
        lastHi = hiKey;
        $('lyrics').querySelectorAll('.syl').forEach((s) => {
          const i = +s.dataset.index;
          s.classList.toggle('sung', i < active || (i === active && !singing));
          s.classList.toggle('now', i === active && singing);
        });
      }
      // Scroll follows whichever line is sounding now — including the greyed
      // other-part cues — so it glides through them instead of leaping straight
      // to your next entry after a long rest.
      const li = currentLineIndex(state.lyrics.lines, pos);
      if (li !== lastLine && li >= 0) {
        lastLine = li;
        const box = $('lyrics');
        const lineEl = box.querySelector(`.lyric-line[data-line="${li}"]`);
        if (lineEl) {
          // Scroll only inside the lyrics box (never the whole page), so the
          // transport stays reachable on small screens.
          const target = lineEl.offsetTop - (box.clientHeight - lineEl.offsetHeight) / 2;
          box.scrollTo({ top: Math.max(0, target), behavior: 'smooth' });
        }
      }
    }
  }

  // Index of the last display line that has begun by `pos` (any character's).
  function currentLineIndex(lines, pos) {
    let idx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i] && lines[i].start <= pos + 0.02) idx = i; else if (lines[i]) break;
    }
    return idx;
  }

  function startRaf() {
    cancelRaf();
    const step = () => {
      renderPlayhead();
      if (state.player && state.player.playing) state.raf = requestAnimationFrame(step);
    };
    state.raf = requestAnimationFrame(step);
  }
  function cancelRaf() { if (state.raf) cancelAnimationFrame(state.raf); state.raf = null; }

  function teardownPlayer() {
    cancelRaf();
    if (state.player) { state.player.pause(); state.player = null; }
    state.lyrics = null;
    lastHi = '';
    lastLine = -1;
    state.opts.mutePiano = false;
    state.opts.otherParts = true;
    state.opts.speed = 1;
    resetToggleLabels();
  }

  function resetToggleLabels() {
    // default: both ON (piano on, other parts on)
    if ($('btn-mute-piano')) setToggle('btn-mute-piano', true, 'Piano ON', 'Piano OFF');
    if ($('btn-play-all')) setToggle('btn-play-all', true, 'Other Parts ON', 'Other Parts OFF');
    highlight('speeds', (b) => b.dataset.speed === '1');
    setPlayIcon(false);
  }

  function setPlayIcon(playing) {
    const b = $('btn-play');
    if (!b) return;
    b.querySelector('.lbl').textContent = playing ? 'Pause' : 'Play';
    b.classList.toggle('playing', playing);
  }
}

// ---- small helpers ----------------------------------------------------------
function bigButton(label, onClick) {
  const b = document.createElement('button');
  b.className = 'big';
  b.textContent = label;
  b.onclick = onClick;
  return b;
}
function crumb(label, onClick) {
  const b = document.createElement('button');
  b.className = 'crumb';
  b.textContent = label;
  b.onclick = onClick;
  return b;
}
function highlight(containerId, pred) {
  document.querySelectorAll('#' + containerId + ' button').forEach((b) => b.classList.toggle('selected', pred(b)));
}
function show(id) { $(id).hidden = false; }
function hide(id) { $(id).hidden = true; }
function scrollToStage(id) { $(id).scrollIntoView({ behavior: 'smooth', block: 'start' }); }
function fmt(s) { s = Math.max(0, Math.floor(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
function escapeHtml(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function safeGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function safeSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
