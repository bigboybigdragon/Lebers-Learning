#!/usr/bin/env python3
"""One-time import: build the "Review Questions in Ophthalmology" (12 subspecialty pages)
and "BCSC End-of-Volume Quizzes" (13 subspecialty pages) reviewer sets from the source file
Reviewers/Ophtho_QBank_BCSC_Review_Desktop.html, which holds both question sets tagged
by a "section" field ("BCSC · ..." vs "Review Q · ...").

Run from the repo root:  python3 tools/import_review_and_eov.py

Design notes (see SITE_GUIDE.md):
- Pages are built from bcsc-qbank/Cataract.html as a byte-level template so the engine
  (theme, Home link, autosave/resume N/A here — that's Quiz.html only, misses/flagged
  filters, collapsible mobile header, GoatCounter, figure lightbox-free rendering,
  _stats side-channel) is identical to the existing BCSC section pages.
- The source file's own no-JS "staticApp" fallback (~570KB of the 926KB template) is
  DEAD CODE — the page's own script unconditionally hides it and shows #jsApp the
  instant JS runs, and every feature on this site already requires JS (GoatCounter,
  theme toggle, autosave). New pages built here omit it entirely: same functionality,
  ~60% smaller per page. (The 13 original BCSC files still carry it; that's a separate,
  not-yet-done cleanup — see SITE_GUIDE.md.)
- Each new question gets "type":"mcq" and "images"/"ratImages" arrays added (the source
  has neither field name/shape used elsewhere on the site) so the shared engine code
  (which checks q.type==="mcq" for scoring, and renders q.images) works unmodified.
- Figures: only "Review Q" questions have any (375 total, 0 in "BCSC ·" questions).
  Extracted from the source's inline base64 straight to review-questions/img/<hash>.jpg
  (never written inline) — same content-hash-dedup convention as bcsc-qbank/img/.
"""
import json, re, os, hashlib

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC_PATH = os.path.expanduser(
    "~/Documents/Cowork/Reviewers/Ophtho_QBank_BCSC_Review_Desktop.html")
TEMPLATE_PATH = os.path.join(ROOT, "bcsc-qbank", "Cataract.html")

REVIEW_DIR = os.path.join(ROOT, "review-questions")
EOV_DIR = os.path.join(ROOT, "bcsc-eov")
REVIEW_IMG_DIR = os.path.join(REVIEW_DIR, "img")

# (source "section" value, display label, storage-key slug, filename)
REVIEW_SECTIONS = [
    ("Review Q · Fundamentals", "Fundamentals", "fundamentals", "Fundamentals.html"),
    ("Review Q · Embryology and Anatomy", "Embryology and Anatomy", "embryology-anatomy", "EmbryologyAnatomy.html"),
    ("Review Q · Optics", "Optics", "optics", "Optics.html"),
    ("Review Q · Neuro-Ophthalmology", "Neuro-Ophthalmology", "neuro", "Neuro.html"),
    ("Review Q · Pediatrics and Strabismus", "Pediatrics and Strabismus", "peds", "Peds.html"),
    ("Review Q · Oculoplastics, Lacrimal & Orbit", "Oculoplastics, Lacrimal & Orbit", "oculoplastics", "Oculoplastics.html"),
    ("Review Q · Pathology & Tumors", "Pathology & Tumors", "pathology", "Pathology.html"),
    ("Review Q · Uveitis", "Uveitis", "uveitis", "Uveitis.html"),
    ("Review Q · Glaucoma", "Glaucoma", "glaucoma", "Glaucoma.html"),
    ("Review Q · Cornea & External Disease", "Cornea & External Disease", "cornea", "Cornea.html"),
    ("Review Q · Lens and Cataract", "Lens and Cataract", "cataract", "Cataract.html"),
    ("Review Q · Retina and Vitreous", "Retina and Vitreous", "retina", "Retina.html"),
]

