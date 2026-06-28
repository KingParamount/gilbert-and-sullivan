// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

// ui.js — renders the opera chooser + the three stages (pick part -> pick song
// -> practise) and wires the practice player. Big, friendly, forgiving.

import { Synth } from './synth.js';
import { Player } from './player.js';
import { loadOpera, songsForPart, getPart, makeRouting } from './opera.js';
import { buildLyrics, activeSyllable } from './lyrics.js';

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
    opts: { mutePiano: false, playAll: false, speed: 1, volume: 0.85, accompVolume: 0.7 },
    raf: null,
  };
  let lastActive = -1; // index of the currently-highlighted lyric syllable

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
  selectOpera(start);

  function selectOpera(id) {
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
      scrollToStage('stage-part');
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
    synth.setAccompVolume(state.opts.accompVolume);
    $('volume').value = state.opts.volume;
    $('accomp-volume').value = state.opts.accompVolume;

    $('lyrics').innerHTML = '<p class="loading">Loading the music…</p>';
    setPlayIcon(false);

    player.loadUrl(state.cfg.baseUrl + '/' + song.file).then(() => {
      if (state.player !== player) return; // user moved on while loading
      state.lyrics = buildLyrics(player);
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

    $('accomp-volume').oninput = (e) => {
      state.opts.accompVolume = +e.target.value;
      synth.setAccompVolume(state.opts.accompVolume);
    };

    $('btn-mute-piano').onclick = (e) => {
      state.opts.mutePiano = !state.opts.mutePiano;
      e.currentTarget.classList.toggle('on', state.opts.mutePiano);
      e.currentTarget.querySelector('.lbl').textContent = state.opts.mutePiano ? 'Piano is OFF' : 'Mute Piano';
      applyRouting();
      state.player.reschedule();
    };

    $('btn-play-all').onclick = (e) => {
      state.opts.playAll = !state.opts.playAll;
      e.currentTarget.classList.toggle('on', state.opts.playAll);
      e.currentTarget.querySelector('.lbl').textContent = state.opts.playAll ? 'Just My Part' : 'Play All Parts';
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
      div.className = 'lyric-line';
      div.dataset.line = li;
      line.forEach((syl) => {
        const span = document.createElement('span');
        span.className = 'syl';
        span.dataset.index = syl.index;
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
      if (active !== lastActive) {
        lastActive = active;
        const spans = $('lyrics').querySelectorAll('.syl');
        spans.forEach((s) => {
          const i = +s.dataset.index;
          s.classList.toggle('sung', i < active);
          s.classList.toggle('now', i === active);
        });
        const cur = state.lyrics.syllables[active];
        if (cur) {
          const box = $('lyrics');
          const lineEl = box.querySelector(`.lyric-line[data-line="${cur.line}"]`);
          if (lineEl) {
            // Scroll only inside the lyrics box (never the whole page), so the
            // transport stays reachable on small screens.
            const target = lineEl.offsetTop - (box.clientHeight - lineEl.offsetHeight) / 2;
            box.scrollTo({ top: Math.max(0, target), behavior: 'smooth' });
          }
        }
      }
    }
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
    lastActive = -1;
    state.opts.mutePiano = false;
    state.opts.playAll = false;
    state.opts.speed = 1;
    resetToggleLabels();
  }

  function resetToggleLabels() {
    const mp = $('btn-mute-piano'); if (mp) { mp.classList.remove('on'); mp.querySelector('.lbl').textContent = 'Mute Piano'; }
    const pa = $('btn-play-all'); if (pa) { pa.classList.remove('on'); pa.querySelector('.lbl').textContent = 'Play All Parts'; }
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
