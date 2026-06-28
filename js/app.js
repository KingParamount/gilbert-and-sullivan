// app.js — bootstrap. Loads the opera config and starts the UI.
// To add another opera later: drop its folder under /operas and change OPERA.

import { loadOpera } from './opera.js';
import { initUI } from './ui.js';

const OPERA = 'operas/trial-by-jury';

loadOpera(OPERA)
  .then((cfg) => initUI(cfg))
  .catch((err) => {
    console.error(err);
    document.getElementById('lyrics')?.replaceChildren();
    document.body.insertAdjacentHTML('afterbegin',
      '<p style="padding:1rem;font:1.2rem sans-serif">Sorry — the song list failed to load. ' +
      'If you opened this file directly, run it through a small web server instead.</p>');
  });