# (source "section" value, display label, storage-key slug, filename) — filenames match
# bcsc-qbank/'s own naming for the same subspecialty, for consistency/predictability.
EOV_SECTIONS = [
    ("BCSC · Update on General Medicine", "Update on General Medicine", "general", "General.html"),
    ("BCSC · Fundamentals & Principles of Ophthalmology", "Fundamentals & Principles of Ophthalmology", "fundamentals", "Fundamentals.html"),
    ("BCSC · Clinical Optics & Vision Rehab", "Clinical Optics & Vision Rehab", "optics", "Optics.html"),
    ("BCSC · Ophthalmic Pathology & Intraocular Tumors", "Ophthalmic Pathology & Intraocular Tumors", "pathology", "Pathology.html"),
    ("BCSC · Neuro-Ophthalmology", "Neuro-Ophthalmology", "neuro", "Neuro.html"),
    ("BCSC · Pediatric Ophthalmology & Strabismus", "Pediatric Ophthalmology & Strabismus", "peds", "Peds.html"),
    ("BCSC · Oculofacial Plastic & Orbital Surgery", "Oculofacial Plastic & Orbital Surgery", "plastics", "Plastics.html"),
    ("BCSC · External Disease & Cornea", "External Disease & Cornea", "cornea", "Cornea.html"),
    ("BCSC · Uveitis & Ocular Inflammation", "Uveitis & Ocular Inflammation", "uveitis", "Uveitis.html"),
    ("BCSC · Glaucoma", "Glaucoma", "glaucoma", "Glaucoma.html"),
    ("BCSC · Lens & Cataract", "Lens & Cataract", "cataract", "Cataract.html"),
    ("BCSC · Retina & Vitreous", "Retina & Vitreous", "retina", "Retina.html"),
    ("BCSC · Refractive Surgery", "Refractive Surgery", "refractive", "Refractive.html"),
]

EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}


def load_template():
    tpl = open(TEMPLATE_PATH, encoding="utf-8").read()
    head_end = tpl.find('<div id="staticApp"')
    jsapp_start = tpl.find('<div id="jsApp"')
    assert head_end > 0 and jsapp_start > head_end, "template markers not found"
    head = tpl[:head_end]
    body = tpl[jsapp_start:]

    old_open = '<div id="jsApp" style="display:none">'
    assert body.count(old_open) == 1
    body = body.replace(old_open, '<div id="jsApp">', 1)

    old_toggle = ('try{document.getElementById("jsApp").style.display="block";'
                  'document.getElementById("staticApp").style.display="none";}catch(e){}\n')
    assert body.count(old_toggle) == 1
    body = body.replace(old_toggle, '', 1)

    # figHtml() in the original template resolves q.images entries as *element ids*
    # (document.getElementById(id).src), which only works because the (omitted, see
    # above) staticApp block happened to also host <img id="qimg-N"> anchors for the
    # real app to read filenames off of. Since we never write that block, q.images
    # here holds real img/ filenames directly, so figHtml must build <img> tags from
    # them without any DOM lookup.
    old_figfn = ('function figHtml(ids){ if(!ids||!ids.length) return ""; return \'<div class="fig">\' '
                 '+ ids.map(id=>{const el=document.getElementById(id); return el? '
                 '`<img src="${el.src}" alt="Figure" loading="lazy">` : "";}).join("") + \'</div>\'; }')
    new_figfn = ('function figHtml(files){ if(!files||!files.length) return ""; return \'<div class="fig">\' '
                 '+ files.map(f=>`<img src="img/${f}" alt="Figure" loading="lazy">`).join("") + \'</div>\'; }')
    assert body.count(old_figfn) == 1, "figHtml() template text changed \u2014 update this patch"
    body = body.replace(old_figfn, new_figfn, 1)

    m = re.search(r'<title>(.*?)</title>', head)
    assert m
    old_title = m.group(1)

    old_h1 = 'BCSC Qbank &middot; Lens &amp; Cataract'
    assert body.count(old_h1) == 1

    old_note = ('265 questions in Lens &amp; Cataract. Click an option to lock your answer: '
                'correct turns green, your wrong pick turns red, and the rationale appears. '
                '1 card(s) are image-identification flashcards &mdash; tap to reveal. '
                'Progress is saved until you reset.')
    assert body.count(old_note) == 1

    m2 = re.search(r'localStorage\.setItem\("(bcscanki_[a-z-]+)",JSON\.stringify\(state\)\)', body)
    assert m2
    old_key = m2.group(1)
    assert body.count(old_key) == 6, "expected exactly 6 occurrences of the storage key"

    old_qdata_start = body.find('id="qbankData">') + len('id="qbankData">')
    old_qdata_end = body.find('</script>', old_qdata_start)
    assert old_qdata_start > 0

    # updateHomeLinks() hardcodes this template's OWN subspecialty name into the
    # prog_tag query param it appends to the Home link (harmless — index.html doesn't
    # read prog_tag/prog_ans — but wrong/misleading if left as "Cataract" on every page
    # built from this template). Swap it per-page below.
    old_progtag = 'prog_tag","Cataract"'
    assert body.count(old_progtag) == 1

    return {
        "head": head, "body": body,
        "old_title": old_title, "old_h1": old_h1, "old_note": old_note,
        "old_key": old_key, "old_progtag": old_progtag, "qdata_span": (old_qdata_start, old_qdata_end),
    }


