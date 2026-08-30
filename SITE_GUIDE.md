# Leber's Learning — Site Guide

Read this fully before changing anything. This site hosts interactive study reviewers for
Arlon (ophthalmology residency). It is a static site on GitHub Pages; user progress lives in
each visitor's browser `localStorage` and **must never be lost by an update**.

- Live site: https://bigboybigdragon.github.io/Lebers-Learning/
- Repo: `bigboybigdragon/Lebers-Learning` (public — no patient data ever goes in this repo)
- Local working copy: `~/Documents/Cowork/Web/Lebers-Learning/`
- Remote uses SSH over port 443 (`ssh://git@ssh.github.com:443/...`) because port 22 is
  blocked on some networks. Already configured; just `git push origin main`.
- Deploys automatically ~1–2 min after every push to `main`. Verify with
  `curl "https://bigboybigdragon.github.io/Lebers-Learning/<page>?v=123"` (query busts cache).

## Golden rules (breaking any of these destroys user progress)

1. **Never change a localStorage key that already exists.** Keys are listed in the inventory
   below and in the `REVIEWERS` config in `index.html`.
2. **Never change question `id` values inside a page's embedded data.** Saved answers are
   keyed by question id; regenerating ids orphans everyone's progress.
3. **Never rename or move a published HTML file.** URLs are shared and bookmarked.
4. **New features store data in NEW keys** (convention: `<progresskey>_<feature>`, e.g.
   `bcscanki_glaucoma_flags`). Never piggyback new data into the existing progress object.
5. **Never overwrite a value the page itself saves** except through the page's own code paths.
6. Commit each feature separately and push; verify live before declaring done.

## localStorage key inventory

Per section page (progress key `KEY` is in the `REVIEWERS` config in index.html):

| Key           | Written by      | Contents                                        |
|---------------|-----------------|-------------------------------------------------|
| `KEY`         | section page    | BCSC: `{qid: letter\|"__shown__"}` · OU: `{state:{...},ratings:{...}}` |
| `KEY_stats`   | section page    | `{ans, cor}` — answered/correct counts for landing-page score badge |
| `KEY_flags`   | section page    | `{qid: 1}` — flagged/bookmarked questions       |

Site-wide: `bcscTheme` (landing+BCSC theme), `ouTheme` (OU pages theme),
`ouUnlocked_lebers` (OU password-gate unlock memory), `skipgc` (GoatCounter self-exclusion),
`bcsc_exam_session_v1` (Exam Mode in-progress autosave — see Exam Mode section).

## Repo layout

```
index.html            landing page (config-driven; see below)
SITE_GUIDE.md         this file
bcsc-qbank/           13 BCSC section pages (one engine, per-file data + keys)
oculus-uterque/       5 Oculus Uterque source-exam pages (a second engine)
```

## How to add a new reviewer (the streamlined path)

1. **Build the page(s).** One self-contained HTML file per section, in a NEW subfolder
   (kebab-case, e.g. `mania-reviewers/`). Easiest: copy an existing page of the closest
   engine (BCSC = simple locked-answer quiz; OU = filters + flashcard mode) and replace its
   embedded question data, title, and keys. Every page must have:
   - `<meta charset>` + `<meta name="viewport" content="width=device-width, initial-scale=1">`
   - a **unique progress key** `slug_v1` (new key = rule 1 satisfied), and the `_stats`
     side-channel write inside `updateScore` (copy the pattern)
   - light/dark support: `?theme=` query param + theme toggle (copy the theme scripts)
   - a **Home button** in the header scorebar linking `../index.html`
   - the auto-resume snippet (scrolls to first unanswered on load — copy it)
   - the GoatCounter snippet at the end **exactly as on other pages** (with
     `no_onload` settings + the `count({path: location.pathname})` loader)
2. **Register it on the landing page.** In `index.html`, find `var REVIEWERS = [` and add one
   group object (or add sections to an existing group). That block's comment documents every
   field. This is the only landing-page edit needed — rendering, progress bars, score badges,
   theme links, and password gates are all generated from it.
