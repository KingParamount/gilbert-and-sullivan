// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: MIT

const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));

// synth.js — sound engine. Prefers bundled sampled instruments (WebAudioFont:
// a real grand piano + oboe), and falls back to a dependency-free oscillator
// synth if the samples fail to load, so there is ALWAYS sound. Each MIDI track
// routes through its own gain node. This is the only file that makes sound.

const LIB = 'vendor/WebAudioFontPlayer.js';
const INSTRUMENTS = {
  piano: { src: 'assets/instruments/piano.js', global: '_tone_0000_FluidR3_GM_sf2_file' },
  oboe:  { src: 'assets/instruments/oboe.js',  global: '_tone_0680_FluidR3_GM_sf2_file' },
};

// Sound for the parts being learned: 'synth' = built-in oscillator voices,
// 'sample' = the sampled oboe. The piano accompaniment is always the sampled
// piano. Flip this one word to switch the voices back to the oboe.
const DEFAULT_VOICE_SOURCE = 'synth';

export class Synth {
  constructor() {
    this.ctx = null;
    this.master = null;       // overall output ("Master volume")
    this.leadBus = null;      // the part being learned
    this.accompBus = null;    // piano + any non-rehearsed voices ("Accompaniment volume")
    this.trackGains = {};
    this.leadTracks = new Set();
    this.voiceSource = DEFAULT_VOICE_SOURCE;
    this._voices = [];        // active oscillator voices
    this.player = null;       // WebAudioFontPlayer, when samples are available
    this.presets = {};
    this.ready = false;       // true once samples decoded
    this.settled = false;     // true once we know whether samples loaded or not
    this._readyCbs = [];
    this._loadStarted = false;
  }