def extract_images(qbank_html, img_dir, wanted_ids):
    """qimg-N id -> filename written into img_dir (deduped by content hash).
    Only decodes ids actually referenced by `wanted_ids` (skips the unrelated ones)."""
    os.makedirs(img_dir, exist_ok=True)
    out = {}
    for iid, mime, b64 in re.findall(
            r'<img id="(qimg-\d+)"[^>]*? src="data:([^;]+);base64,([^"]*)"', qbank_html):
        if iid not in wanted_ids:
            continue
        raw = __import__("base64").b64decode(b64)
        name = hashlib.sha256(raw).hexdigest()[:12] + EXT.get(mime, ".jpg")
        path = os.path.join(img_dir, name)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(raw)
        out[iid] = name
    return out


def write_pool_json(entries_dir, fname, section_label, key, html_file, img_base, questions):
    """Write a Quiz.html-compatible data/<Section>.json pool file (same shape as
    bcsc-qbank/data/*.json). All questions go in the pool (unlike the older BCSC
    extractor, image questions are NOT excluded — Quiz.html can render them via
    imgBase). Returns the manifest entry."""
    data_dir = os.path.join(entries_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    pool = [{"id": q["id"], "q": q["q"], "options": q["options"], "answer": q["answer"],
             "rationale": q["rationale"], "ref": q.get("ref", ""),
             "images": q.get("images", []), "ratImages": q.get("ratImages", [])}
            for q in questions]
    answers = {str(q["id"]): q["answer"] for q in questions}
    folder_name = os.path.basename(entries_dir.rstrip("/"))
    out = {"section": section_label, "key": key, "file": f"{folder_name}/{html_file}",
           "imgBase": img_base, "pool": pool, "answers": answers}
    jname = html_file.replace(".html", ".json")
    with open(os.path.join(data_dir, jname), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    return {"name": section_label, "file": f"{folder_name}/{html_file}",
            "json": f"../{folder_name}/data/{jname}", "key": key, "poolCount": len(pool)}


def build_page(tpl, out_path, title, h1, note_html, storage_key, questions, h1_plain=None, folder_depth_home="../index.html"):
    if h1_plain is None:
        h1_plain = title
    body = tpl["body"]
    body = body[:tpl["qdata_span"][0]] + json.dumps(questions, ensure_ascii=False) + body[tpl["qdata_span"][1]:]
    body = body.replace(tpl["old_h1"], h1, 1)
    body = body.replace(tpl["old_note"], note_html, 1)
    body = body.replace(tpl["old_key"], storage_key)  # all 6 occurrences, same suffix shapes
    body = body.replace(tpl["old_progtag"], 'prog_tag",' + json.dumps(h1_plain), 1)
    head = tpl["head"].replace(tpl["old_title"], title, 1)
    html = head + body
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return len(html)


def main():
    tpl = load_template()
    src = open(SRC_PATH, encoding="utf-8", errors="ignore").read()
    i = src.find('id="qbankData">') + len('id="qbankData">')
    j = src.find('</script>', i)
    all_q = json.loads(src[i:j])
    print(f"source: {len(all_q)} questions total")

    # ---------------- Review Questions in Ophthalmology (12 files) ----------------
    review_manifest = []
    review_quiz_manifest = []
    for src_section, label, slug, fname in REVIEW_SECTIONS:
        qs = [q for q in all_q if q["section"] == src_section]
        assert qs, f"no questions found for {src_section!r}"
        wanted_ids = {q["img"] for q in qs if q.get("img")}
        imgmap = extract_images(src, REVIEW_IMG_DIR, wanted_ids) if wanted_ids else {}

        entries = []
        for q in qs:
            e = {
                "id": q["id"], "section": label, "type": "mcq", "q": q["q"],
                "options": q["options"], "answer": q["answer"],
                "rationale": q["rationale"], "ref": q.get("ref", ""),
                "images": [imgmap[q["img"]]] if q.get("img") and q["img"] in imgmap else [],
                "ratImages": [],
            }
            entries.append(e)

        key = "reviewq_" + slug
        n = len(entries)
        note = (f'{n} questions in {label}. Click an option to lock your answer: correct turns '
                f'green, your wrong pick turns red, and the rationale appears. '
                f'Progress is saved until you reset.')
        out_path = os.path.join(REVIEW_DIR, fname)
        size = build_page(tpl, out_path, f"Review Questions · {label}",
                           f"Review Questions &middot; {label}", note, key, entries)
        review_manifest.append({"label": label, "file": fname, "key": key, "count": n})
        review_quiz_manifest.append(write_pool_json(
            REVIEW_DIR, fname, label, key, fname, "../review-questions/img/", entries))
        print(f"review-questions/{fname}: {n} questions, {size/1024:.0f} KB, key={key}")

    # ---------------- BCSC End-of-Volume Quizzes (13 subspecialty files) ----------------
    eov_manifest = []
    eov_quiz_manifest = []
    for src_section, label, slug, fname in EOV_SECTIONS:
        qs = [q for q in all_q if q["section"] == src_section]
        assert qs, f"no questions found for {src_section!r}"
        entries = []
        for q in qs:
            entries.append({
                "id": q["id"], "section": label, "type": "mcq", "q": q["q"],
                "options": q["options"], "answer": q["answer"],
                "rationale": q["rationale"], "ref": q.get("ref", ""),
                "images": [], "ratImages": [],
            })
        key = "bcsceov_" + slug
        n = len(entries)
        note = (f'{n} end-of-volume self-assessment questions in {label} — a separate '
                f'question set from the main BCSC Question Bank above. Click an option to '
                f'lock your answer: correct turns green, your wrong pick turns red, and the '
                f'rationale appears. Progress is saved until you reset.')
        out_path = os.path.join(EOV_DIR, fname)
        size = build_page(tpl, out_path, f"BCSC End-of-Volume · {label}",
                           f"BCSC End-of-Volume &middot; {label}", note, key, entries)
        eov_manifest.append({"label": label, "file": fname, "key": key, "count": n})
        eov_quiz_manifest.append(write_pool_json(
            EOV_DIR, fname, label, key, fname, "../bcsc-eov/img/", entries))
        print(f"bcsc-eov/{fname}: {n} questions, {size/1024:.0f} KB, key={key}")

    with open(os.path.join(REVIEW_DIR, "data", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"sections": review_quiz_manifest}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(EOV_DIR, "data", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"sections": eov_quiz_manifest}, f, ensure_ascii=False, indent=1)
    print("Wrote review-questions/data/manifest.json and bcsc-eov/data/manifest.json "
          "(Exam Mode pool data, fetched by bcsc-qbank/Quiz.html).")

    with open(os.path.join(ROOT, "tools", "_import_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({
            "review_questions": {"dir": "review-questions", "sections": review_manifest,
                                  "total": sum(m["count"] for m in review_manifest)},
            "bcsc_eov": {"dir": "bcsc-eov", "sections": eov_manifest,
                         "total": sum(m["count"] for m in eov_manifest)},
        }, f, indent=1)
    print("Wrote tools/_import_manifest.json (used to generate the landing-page config).")


if __name__ == "__main__":
    main()
