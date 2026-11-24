#!/usr/bin/env python3
"""Build the public Said & Done Ledger page from the vault's source-of-record file.

The vault note stays the only place the Ledger is edited. This script turns it into
a static site in ./docs, ready for GitHub Pages at ledger.protopia.africa.

    python3 build.py            # build docs/ from the vault file
    python3 build.py --check    # build, then exit 1 if the public-hygiene lint finds anything

Answer blocks and the FAQ come from answers.py, checked against the note on every build.

What it does to the note on the way out:
  * keeps everything from "## 1." onwards, minus the "Update protocol" section and any
    block wrapped in <!-- public:skip --> ... <!-- /public:skip -->
  * turns [[wikilinks]] into links to the published Substack post (from each note's `url:`)
  * keeps ~~struck~~ superseded figures visible as <del>, so every delta stays on the page
  * writes index.html plus a frozen copy at v/<version>/ so old versions keep a stable URL
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension

import answers

HERE = Path(__file__).resolve().parent
# Where the vault's Africa's Protopia folder lives. Kept out of the public repo:
# set PROTOPIA_PROJECT, or put the path in .project-path (git-ignored).
_local = HERE / ".project-path"
PROJECT = Path(os.environ.get("PROTOPIA_PROJECT") or (_local.read_text().strip() if _local.exists() else ""))
if not PROJECT.is_dir():
    sys.exit("Set PROTOPIA_PROJECT or write the vault project path into .project-path")
SOURCE = PROJECT / "Research" / "The Said & Done Ledger.md"
SITE = HERE / "docs"  # GitHub Pages serves main:/docs
DOMAIN = "ledger.protopia.africa"
LEDGER_URL = f"https://{DOMAIN}/"

# The one place the Substack address lives. When the custom domain is switched on,
# change this to "https://protopia.africa" and rebuild: every Substack link on the page,
# including old africasprotopia.substack.com links in the note, follows it.
SUBSTACK_URL = "https://africasprotopia.substack.com"
SUBSTACK_OLD = "https://africasprotopia.substack.com"  # links in the note use this; rewritten to SUBSTACK_URL

# Structured data (JSON-LD) identity. The @ids are permanent labels, not pages to visit:
# never change them, or search engines lose the link between old and new versions.
ORG_ID = f"{LEDGER_URL}#organization"
DATASET_ID = f"{LEDGER_URL}#dataset"
PERSON_ID = f"{LEDGER_URL}#ivan-irakoze"
FAQ_ID = f"{LEDGER_URL}#faq"
PERSON_NAME = "Ivan Irakoze"
PERSON_PROFILE = "https://substack.com/@ivanirakoze"  # his Substack profile, as linked on the About page
PERSON_LINKEDIN = "https://www.linkedin.com/in/ivan-irakoze/"  # confirmed by Ivan, 2026-11-24
# The one-line description of Africa's Protopia used in the structured data (chosen by Ivan, 2026-11-24).
PUBLICATION_DESCRIPTOR = (
    "Africa's Protopia follows sovereign African AI from announcement to deployment, "
    "and the people turning African opportunities into working systems."
)

SKIP_SECTIONS = {"Update protocol", "Change history"}  # vault-only

# Phrases that belong in the vault but not on a public page. Each hit is a line to fix
# in the vault note (reword, add a public source, or wrap in public:skip).
LINT = [
    (r"Investment Landscape|Field Guide|Founders Atlas", "cites an internal research note, not a public source"),
    (r"\bIvan\b", "names Ivan inside the data"),
    (r"\bW\d{1,2}\b", "internal week number"),
    (r"\bvault\b", "mentions the vault"),
    (r"\[\[", "wikilink left unresolved"),
]


# ---------- vault helpers ----------

def frontmatter_url(path: Path):
    """Return the `url:` value from a note's YAML frontmatter, or None."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    u = re.search(r"^url:\s*(\S+)", m.group(1), re.M)
    return u.group(1) if u else None


