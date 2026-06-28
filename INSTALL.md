# Installing the G&S Learn-O-Matic on your website

This is a **self-contained static website**. There is **no server software,
database, or build step** — it's just a folder of files (HTML, CSS, JavaScript,
the karaoke files, and the piano/oboe sounds). To "install" it you simply copy
the folder onto a web host. It will run on essentially any normal web hosting.

> **TL;DR for your webmaster:** Upload the whole `gilbert-and-sullivan` folder
> into your web space (e.g. into a subfolder called `learn-o-matic`) and visit
> `https://yoursociety.org/learn-o-matic/`. All links are relative, so it works
> in any folder. It must be served over http/https (not opened as a local file).

---

## What you need
- A modern web browser (Chrome, Edge, Safari, Firefox — anything from the last
  few years). Works on tablets/iPads, which is handy at rehearsal.
- Somewhere to put files that gets served over the web — i.e. **normal web
  hosting**. Almost everything qualifies: a cPanel/Plesk host, any FTP web space,
  GitHub Pages, Netlify, etc.
- About **8 MB** of space.

There is nothing to compile and nothing to "run" on the server — the whole thing
executes in the visitor's browser.

---

## Option A — Upload to your existing website (most common)

1. Get the files: unzip the bundle (or download the folder). You'll have a folder
   called **`gilbert-and-sullivan`** containing `index.html`, `js/`, `css/`,
   `operas/`, etc.
2. Open your host's **File Manager** (in cPanel/Plesk) or an **FTP** program
   (e.g. the free [FileZilla](https://filezilla-project.org/)).
3. Upload the **whole folder** into your web area (usually `public_html` or
   `www`). Put it in a subfolder, e.g. rename it to `learn-o-matic`.
4. Visit it: `https://yoursociety.org/learn-o-matic/`

That's it. Because every link inside the app is **relative**, it works at any
address or sub-folder — you don't have to edit anything. Just don't rename the
files/folders *inside* it.

---

## Option B — A WordPress site

WordPress can't run this as a normal "page", but it sits happily *alongside* it:

1. Using your host's **File Manager** or FTP, upload the `gilbert-and-sullivan`
   folder into a subfolder of your site (next to `wp-content`), e.g.
   `learn-o-matic`.
2. In WordPress, add a **menu link** (Appearance → Menus → Custom Link) pointing
   to `/learn-o-matic/`.
3. (Alternatively, some "host static HTML" plugins can serve it from inside the
   media library — but the folder-upload method above is simplest and most
   robust.)

---

## Option C — Free hosting via GitHub Pages (if you have no web host)

1. Create a free account at [github.com](https://github.com).
2. Make a new **public repository** (any name, e.g. `learn-o-matic`).
3. Upload all the files from the `gilbert-and-sullivan` folder into it
   (drag-and-drop in the browser works).
4. Repository **Settings → Pages → Build and deployment → Deploy from a branch**,
   choose `main` and `/ (root)`, Save.
5. After a minute it's live at
   `https://YOURNAME.github.io/learn-o-matic/`.

(This is exactly how the original is hosted.)

---

## Important: it must be served by a web server

The app loads its data with modern browser features that are blocked when you
open the page as a local file (`file://...`). So **double-clicking `index.html`
won't work** — you'll get a "failed to load" message.

- On a real website (Options A–C) this is automatic; nothing to do.
- To **preview on your own computer** first, you need a tiny local web server.
  The simplest, if you have Python installed: open a terminal in the
  `gilbert-and-sullivan` folder and run
  `python3 -m http.server 8000`
  then visit `http://localhost:8000/`.

---

## Adding or editing operas later (optional, for the technical)

Everything opera-specific lives in **data files** — the app code never needs to
change:

- Each opera is a folder under `operas/` containing its `.kar` files and a
  `songs.json` that describes its parts and numbers.
- `operas.json` (in the root) lists which operas appear in the title dropdown.
- `scripts/build-songs.py` regenerates the `songs.json` files from the `.kar`
  files; `README.md` documents the `songs.json` format.
- `OPERA_REVIEW.md` records the known quirks and best-guesses in the current
  data set (e.g. a few numbers whose printed number is approximate).

---

## Credits & terms (please keep)

- The karaoke/MIDI files are courtesy of **The Gilbert & Sullivan Archive**
  (https://www.gsarchive.net). The credit is shown in the page footer — please
  leave it there. As you're republishing their files, it's courteous to drop the
  Archive a note of thanks (and to check their terms).
- The application code is licensed under the **MIT License** (see `LICENSE` and
  `NOTICE`) — free to use, share and adapt, with no warranty. (The music files
  have their own terms, as above.)
