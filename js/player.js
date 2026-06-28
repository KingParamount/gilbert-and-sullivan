// player.js — sequencer / transport on top of Synth.
// Holds events in tempo-mapped "base seconds" (speed-independent) and uses a
// look-ahead scheduler so play / pause / seek / speed changes stay responsive.

import { parseMidi, makeTickToSec } from './midi.js';

const LOOKAHEAD = 0.2;   // seconds scheduled in advance
const TICK_MS = 25;      // scheduler poll interval

export class Player {
  constructor(synth) {
    this.synth = synth;
    this.events = [];
    this.lyrics = [];
    this.trackNames = [];
    this.duration = 0;

    this.position = 0;     // base seconds (musical position, independent of speed)
    this.speed = 1;
    this.playing = false;

    this._t0 = 0;          // ctx time at which current run started
    this._p0 = 0;          // base-seconds position at which current run started
    this._idx = 0;
    this._timer = null;

    // routing hooks, set by the UI from the opera config
    this.audible = () => false;
    this.timbre = () => 'piano';
    this.volume = () => 1;

    this.onEnd = null;
  }

  async loadUrl(url) {
    const buf = await (await fetch(url)).arrayBuffer();
    this.load(buf);
  }

  load(buffer) {
    const m = parseMidi(buffer);
    const t2s = makeTickToSec(m.division, m.tempos);
    this.trackNames = m.tracks.map((t) => t.name);

    const events = [], lyrics = [];
    let duration = 0;
    m.tracks.forEach((tr) => {
      tr.notes.forEach((n) => {
        const s = t2s(n.tick), e = t2s(n.tick + n.dur);
        events.push({ sec: s, dur: Math.max(0.05, e - s), midi: n.midi, vel: n.vel, track: tr.name });
        if (e > duration) duration = e;
      });
      tr.lyrics.forEach((l) => lyrics.push({ sec: t2s(l.tick), text: l.text, track: tr.name }));
    });
    events.sort((a, b) => a.sec - b.sec);
    lyrics.sort((a, b) => a.sec - b.sec);

    this.events = events;
    this.lyrics = lyrics;
    this.duration = duration;
    this.position = 0;
  }

  getPosition() {
    if (this.playing) return this._p0 + (this.synth.ctx.currentTime - this._t0) * this.speed;
    return this.position;
  }

  play() {
    if (this.playing || !this.events.length) return;
    this.synth.resume();
    this.playing = true;
    this._p0 = this.position;
    this._t0 = this.synth.ctx.currentTime + 0.06;
    this._idx = this.events.findIndex((e) => e.sec >= this._p0);
    if (this._idx < 0) this._idx = this.events.length;
    this._loop();
  }

  _loop() {
    if (!this.playing) return;
    const ctx = this.synth.ctx;
    const horizon = this._p0 + (ctx.currentTime + LOOKAHEAD - this._t0) * this.speed;

    while (this._idx < this.events.length && this.events[this._idx].sec <= horizon) {
      const e = this.events[this._idx++];
      if (!this.audible(e.track)) continue;
      const when = this._t0 + (e.sec - this._p0) / this.speed;
      this.synth.scheduleNote(Math.max(when, ctx.currentTime), e.dur / this.speed, e.midi, e.vel, e.track, this.timbre(e.track));
    }
    this.synth.prune();

    if (this.getPosition() >= this.duration) {
      this._stopClock();
      this.position = this.duration;
      this.synth.allOff();
      if (this.onEnd) this.onEnd();
      return;
    }
    this._timer = setTimeout(() => this._loop(), TICK_MS);
  }

  _stopClock() { this.playing = false; clearTimeout(this._timer); this._timer = null; }

  pause() {
    if (!this.playing) return;
    this.position = this.getPosition();
    this._stopClock();
    this.synth.allOff();
  }

  toggle() { this.playing ? this.pause() : this.play(); }

  seek(sec) {
    const was = this.playing;
    if (was) this.pause();
    this.position = Math.max(0, Math.min(this.duration, sec));
    if (was) this.play();
  }

  skip(delta) { this.seek(this.getPosition() + delta); }
  restart() { this.seek(0); }

  setSpeed(s) {
    const was = this.playing;
    if (was) this.pause();
    this.speed = s;
    if (was) this.play();
  }

  // Re-evaluate which tracks are audible mid-playback (mute piano / play all).
  reschedule() {
    if (!this.playing) return;
    const pos = this.getPosition();
    this.pause();
    this.position = pos;
    this.play();
  }
}
