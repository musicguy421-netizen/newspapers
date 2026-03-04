"""
export_html.py – Convert search_results.json into a readable HTML report.

Usage:
    python export_html.py                          # reads search_results.json
    python export_html.py --input search_results.json --output report.html
"""

import argparse
import json
import os
from html import escape


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Article Search Results</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f4f6f9;
      color: #222;
      padding: 2rem;
    }}

    h1 {{
      font-size: 1.8rem;
      margin-bottom: 0.25rem;
      color: #1a1a2e;
    }}

    .meta {{
      font-size: 0.85rem;
      color: #666;
      margin-bottom: 2rem;
    }}

    .keyword-section {{
      margin-bottom: 3rem;
    }}

    .keyword-heading {{
      display: inline-block;
      background: #1a1a2e;
      color: #fff;
      font-size: 1rem;
      font-weight: 600;
      padding: 0.4rem 1rem;
      border-radius: 4px;
      margin-bottom: 1rem;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      font-size: 0.9rem;
    }}

    thead {{
      background: #eef0f5;
    }}

    th {{
      text-align: left;
      padding: 0.75rem 1rem;
      font-weight: 600;
      color: #444;
      border-bottom: 2px solid #dde1ea;
      white-space: nowrap;
    }}

    td {{
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #eee;
      vertical-align: top;
    }}

    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #fafbfd; }}

    .score {{
      font-weight: 700;
      color: #2d6a4f;
      white-space: nowrap;
    }}

    .score.high   {{ color: #1b7a4e; }}
    .score.medium {{ color: #b07d1b; }}
    .score.low    {{ color: #c0392b; }}

    .source-tag {{
      display: inline-block;
      background: #e8eaf6;
      color: #3949ab;
      font-size: 0.75rem;
      padding: 0.2rem 0.5rem;
      border-radius: 3px;
      white-space: nowrap;
    }}

    .title a {{
      color: #1a1a2e;
      text-decoration: none;
      font-weight: 500;
    }}

    .title a:hover {{ text-decoration: underline; color: #3949ab; }}

    .summary {{ color: #555; line-height: 1.5; }}

    .date {{ white-space: nowrap; color: #888; font-size: 0.82rem; }}

    .no-summary {{ color: #bbb; font-style: italic; }}
  </style>
</head>
<body>

  <h1>Article Search Results</h1>
  <p class="meta">
    Generated: {generated_at} &nbsp;|&nbsp;
    Articles indexed: {total_indexed} &nbsp;|&nbsp;
    Top {top_n} results per keyword
  </p>

  {sections}

</body>
</html>"""


SECTION_TEMPLATE = """
  <div class="keyword-section">
    <div class="keyword-heading">{keyword}</div>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Score</th>
          <th>Source</th>
          <th>Title</th>
          <th>Date</th>
          <th>Summary</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>"""


def score_class(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def build_row(rank: int, article: dict) -> str:
    score = article.get("similarity_score", 0)
    sc = score_class(score)
    url = escape(article.get("url", "#"))
    title = escape(article.get("title_english", "") or article.get("title_original", "") or "Untitled")
    source = escape(article.get("source", ""))
    date = escape(article.get("published_date", "") or "")
    summary = escape(article.get("summary_english", ""))

    summary_cell = (
        f'<span class="summary">{summary}</span>'
        if summary
        else '<span class="no-summary">—</span>'
    )

    return f"""
        <tr>
          <td>{rank}</td>
          <td><span class="score {sc}">{score:.3f}</span></td>
          <td><span class="source-tag">{source}</span></td>
          <td class="title"><a href="{url}" target="_blank" rel="noopener">{title}</a></td>
          <td class="date">{date[:10] if date else "—"}</td>
          <td>{summary_cell}</td>
        </tr>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Export search_results.json to HTML")
    parser.add_argument("--input",  default="search_results.json", help="Input JSON file")
    parser.add_argument("--output", default="search_results.html",  help="Output HTML file")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")

    with open(args.input, encoding="utf-8") as fh:
        data = json.load(fh)

    sections_html = ""
    for keyword, articles in data.get("results", {}).items():
        rows = "".join(build_row(i + 1, a) for i, a in enumerate(articles))
        sections_html += SECTION_TEMPLATE.format(keyword=escape(keyword), rows=rows)

    html = HTML_TEMPLATE.format(
        generated_at=escape(data.get("generated_at", "")),
        total_indexed=data.get("total_articles_indexed", "?"),
        top_n=data.get("top_n_per_keyword", "?"),
        sections=sections_html,
    )

    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"HTML report saved to: {args.output}")


if __name__ == "__main__":
    main()
