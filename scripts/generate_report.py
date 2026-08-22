"""
scripts/generate_report.py

Generates a single self-contained HTML report from downloaded impact
hypothesis JSON files. This stands in for the Compliance Review Portal in
the target architecture (see the "Two Loops" diagram, Compliance Decision
step) — a human-readable view of what the pipeline proposed, with nothing
here confirmed until a Compliance Analyst says so.

Usage:
    az storage blob download-batch --account-name <acct> \\
        --source impact-hypotheses --destination ./hypotheses --auth-mode login
    python scripts/generate_report.py ./hypotheses --out out/compliance_review.html

The Confirm / Modify / Reject / Request investigation buttons on each case
change the case's appearance in the browser for demo purposes only — they
write nothing anywhere. A real deployment persists that decision to GRC
(ADR-3, ADR-7).
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

CLASSIFICATION_META = {
    "potential_impact": {"label": "Potential Impact", "css": "amber"},
    "no_impact_proposed": {"label": "No Impact Proposed", "css": "green"},
    "insufficient_evidence": {"label": "Insufficient Evidence", "css": "violet"},
}


def load_hypotheses(folder: Path) -> list[dict]:
    hypotheses = []
    for path in sorted(folder.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            hypotheses.append(json.load(f))
    return hypotheses


def _esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def _internal_citations(citations: dict) -> list[str]:
    """Handles both the current single-string internal citation and a
    possible future list form (citations.internal_citations), so this
    report doesn't need to change if that polish item lands later."""
    if citations.get("internal_citations"):
        return [
            f"{c.get('document_id', '')}, {c.get('section', '')}"
            for c in citations["internal_citations"]
        ]
    if citations.get("internal"):
        return [citations["internal"]]
    return []


def render_exhibit(index: int, fragment: dict) -> str:
    letter = chr(ord("A") + index)
    return f"""
    <details class="exhibit">
      <summary>
        <span class="exhibit-tag">Exhibit {letter}</span>
        <span class="exhibit-title">{_esc(fragment.get('policy_title'))}</span>
        <span class="exhibit-section">{_esc(fragment.get('section'))}</span>
      </summary>
      <p class="exhibit-excerpt">{_esc(fragment.get('excerpt'))}</p>
      <p class="exhibit-meta">Ranking signal: {fragment.get('relevance_score', 0):.3f} — a retrieval ranking score, not a percentage of relevance.</p>
    </details>
    """


def render_case(hypothesis: dict) -> str:
    classification = hypothesis.get("classification", "insufficient_evidence")
    meta = CLASSIFICATION_META.get(classification, CLASSIFICATION_META["insufficient_evidence"])
    citations = hypothesis.get("citations", {}) or {}
    internal_citations = _internal_citations(citations)
    fragments = hypothesis.get("retrieved_fragments", []) or []
    confidence = hypothesis.get("confidence")
    requirement_text = hypothesis.get("requirement_text")

    exhibits_html = "".join(render_exhibit(i, f) for i, f in enumerate(fragments)) or (
        '<p class="no-exhibits">No policy fragments were retrieved for this requirement.</p>'
    )

    internal_html = (
        "".join(f"<li>{_esc(c)}</li>" for c in internal_citations)
        or '<li class="none">No internal policy citation — no matching evidence found.</li>'
    )

    if requirement_text:
        requirement_line = f'<p class="case-requirement">{_esc(requirement_text)}</p>'
    else:
        requirement_line = (
            '<p class="case-requirement case-requirement--missing">'
            "Requirement text not captured in this run — only the ID is available below.</p>"
        )

    confidence_pct = f"{confidence * 100:.0f}" if isinstance(confidence, (int, float)) else None
    signal_width = f"{confidence_pct}%" if confidence_pct is not None else "0%"
    signal_display = f"{confidence_pct}%" if confidence_pct is not None else "—"

    timestamp = _esc(hypothesis.get("timestamp", ""))[:19].replace("T", " ")

    return f"""
    <article class="case" data-status="pending">
      <header class="case-head">
        <div class="case-id">
          <span class="case-number">{_esc(hypothesis.get('requirement_id'))}</span>
          <span class="case-citation">{_esc(citations.get('external', '—'))}</span>
        </div>
        <div class="stamp stamp--{meta['css']}">{meta['label']}</div>
      </header>

      {requirement_line}

      <section class="case-block">
        <h3>Findings</h3>
        <p class="case-reasoning">{_esc(hypothesis.get('reasoning'))}</p>
      </section>

      <section class="case-block">
        <h3>Internal policy citation</h3>
        <ul class="citation-list">{internal_html}</ul>
      </section>

      <section class="case-block">
        <h3>Evidence exhibits</h3>
        {exhibits_html}
      </section>

      <section class="case-meta-row">
        <div class="signal">
          <span class="signal-label">Model-reported signal</span>
          <div class="signal-bar"><div class="signal-fill" style="width:{signal_width}"></div></div>
          <span class="signal-value">{signal_display}</span>
          <span class="signal-note">Reflects the model's own certainty in its reasoning — not a calibrated probability of actual impact.</span>
        </div>
        <div class="model-tag">{_esc(hypothesis.get('model_version'))} · {timestamp}</div>
      </section>

      <footer class="disposition">
        <span class="disposition-flag">Requires human confirmation</span>
        <div class="disposition-actions">
          <button type="button" class="btn btn--confirm" data-action="Confirmed">Confirm</button>
          <button type="button" class="btn btn--modify" data-action="Modified">Modify</button>
          <button type="button" class="btn btn--reject" data-action="Rejected">Reject</button>
          <button type="button" class="btn btn--investigate" data-action="Investigation requested">Request investigation</button>
        </div>
        <span class="disposition-status"></span>
      </footer>
    </article>
    """


