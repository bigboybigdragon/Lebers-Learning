#!/usr/bin/env python3
"""Replace inline base64 figures in bcsc-qbank/*.html with references to bcsc-qbank/img/.

Run from the repo root:  python3 tools/slim_section_pages.py

Why: each section page embedded its figures as base64 data URIs, so every edit to a page
stored another multi-MB blob in git history. The same images already exist as files in
bcsc-qbank/img/ (written by extract_quiz_data.py, named by content hash). This rewrites
the <img id="qimg-N"> elements to point at those files and adds loading="lazy".

Safe by design: it touches ONLY image src attributes. Question ids, the embedded
qbankData JSON, and every localStorage key are left byte-identical, so saved progress
is unaffected (see SITE_GUIDE.md golden rules).

Idempotent: pages already converted are skipped.
"""
import re, os, base64, hashlib

SECTIONS = ["General","Fundamentals","Optics","Pathology","Neuro","Peds","Plastics",
            "Cornea","Uveitis","Glaucoma","Cataract","Retina","Refractive"]

EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
qdir = os.path.join(root, "bcsc-qbank")
imgdir = os.path.join(qdir, "img")

PATTERN = re.compile(r'<img id="(qimg-\d+)" src="data:([^;]+);base64,([^"]*)"')

total_before = total_after = 0
for name in SECTIONS:
    path = os.path.join(qdir, name + ".html")
    html = open(path, encoding="utf-8").read()
    before = len(html)
    total_before += before

    missing = []
    def sub(m):
        iid, mime, b64 = m.groups()
        raw = base64.b64decode(b64)
        fname = hashlib.sha256(raw).hexdigest()[:12] + EXT.get(mime, ".jpg")
        if not os.path.exists(os.path.join(imgdir, fname)):
            missing.append(fname)                      # never drop an image we can't find
            return m.group(0)
        return '<img id="%s" loading="lazy" src="img/%s"' % (iid, fname)

    new_html, n = PATTERN.subn(sub, html)
    if missing:
        raise SystemExit("ABORT %s: %d image files missing from img/ (run extract_quiz_data.py first)"
                         % (name, len(missing)))

    if n:
        open(path, "w", encoding="utf-8").write(new_html)
    after = len(new_html)
    total_after += after
    print("%-14s %5.1f MB -> %5.1f MB  (%d figures%s)"
          % (name + ".html", before/1024/1024, after/1024/1024, n, "" if n else ", already converted"))

print("\nTOTAL %.1f MB -> %.1f MB  (%.0f%% smaller)"
      % (total_before/1024/1024, total_after/1024/1024,
         100*(1-total_after/total_before) if total_before else 0))
