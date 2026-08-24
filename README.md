# Residency Reviewers

Static site for hosted study reviewers (BCSC Qbank, Oculus Uterque, Mania, etc.), published via GitHub Pages.

No patient data lives in this repo. Only self-contained review/study HTML files belong here.

## Workflow
- Files are pushed here from `Reviewers/` (or wherever the current version lives) when a reviewer is ready to publish.
- Only the current version of each reviewer is kept here — older versions stay local in `Reviewers/old/`.
- Edits: change the file, `git add`, `git commit`, `git push` — GitHub Pages redeploys automatically.
