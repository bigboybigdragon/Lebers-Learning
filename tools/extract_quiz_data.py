#!/usr/bin/env python3
"""Regenerate bcsc-qbank/data/*.json (quiz-mode question pools) from the section pages.

Run from the repo root:  python3 tools/extract_quiz_data.py

Re-run this whenever question content in a bcsc-qbank/*.html page changes, then commit
the regenerated data/ files together with the page change. The section pages' embedded
<script id="qbankData"> JSON is the source of truth; these files are derived.

Each data/<Section>.json contains:
  section  display label (must match the REVIEWERS config label in index.html)
  key      the section's localStorage progress key (NEVER changes; see SITE_GUIDE.md)
  file     the section page filename
  pool     text-only MCQs usable in Random Quiz: {id,q,options,answer,rationale,ref}
           (MCQs whose stem needs an image are excluded from the pool)
  answers  answer letter for EVERY MCQ id (including image ones) so the quiz page can
           recompute the section's _stats side-channel exactly after writing answers
data/manifest.json lists all sections with pool sizes for the quiz setup screen.
"""
import json, re, os

SECTIONS = [
    # (html file, display label, storage key)  — keep in sync with REVIEWERS in index.html
    ("General.html",      "Update on General Medicine",                 "bcscanki_general-medicine"),
    ("Fundamentals.html", "Fundamentals & Principles of Ophthalmology", "bcscanki_fundamentals"),
    ("Optics.html",       "Clinical Optics & Vision Rehabilitation",    "bcscanki_optics"),
    ("Pathology.html",    "Ophthalmic Pathology & Intraocular Tumors",  "bcscanki_pathology"),
    ("Neuro.html",        "Neuro-Ophthalmology",                        "bcscanki_neuro"),
    ("Peds.html",         "Pediatric Ophthalmology & Strabismus",       "bcscanki_peds-strabismus"),
    ("Plastics.html",     "Oculofacial Plastic & Orbital Surgery",      "bcscanki_plastics-orbit"),
    ("Cornea.html",       "External Disease & Cornea",                  "bcscanki_cornea"),
    ("Uveitis.html",      "Uveitis & Ocular Inflammation",              "bcscanki_uveitis"),
    ("Glaucoma.html",     "Glaucoma",                                   "bcscanki_glaucoma"),
    ("Cataract.html",     "Lens & Cataract",                            "bcscanki_cataract"),
    ("Retina.html",       "Retina & Vitreous",                          "bcscanki_retina"),
    ("Refractive.html",   "Refractive Surgery",                         "bcscanki_refractive"),
]

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
qdir = os.path.join(root, "bcsc-qbank")
outdir = os.path.join(qdir, "data")
os.makedirs(outdir, exist_ok=True)

manifest = []
for fname, label, key in SECTIONS:
    html = open(os.path.join(qdir, fname), encoding="utf-8").read()
    i = html.find('id="qbankData">')
    assert i > 0, f"qbankData not found in {fname}"
    i += len('id="qbankData">')
    j = html.find("</script>", i)
    qd = json.loads(html[i:j])

    pool, answers = [], {}
    for q in qd:
        if q.get("type") != "mcq":
            continue
        answers[str(q["id"])] = q["answer"]
        if q.get("images"):
            continue  # stem needs a figure; excluded from quiz pool
        rationale = q.get("rationale", "")
        if q.get("ratImages"):
            rationale += ' <span class="ref">(A figure accompanies this rationale on the section page.)</span>'
        pool.append({
            "id": q["id"], "q": q["q"], "options": q["options"],
            "answer": q["answer"], "rationale": rationale, "ref": q.get("ref", ""),
        })

    out = {"section": label, "key": key, "file": fname, "pool": pool, "answers": answers}
    jname = fname.replace(".html", ".json")
    with open(os.path.join(outdir, jname), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    manifest.append({"name": label, "file": fname, "json": "data/" + jname,
                     "key": key, "poolCount": len(pool)})
    print(f"{fname}: {len(pool)} pool / {len(answers)} mcq answers")

with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump({"sections": manifest}, f, ensure_ascii=False, indent=1)
print("manifest.json written")