def build_link_map():
    """Map note name -> public URL for every Content/Published note that has one."""
    links = {}
    for folder in ("Published", "Content"):
        for note in (PROJECT / folder).glob("*.md"):
            url = frontmatter_url(note)
            if url:
                links[note.stem] = url
    return links


def resolve_wikilinks(text, links, warnings):
    def swap(m):
        target, alias = m.group(1), m.group(3)
        name = Path(target).name  # [[03 Projects/.../Note|Alias]] -> "Note"
        label = alias or name
        url = links.get(name)
        if url:
            return f"[{label}]({url})"
        warnings.append(f"no public URL for [[{target}]] — rendered as plain text")
        return label
    return re.sub(r"\[\[([^\]|]+?)(\|([^\]]+))?\]\]", swap, text)


def split_note(text):
    """Return (preamble, body) with frontmatter dropped. Body starts at '## 1.'."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    idx = text.find("\n## 1.")
    if idx == -1:
        sys.exit("Could not find '## 1.' in the Ledger note — has the structure changed?")
    return text[:idx], text[idx:]


def drop_sections(body):
    body = re.sub(r"<!-- public:skip -->.*?<!-- /public:skip -->", "", body, flags=re.S)
    parts = re.split(r"(?m)^(?=## )", body)
    keep = [p for p in parts if not any(p.startswith(f"## {s}") for s in SKIP_SECTIONS)]
    return "".join(keep)


def meta_from_preamble(pre):
    version = re.search(r"\*\*Version:\*\*\s*(v[\d.]+)", pre)
    as_of = re.search(r"\*\*Data as of:\*\*\s*(\d{4}-\d{2}-\d{2})", pre)
    rule = re.search(r"(?m)^> \*\*Hard rule\.\*\*(.*)$", pre)
    changelog = re.findall(r"(?m)^\*(v[\d.]+) — (.*)\*$", pre)
    return {
        "version": version.group(1) if version else "v?",
        "as_of": as_of.group(1) if as_of else "",
        "rule": rule.group(1).strip() if rule else "",
        "changelog": changelog,
    }


# ---------- markdown -> html ----------

class TableCards(Treeprocessor):
    """Wrap each table in a scroll box and label every cell, so phones can show rows as cards."""

    def run(self, root):
        for parent in list(root.iter()):
            for i, child in enumerate(list(parent)):
                if child.tag != "table":
                    continue
                heads = ["".join(th.itertext()).strip() for th in child.iter("th")]
                cols = len(heads)
                child.set("class", f"cols-{min(cols, 5)}")
                tbody = child.find("tbody")
                for tr in (tbody if tbody is not None else []):
                    for j, td in enumerate(tr):
                        if j < cols and heads[j]:
                            td.set("data-label", heads[j])
                wrap = ET.Element("div", {"class": "table-wrap"})
                parent.remove(child)
                wrap.append(child)
                parent.insert(i, wrap)


class TableCardsExt(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(TableCards(md), "tablecards", 5)


def to_html(md_text):
    md_text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", md_text, flags=re.S)
    md = markdown.Markdown(
        extensions=["tables", "sane_lists", "toc", TableCardsExt()],
        extension_configs={"toc": {"permalink": "#", "permalink_title": "Link to this section", "toc_depth": "2"}},
    )
    body = md.convert(md_text)
    # open external links in a new tab, safely
    body = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', body)
    return body, md.toc_tokens


# ---------- answer blocks + FAQ (text lives in answers.py) ----------

NUM = re.compile(r"\d+(?:[.,]\d+)*")


def esc(text):
    return html.escape(text, quote=False)


def fill(text, meta):
    return text.format(ledger=f"the Said & Done Ledger {meta['version']}")


def add_answer_blocks(body_html, meta):
    """Put each section's answer block straight under its numbered H2."""
    def put(m):
        text = answers.ANSWER_BLOCKS.get(int(m.group(2)))
        return m.group(1) + (f'\n<p class="answer">{esc(fill(text, meta))}</p>' if text else "")
    return re.sub(r'(<h2 id="[^"]+">(\d+)\. .*?</h2>)', put, body_html, flags=re.S)