  ensure() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.85;
      this.master.connect(this.ctx.destination);
      this.leadBus = this.ctx.createGain();
      this.leadBus.gain.value = 1;
      this.leadBus.connect(this.master);
      this.accompBus = this.ctx.createGain();
      this.accompBus.gain.value = 0.7;
      this.accompBus.connect(this.master);
      this._loadInstruments();
    }
    return this.ctx;
  }

  resume() { this.ensure(); if (this.ctx.state === 'suspended') this.ctx.resume(); }

  // Called when we know whether sampled sound is available (ready=true/false).
  whenSettled(cb) { if (this.settled) cb(this.ready); else this._readyCbs.push(cb); }
  _settle() { this.settled = true; this._readyCbs.forEach((cb) => cb(this.ready)); this._readyCbs = []; }

  async _loadInstruments() {
    if (this._loadStarted) return;
    this._loadStarted = true;
    try {
      await loadScript(LIB);
      await Promise.all(Object.values(INSTRUMENTS).map((i) => loadScript(i.src)));
      this.player = new window.WebAudioFontPlayer();
      Object.values(INSTRUMENTS).forEach((i) => this.player.loader.decodeAfterLoading(this.ctx, i.global));
      await waitDecoded(this.player, Object.values(INSTRUMENTS).map((i) => i.global));
      this.presets = {};
      for (const k in INSTRUMENTS) this.presets[k] = window[INSTRUMENTS[k].global];
      this.ready = true;
    } catch (e) {
      console.warn('Sampled instruments unavailable — using the built-in synth.', e);
      this.ready = false;
    }
    this._settle();
  }

  setMasterVolume(v) { this.ensure(); this.master.gain.setTargetAtTime(v, this.ctx.currentTime, 0.01); }
  setAccompVolume(v) { this.ensure(); this.accompBus.gain.setTargetAtTime(v, this.ctx.currentTime, 0.01); }

  // Tell the synth which tracks are the part being learned; everything else
  // routes through the accompaniment bus.
  setLeadTracks(names) {
    this.leadTracks = new Set(names);
    if (!this.ctx) return;
    for (const name in this.trackGains) {
      const g = this.trackGains[name];
      try { g.disconnect(); } catch (e) {}
      g.connect(this.leadTracks.has(name) ? this.leadBus : this.accompBus);
    }
  }

  trackGain(name) {
    if (!this.trackGains[name]) {
      const g = this.ctx.createGain();
      g.gain.value = 1;
      g.connect(this.leadTracks.has(name) ? this.leadBus : this.accompBus);
      this.trackGains[name] = g;
    }
    return this.trackGains[name];
  }

  // Schedule one note. `when`/`dur` are in AudioContext seconds. The piano is
  // always the sampled instrument; the voices follow `voiceSource`.
  scheduleNote(when, dur, midi, vel, trackName, timbre) {
    const wantSample = (timbre === 'piano') || (this.voiceSource === 'sample');
    if (this.ready && this.player && wantSample) this._scheduleSampled(when, dur, midi, vel, trackName, timbre);
    else this._scheduleOsc(when, dur, midi, vel, trackName, timbre);
  }

  _scheduleSampled(when, dur, midi, vel, trackName, timbre) {
    const preset = timbre === 'voice' ? this.presets.oboe : this.presets.piano;
    const colour = timbre === 'voice' ? 0.9 : (timbre === 'choir' ? 0.4 : 0.6); // your line leads
    const volume = Math.max(0.05, vel / 127) * colour;
    this.player.queueWaveTable(this.ctx, this.trackGain(trackName), preset, when, midi, dur, volume);
  }

  // --- fallback oscillator synth (used only if samples fail to load) ---------
  _scheduleOsc(when, dur, midi, vel, trackName, timbre) {
    const ctx = this.ctx;
    const out = this.trackGain(trackName);
    const freq = 440 * Math.pow(2, (midi - 69) / 12);
    const v = Math.min(1, vel / 127);
    const mkOsc = (type, detune) => { const o = ctx.createOscillator(); o.type = type; o.frequency.value = freq; o.detune.value = detune; return o; };

    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.connect(out);
    const g = ctx.createGain();
    g.connect(filter);

    let oscs, stopAt;
    if (timbre === 'voice' || timbre === 'choir') {
      const cutoff = timbre === 'voice' ? 2600 : 1500;
      const wave = timbre === 'voice' ? 'sawtooth' : 'triangle';
      const detune = timbre === 'voice' ? 4 : 6;
      const amp = v * (timbre === 'voice' ? 0.42 : 0.3);
      filter.frequency.value = cutoff;
      oscs = [mkOsc(wave, -detune), mkOsc(wave, detune)];
      const susEnd = Math.max(when + 0.07, when + dur);
      g.gain.setValueAtTime(0.0001, when);
      g.gain.linearRampToValueAtTime(amp, when + 0.04);
      g.gain.exponentialRampToValueAtTime(Math.max(0.0001, amp * 0.85), susEnd);
      g.gain.setTargetAtTime(0.0001, susEnd, 0.08);
      stopAt = susEnd + 0.3;
    } else {
      const amp = v * 0.5;
      const bright = 1600 + v * 3200;
      const decayT = clamp(4.0 * Math.pow(2, -(midi - 57) / 22), 0.45, 7);
      oscs = [mkOsc('triangle', 0)];
      filter.frequency.setValueAtTime(bright, when);
      filter.frequency.exponentialRampToValueAtTime(700, when + decayT);
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(amp, when + 0.004);
      g.gain.exponentialRampToValueAtTime(Math.max(0.0001, amp * 0.04), when + decayT);
      const off = Math.max(when + 0.05, when + dur);
      g.gain.setTargetAtTime(0.0001, off, 0.08);
      stopAt = Math.min(when + decayT, off) + 0.3;
    }
    oscs.forEach((o) => { o.connect(g); o.start(when); o.stop(stopAt); });
    this._voices.push({ oscs, g, end: stopAt });
  }

  // Silence everything immediately (used on pause / seek / reschedule).
  allOff() {
    if (!this.ctx) return;
    if (this.player && this.ready) { try { this.player.cancelQueue(this.ctx); } catch (e) {} }
    const now = this.ctx.currentTime;
    this._voices.forEach((v) => {
      try { v.g.gain.cancelScheduledValues(now); v.g.gain.setTargetAtTime(0.0001, now, 0.015); } catch (e) {}
      v.oscs.forEach((o) => { try { o.stop(now + 0.05); } catch (e) {} });
    });
    this._voices = [];
  }

  prune() {
    if (!this.ctx) return;
    const now = this.ctx.currentTime;
    if (this._voices.length > 400) this._voices = this._voices.filter((v) => v.end > now);
  }
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error('Failed to load ' + src));
    document.head.appendChild(s);
  });
}

// Resolve once every named preset has decoded sample buffers.
function waitDecoded(player, names) {
  return new Promise((resolve, reject) => {
    let tries = 0;
    const check = () => {
      if (names.every((n) => player.loader.loaded(n))) return resolve();
      if (++tries > 200) return reject(new Error('Sample decode timed out')); // ~24s
      setTimeout(check, 120);
    };
    check();
  });
}