def render_summary(hypotheses: list[dict]) -> str:
    counts = {"potential_impact": 0, "no_impact_proposed": 0, "insufficient_evidence": 0}
    for h in hypotheses:
        c = h.get("classification")
        if c in counts:
            counts[c] += 1

    return f"""
    <div class="summary-grid">
      <div class="summary-item">
        <span class="summary-number">{len(hypotheses)}</span>
        <span class="summary-label">Requirements reviewed</span>
      </div>
      <div class="summary-item summary-item--amber">
        <span class="summary-number">{counts['potential_impact']}</span>
        <span class="summary-label">Potential impact</span>
      </div>
      <div class="summary-item summary-item--green">
        <span class="summary-number">{counts['no_impact_proposed']}</span>
        <span class="summary-label">No impact proposed</span>
      </div>
      <div class="summary-item summary-item--violet">
        <span class="summary-number">{counts['insufficient_evidence']}</span>
        <span class="summary-label">Insufficient evidence</span>
      </div>
    </div>
    """


def build_page(hypotheses: list[dict], source_label: str) -> str:
    cases_html = "".join(render_case(h) for h in hypotheses)
    summary_html = render_summary(hypotheses)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    page = _PAGE_TEMPLATE
    page = page.replace("__SOURCE_LABEL__", html.escape(source_label))
    page = page.replace("__SUMMARY__", summary_html)
    page = page.replace("__CASES__", cases_html)
    page = page.replace("__GENERATED_AT__", generated_at)
    page = page.replace("__COUNT__", str(len(hypotheses)))
    return page


_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Compliance Review — Regulatory Impact Docket</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --paper: #F3F5F7;
  --paper-raised: #FFFFFF;
  --ink: #1A2332;
  --ink-soft: #4B5768;
  --rule: #C7CFD9;
  --accent: #0F4C81;
  --amber: #B45309;
  --amber-bg: #FBEBD8;
  --green: #166534;
  --green-bg: #E1F0E5;
  --violet: #6D28D9;
  --violet-bg: #ECE6FB;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  line-height: 1.5;
}

.page { max-width: 880px; margin: 0 auto; padding: 48px 24px 96px; }

.masthead { border-bottom: 2px solid var(--ink); padding-bottom: 28px; margin-bottom: 32px; }

.masthead-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 8px;
}

.masthead h1 {
  font-family: 'Newsreader', Georgia, serif;
  font-weight: 500;
  font-size: 40px;
  line-height: 1.15;
  margin: 0 0 8px;
  letter-spacing: -0.01em;
}

.masthead-sub { color: var(--ink-soft); font-size: 15px; margin: 0; max-width: 62ch; }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--rule);
  border: 1px solid var(--rule);
  margin: 32px 0 40px;
}

.summary-item { background: var(--paper-raised); padding: 18px 16px; display: flex; flex-direction: column; gap: 4px; }
.summary-number { font-family: 'Newsreader', serif; font-size: 32px; font-weight: 500; }
.summary-label { font-size: 12px; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 0.06em; }
.summary-item--amber .summary-number { color: var(--amber); }
.summary-item--green .summary-number { color: var(--green); }
.summary-item--violet .summary-number { color: var(--violet); }

.case {
  background: var(--paper-raised);
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 28px 28px 20px;
  margin-bottom: 24px;
  position: relative;
}

.case-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 16px; }
.case-id { display: flex; flex-direction: column; gap: 2px; }
.case-number { font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: var(--ink-soft); }
.case-citation { font-family: 'IBM Plex Mono', monospace; font-size: 15px; font-weight: 500; color: var(--accent); }

.stamp {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 7px 12px;
  border: 2px solid currentColor;
  border-radius: 2px;
  transform: rotate(-2deg);
  white-space: nowrap;
}
.stamp--amber { color: var(--amber); background: var(--amber-bg); }
.stamp--green { color: var(--green); background: var(--green-bg); }
.stamp--violet { color: var(--violet); background: var(--violet-bg); }

.case-requirement {
  font-family: 'Newsreader', serif;
  font-size: 18px;
  line-height: 1.5;
  margin: 0 0 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--rule);
}
.case-requirement--missing { font-family: 'IBM Plex Sans', sans-serif; font-size: 13px; font-style: italic; color: var(--ink-soft); }

.case-block { margin-bottom: 20px; }
.case-block h3 { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-soft); margin: 0 0 8px; }
.case-reasoning { font-size: 14.5px; margin: 0; }