def check_answers(meta, public_md):
    """Guard rails for answers.py: right version, 40–60 words, no number the page doesn't carry."""
    problems = []
    if meta["version"] != answers.FOR_VERSION:
        problems.append(f"answers.py was checked against {answers.FOR_VERSION}, the note is now "
                        f"{meta['version']}: re-read every answer and FAQ line, then bump FOR_VERSION")
    on_page = set(NUM.findall(public_md))
    sections = {int(n) for n in re.findall(r"(?m)^## (\d+)\.", public_md)}
    for n in sorted(sections - answers.ANSWER_BLOCKS.keys()):
        problems.append(f"section {n} has no answer block")
    items = [(f"answer §{n}", t, True) for n, t in answers.ANSWER_BLOCKS.items()]
    items += [(f"FAQ '{q[:40]}'", q + " " + a, False) for q, a in answers.FAQ]
    for label, text, is_block in items:
        words = len(fill(text, meta).split())
        if is_block and not 40 <= words <= 60:
            problems.append(f"{label} is {words} words (want 40–60)")
        for num in NUM.findall(text):
            if num not in on_page:
                problems.append(f"{label} uses {num}, which is not in the Ledger note")
    return problems


# ---------- page ----------

def render(meta, body_html, toc_tokens, archived=False):
    v, as_of = meta["version"], meta["as_of"]
    as_of_h = dt.date.fromisoformat(as_of).strftime("%-d %B %Y") if as_of else ""
    canonical = f"https://{DOMAIN}/" if not archived else f"https://{DOMAIN}/v/{v[1:]}/"
    prefix = "../../" if archived else ""

    toc = "\n".join(
        f'<li><a href="#{t["id"]}">{html.escape(t["name"])}</a></li>' for t in toc_tokens
    )
    changelog = "\n".join(
        f"<li><strong>{cv}</strong> — {to_html(text)[0].removeprefix('<p>').removesuffix('</p>')}</li>"
        for cv, text in meta["changelog"]
    )
    changelog_section = (
        '<section id="changelog"><h2>Changelog</h2>'
        "<p>What changed in each version. From v1.0 on, replaced figures stay on the page, struck through, so you can see what changed. Every earlier version also stays readable at its own address.</p>"
        f'<ul class="changelog">{changelog}</ul></section>' if changelog else ""
    )
    changelog_toc = '<li><a href="#changelog">Changelog</a></li>' if changelog else ""
    rule = to_html("**Our rule.** " + meta["rule"])[0] if meta["rule"] else ""
    banner = (
        f'<p class="archived">You are reading <strong>{v}</strong>, an archived version. '
        f'<a href="/">Read the current Ledger</a>.</p>' if archived else ""
    )
    faq = [(q, a) for q, a in answers.FAQ]
    faq_section = (
        '<section id="faq"><h2>Frequently asked questions</h2>'
        + "".join(f"<h3>{esc(q)}</h3>\n<p>{esc(a)}</p>\n" for q, a in faq)
        + "</section>"
    )
    jsonld = {"@context": "https://schema.org", "@graph": [
        {
            "@type": "Organization",
            "@id": ORG_ID,
            "name": "Africa's Protopia",
            "url": SUBSTACK_URL,
            "description": PUBLICATION_DESCRIPTOR,
            "logo": f"{LEDGER_URL}assets/logo.png",
            "sameAs": [SUBSTACK_URL, LEDGER_URL],
        },
        {
            "@type": "Person",
            "@id": PERSON_ID,
            "name": PERSON_NAME,
            "url": PERSON_PROFILE,
            "sameAs": [PERSON_PROFILE] + ([PERSON_LINKEDIN] if PERSON_LINKEDIN else []),
        },
        {
            "@type": "Dataset",
            "@id": DATASET_ID,
            "name": "The Said & Done Ledger",
            "alternateName": "The Said & Done Ledger by Africa's Protopia",
            "description": "What African AI was promised, and what got built: announced vs. deployed capital, "
                           "compute online, startup counts, national AI strategies, and a register of contested "
                           "figures with the reason each pair diverges.",
            "url": canonical,
            "version": v.lstrip("v"),
            "dateModified": as_of,
            "spatialCoverage": "Africa",
            "isAccessibleForFree": True,
            "creator": {"@id": PERSON_ID},
            "publisher": {"@id": ORG_ID},
        },
        {
            "@type": "FAQPage",
            "@id": f"{canonical}#faq",
            "url": canonical,
            "about": {"@id": DATASET_ID},
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq
            ],
        },
    ]}
    # "</" inside a <script> block could end it early; JSON allows "<\/" as the same text.
    jsonld_text = json.dumps(jsonld, ensure_ascii=False, indent=1).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Said &amp; Done Ledger {v} · Africa's Protopia</title>