3. **Password-gating (optional):** set `password: {hash, storeKey}` on the group.
   `hash` = SHA-256 hex of the password (`python3 -c "import hashlib;print(hashlib.sha256(b'PASS').hexdigest())"`),
   `storeKey` = new key like `xyzUnlocked_lebers`.
4. **Commit & push**, wait for deploy, verify live: page loads, Home button works, answering
   one question moves the landing-page progress bar (then reset that answer).

## How to update existing questions safely

- Edit text/rationale/images in place — fine.
- Do NOT renumber or re-derive question ids (rule 2). If a rebuild from source data is
  unavoidable, warn Arlon first: progress for that section will detach.
- Keep the file name identical (rule 3).

## Testing checklist before push

- `python3` string-replace scripts with `assert` on exact matches (never blind regex over
  all files); run against all files of an engine at once — the 13 BCSC files share identical
  engine code, as do the 5 OU files.
- After deploy, test in a real browser with a cache-busting query param.
- Check theme toggle in both modes, phone width (375px), and that `localStorage` keys written
  are only the expected ones.

## Exam Mode (bcsc-qbank/Quiz.html)

Cross-subspecialty exam: you choose subspecialties and a count **per subspecialty**;
answers and rationales stay hidden until Submit; results show per-subspecialty scores
and per-item timing, then ask for confirmation before saving.

Derived data (regenerate with the tool below, never hand-edit):
- `bcsc-qbank/data/*.json` — per-section question pools + a complete MCQ answer key
  (used to recompute `_stats` exactly after writing answers).
- `bcsc-qbank/img/*.jpg` — clinical figures extracted from the base64 data URIs
  embedded in the section pages, named by content hash and deduped. Pool entries
  reference them as `images` / `ratImages` filenames; Quiz.html renders them from
  `img/` with lazy loading and a click-to-zoom lightbox.

Answers are written to each section's progress key and `_stats` only when the user
confirms in the results window, and an answer already recorded on a section page is
never overwritten.

**In-progress exams autosave** to their own key `bcsc_exam_session_v1` after every
answer and on submit (question ids + picks + per-item times + submitted flag). On load,
Quiz.html offers to resume or discard it; resuming refetches the section pools, rebuilds
the exam, restores every selection, and — if the exam was already submitted — replays
the reveal and results so the pending save is not lost. The session key is cleared when
the user saves, declines to save, discards, or starts a new exam. It never writes to a
section progress key, so an abandoned exam cannot pollute real progress.

**If you edit questions in any bcsc-qbank/*.html page, regenerate the data files:**

```
python3 tools/extract_quiz_data.py
```

and commit the changed `bcsc-qbank/data/` and `bcsc-qbank/img/` files with the page
edit. The `tools` field in the landing `REVIEWERS` config renders the highlighted
Exam Mode card.

**Figures are now external files, not base64.** The section pages' `<img id="qimg-N">`
elements point at `img/<hash>.jpg` (converted by `tools/slim_section_pages.py`, which is
idempotent and safe to re-run). This took the 13 pages from 83 MB to 14 MB, so editing a
page no longer writes a multi-MB blob into git history. Two consequences to respect:

- `extract_quiz_data.py` reads **both** page forms (inline base64 and `img/` references),
  so it keeps working either way — do not "simplify" it to one branch.
- A page's figures now depend on `bcsc-qbank/img/` existing. Never delete files there
  without re-running both tools.

Four `class="inline-fig"` images inside answer-option text in Pathology.html are still
base64 (95 KB total) — deliberately left alone; extracting them would mean rewriting
option HTML for negligible gain.

`.git` itself is still ~700 MB from the pre-slimming history. That is historical weight
only; new commits are small now. Shrinking it would require rewriting history
(git-filter-repo) and a force-push — do that only if Arlon explicitly asks.