.citation-list { list-style: none; margin: 0; padding: 0; font-family: 'IBM Plex Mono', monospace; font-size: 13px; }
.citation-list li { padding: 6px 0; border-bottom: 1px dashed var(--rule); }
.citation-list li:last-child { border-bottom: none; }
.citation-list li.none { font-style: italic; color: var(--ink-soft); font-family: 'IBM Plex Sans', sans-serif; }

.exhibit { border: 1px solid var(--rule); border-radius: 2px; margin-bottom: 8px; }
.exhibit summary { cursor: pointer; padding: 10px 14px; display: flex; gap: 10px; align-items: baseline; font-size: 13px; list-style: none; }
.exhibit summary::-webkit-details-marker { display: none; }
.exhibit summary::before { content: "▸"; color: var(--accent); margin-right: 2px; }
.exhibit[open] summary::before { content: "▾"; }
.exhibit-tag { font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: var(--accent); }
.exhibit-title { font-weight: 500; }
.exhibit-section { color: var(--ink-soft); }
.exhibit-excerpt { margin: 0; padding: 0 14px 14px 30px; font-size: 13.5px; color: var(--ink-soft); white-space: pre-line; }
.exhibit-meta { margin: 0; padding: 0 14px 12px 30px; font-size: 11px; color: var(--ink-soft); font-style: italic; }
.no-exhibits { font-size: 13px; font-style: italic; color: var(--ink-soft); }

.case-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--rule);
  margin-bottom: 16px;
}
.signal { flex: 1; max-width: 420px; }
.signal-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-soft); display: block; margin-bottom: 4px; }
.signal-bar { height: 6px; background: var(--rule); border-radius: 3px; overflow: hidden; margin-bottom: 4px; }
.signal-fill { height: 100%; background: var(--accent); }
.signal-value { font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600; }
.signal-note { display: block; font-size: 11px; color: var(--ink-soft); margin-top: 4px; max-width: 40ch; }
.model-tag { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--ink-soft); white-space: nowrap; }

.disposition { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding-top: 4px; }
.disposition-flag {
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--accent); background: #E8F0F7; padding: 5px 10px; border-radius: 2px;
}
.disposition-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn {
  font-family: 'IBM Plex Sans', sans-serif; font-size: 12.5px; font-weight: 600;
  border: 1px solid var(--rule); background: var(--paper-raised); color: var(--ink);
  padding: 8px 14px; border-radius: 2px; cursor: pointer; transition: all 0.15s ease;
}
.btn:hover { border-color: var(--ink); }
.btn--confirm:hover { background: var(--green); border-color: var(--green); color: #fff; }
.btn--reject:hover { background: var(--amber); border-color: var(--amber); color: #fff; }
.btn--modify:hover, .btn--investigate:hover { background: var(--accent); border-color: var(--accent); color: #fff; }
.disposition-status { font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600; color: var(--accent); }

.case[data-status="Confirmed"] { border-left: 4px solid var(--green); }
.case[data-status="Rejected"] { border-left: 4px solid var(--amber); }
.case[data-status="Modified"] { border-left: 4px solid var(--accent); }
.case[data-status="Investigation requested"] { border-left: 4px solid var(--violet); }

.footnote { margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--rule); font-size: 12px; color: var(--ink-soft); font-family: 'IBM Plex Mono', monospace; }

@media (max-width: 640px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
  .case-head { flex-direction: column; }
  .case-meta-row { flex-direction: column; align-items: flex-start; }
}

:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<div class="page">
  <div class="masthead">
    <p class="masthead-eyebrow">Regulatory Change Impact Analysis — Compliance Docket</p>
    <h1>Impact Review: __SOURCE_LABEL__</h1>
    <p class="masthead-sub">Every hypothesis below was proposed by the pipeline, not decided by it. Nothing here is a confirmed regulatory position until a Compliance Analyst confirms, modifies, or rejects it — see the disposition line at the foot of each case.</p>
  </div>

  __SUMMARY__

  __CASES__

  <p class="footnote">Generated __GENERATED_AT__ from __COUNT__ file(s). Confirm / Modify / Reject / Request investigation are demo interactions only — a real deployment writes the confirmed decision to GRC.</p>
</div>
<script>
document.querySelectorAll('.btn').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var card = btn.closest('.case');
    var action = btn.dataset.action;
    card.dataset.status = action;
    card.querySelector('.disposition-status').textContent = action + ' (demo only — not saved)';
  });
});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_folder", type=Path, help="Folder of downloaded impact-hypotheses JSON files")
    parser.add_argument("--out", type=Path, default=Path("out/compliance_review.html"))
    parser.add_argument("--source-label", default="EU AI Act, Article 9")
    args = parser.parse_args()

    hypotheses = load_hypotheses(args.input_folder)
    if not hypotheses:
        raise SystemExit(f"No .json files found in {args.input_folder}")

    hypotheses.sort(key=lambda h: h.get("requirement_id", ""))

    page = build_page(hypotheses, args.source_label)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print(f"Wrote {args.out} ({len(hypotheses)} case(s))")


if __name__ == "__main__":
    main()