<meta name="description" content="What African AI was promised, and what got built. A versioned, sourced ledger by Africa's Protopia. {v}, data as of {as_of_h}.">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="The Said &amp; Done Ledger">
<meta property="og:description" content="What African AI was promised, and what got built. {v}, data as of {as_of_h}.">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<link rel="icon" href="{prefix}assets/logo.png">
<link rel="preload" href="{prefix}assets/fonts/DMSerifDisplay-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}assets/ledger.css">
<script type="application/ld+json">
{jsonld_text}
</script>
</head>
<body>
<a class="skip" href="#main">Skip to the Ledger</a>
<header class="masthead">
  <div class="masthead-inner">
    <a class="brand" href="{SUBSTACK_URL}">Africa's Protopia</a>
    <h1>The Said &amp; Done Ledger</h1>
    <p class="dek">What African AI was promised, and what got built.</p>
    <p class="stamp"><span class="ver">{v}</span> <span>Data as of {as_of_h}</span> <span>Updated quarterly</span></p>
    <p class="updated">Last updated <time datetime="{as_of}">{as_of_h}</time></p>
    {banner}
  </div>
</header>
<div class="layout">
  <nav class="toc" aria-label="Sections">
    <p class="toc-title">Sections</p>
    <ol>{toc}<li><a href="#faq">Frequently asked questions</a></li>{changelog_toc}</ol>
    <a class="subscribe" href="{SUBSTACK_URL}/subscribe">Get each update by email</a>
  </nav>
  <main id="main">
    <div class="rule">{rule}</div>
    {add_answer_blocks(body_html, meta)}
    {faq_section}
    {changelog_section}
  </main>
</div>
<footer>
  <p>The Said &amp; Done Ledger is kept by <a href="{SUBSTACK_URL}">Africa's Protopia</a>.
  Compiled by <a href="{PERSON_PROFILE}">{PERSON_NAME}</a>.
  Spotted an error or a newer figure? Write to <a href="mailto:hello@protopia.africa">hello@protopia.africa</a>.</p>
  <p class="small">Built {dt.date.today().isoformat()} · {v}</p>
