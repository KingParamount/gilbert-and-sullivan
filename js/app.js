// Gilbert & Sullivan Learn-O-Matic 4000
// Copyright (C) 2026 KingParamount and contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

// app.js — bootstrap. Loads the opera manifest (operas.json) and starts the UI.
// To add another opera: drop its folder under /operas, generate its songs.json,
// and add one line to operas.json. No code changes needed.

import { initApp } from './ui.js';

fetch('operas.json')
  .then((r) => r.json())
  .then((manifest) => initApp(manifest))
  .catch((err) => {
    console.error(err);
    document.body.insertAdjacentHTML('afterbegin',
      '<p style="padding:1rem;font:1.2rem sans-serif">Sorry — the opera list failed to load. ' +
      'If you opened this file directly, run it through a small web server instead.</p>');
  });