</footer>
</body>
</html>
"""


def unsourced_rows(md_text):
    """Data rows with no link of their own, in tables with no 'Source' caption just above.

    A table counts as sourced as a whole when one of the three non-blank lines before
    its header says "Source" and carries a link. Otherwise each row needs its own link.
    """
    lines = md_text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if not lines[i].startswith("|"):
            i += 1
            continue
        before = [ln for ln in lines[max(0, i - 6):i] if ln.strip()][-3:]
        captioned = any("Source" in ln and "](http" in ln for ln in before)
        j = i + 2  # skip header and |---| rule
        while j < len(lines) and lines[j].startswith("|"):
            withdrawn = lines[j].startswith("| ~~")  # struck rows stay visible on purpose
            if not captioned and not withdrawn and "](http" not in lines[j]:
                out.append(lines[j].strip()[:110])
            j += 1
        i = j
    return out


def lint(public_md):
    hits = []
    for n, line in enumerate(public_md.splitlines(), 1):
        for pattern, why in LINT:
            if re.search(pattern, line):
                hits.append((why, line.strip()[:140]))
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--check", action="store_true", help="exit 1 if the hygiene lint finds anything")
    args = ap.parse_args()

    warnings = []
    pre, body = split_note(args.source.read_text(encoding="utf-8"))
    meta = meta_from_preamble(pre)
    links = build_link_map()
    body = resolve_wikilinks(drop_sections(body), links, warnings)
    # Week numbers ("W9 Ledger Entry") are vault bookkeeping; readers get the title only.
    # Public changelog starts at v1.0, the first public version; pre-launch entries stay in the vault.
    meta["changelog"] = [(v, re.sub(r"^W\d{1,2} ", "", resolve_wikilinks(t, links, warnings)))
                         for v, t in meta["changelog"] if int(v.lstrip("v").split(".")[0]) >= 1]
    body = re.sub(r"(?m)^---\s*$", "", body)  # section rules come from CSS instead
    # Point every Substack link at the current address (see SUBSTACK_URL).
    body = body.replace(SUBSTACK_OLD, SUBSTACK_URL)
    meta["changelog"] = [(v, t.replace(SUBSTACK_OLD, SUBSTACK_URL)) for v, t in meta["changelog"]]

    body_html, toc_tokens = to_html(body)

    if SITE.exists():
        keep_archive = SITE / "v"
        tmp = HERE / ".v-keep"
        if keep_archive.exists():
            shutil.move(str(keep_archive), tmp)
        shutil.rmtree(SITE)
        SITE.mkdir()
        if tmp.exists():
            shutil.move(str(tmp), SITE / "v")
    else:
        SITE.mkdir()
    shutil.copytree(HERE / "assets", SITE / "assets")
    (SITE / "CNAME").write_text(DOMAIN + "\n")
    (SITE / ".nojekyll").write_text("")
    (SITE / "index.html").write_text(render(meta, body_html, toc_tokens), encoding="utf-8")
    # Freeze public versions only (v1.0 is the first); pre-launch drafts get no archive URL.
    if int(meta["version"].lstrip("v").split(".")[0] or 0) >= 1:
        arch = SITE / "v" / meta["version"].lstrip("v")
        arch.mkdir(parents=True, exist_ok=True)
        (arch / "index.html").write_text(render(meta, body_html, toc_tokens, archived=True), encoding="utf-8")

    extra = list(answers.ANSWER_BLOCKS.values()) + [q + " " + a for q, a in answers.FAQ]
    hits = lint(body + "\n".join(t for _, t in meta["changelog"]) + "\n" + "\n".join(extra))
    answer_problems = check_answers(meta, body)
    print(f"Built {meta['version']} (data as of {meta['as_of']}) -> {SITE}/index.html")
    print(f"  {len(answers.ANSWER_BLOCKS)} answer blocks, {len(answers.FAQ)} FAQ entries; "
          f"{len(answer_problems)} problems:")
    for p in answer_problems:
        print("   !", p)
    unsourced = unsourced_rows(body)
    print(f"  {len(unsourced)} table rows carry no source link:")
    for ln in unsourced:
        print("   ·", ln)
    for w in warnings:
        print("  WARN", w)
    if hits:
        print(f"  {len(hits)} public-hygiene hits (fix in the vault note):")
        for why, line in hits:
            print(f"   - {why}: {line}")
    if args.check and (hits or warnings or unsourced or answer_problems):
        sys.exit(1)


if __name__ == "__main__":
    main()
