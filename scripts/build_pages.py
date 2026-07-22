#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import os
import re
import shutil
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "site"
SKIP_PARTS = {
    ".git",
    ".github",
    ".pytest_cache",
    ".tmp",
    ".venv",
    "__pycache__",
    "benchmark-runs",
    "site",
    "tests",
    "venv",
}
SKIP_PREFIXES = {("docs", "plans")}
MARKDOWN_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)]+)(\))")
TITLE_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
REPO_ROOT_MARKDOWN = [
    "README.md",
    "CONTRIBUTING.md",
    "NOTICE.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
]


def is_skipped(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        parts = path.parts
    if any(part in SKIP_PARTS for part in parts):
        return True
    return any(
        tuple(parts[index:index + len(prefix)]) == prefix
        for prefix in SKIP_PREFIXES
        for index in range(max(len(parts) - len(prefix) + 1, 0))
    )


def iter_markdown_sources() -> list[Path]:
    docs: set[Path] = {ROOT / rel for rel in REPO_ROOT_MARKDOWN}
    docs.update(ROOT.glob("s[0-9][0-9]_*/README.md"))
    docs.update(ROOT.glob("examples/**/*.md"))
    docs.update(path for path in ROOT.glob("docs/**/*.md") if not is_skipped(path))
    return sorted(path for path in docs if path.exists() and not is_skipped(path))


def route_for_markdown(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel.as_posix() == "README.md":
        return "/"
    if rel.name == "README.md":
        return "/" + rel.parent.as_posix().strip("/") + "/"
    if len(rel.parts) == 1:
        return "/" + rel.stem.lower().replace("_", "-") + "/"
    return "/" + rel.with_suffix("").as_posix().strip("/") + "/"


def output_path_for_route(output_dir: Path, route: str) -> Path:
    if route == "/":
        return output_dir / "index.html"
    return output_dir / route.strip("/") / "index.html"


def read_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = TITLE_RE.search(text)
    if match:
        return match.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def split_link_target(target: str) -> tuple[str, str]:
    if "#" not in target:
        return target, ""
    path_part, anchor = target.split("#", 1)
    return path_part, "#" + anchor


def is_external_target(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "tel:", "data:"))


def to_root_relative(path: Path) -> str:
    return "/" + path.relative_to(ROOT).as_posix()


def normalize_base_path(value: str) -> str:
    value = value.strip()
    if not value or value == "/":
        return "/"
    return "/" + value.strip("/") + "/"


def detect_base_path() -> str:
    override = os.environ.get("PAGES_BASE_PATH") or os.environ.get("SITE_BASE_PATH")
    if override:
        return normalize_base_path(override)

    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo or "/" not in repo:
        return "/"

    owner, repo_name = repo.split("/", 1)
    if repo_name.lower() == f"{owner}.github.io".lower():
        return "/"
    return normalize_base_path(repo_name)


def with_base_path(path: str, base_path: str) -> str:
    if not path.startswith("/") or base_path == "/":
        return path
    if path == "/":
        return base_path
    return base_path.rstrip("/") + path


def resolve_local_target(source: Path, target: str) -> Path | None:
    candidate = (source.parent / target).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


def rewrite_link_target(target: str, source: Path, routes: dict[Path, str], base_path: str = "/") -> str:
    target = target.strip()
    if not target or is_external_target(target) or target.startswith("#"):
        return target
    path_part, anchor = split_link_target(target)
    if not path_part:
        return anchor or target
    if path_part.startswith("/"):
        return with_base_path(path_part, base_path) + anchor

    resolved = resolve_local_target(source, path_part)
    if resolved is None:
        return target

    if resolved.is_dir():
        readme = resolved / "README.md"
        if readme in routes:
            return with_base_path(routes[readme], base_path) + anchor
        return with_base_path(to_root_relative(resolved).rstrip("/") + "/", base_path) + anchor

    if resolved in routes:
        return with_base_path(routes[resolved], base_path) + anchor

    if resolved.exists():
        return with_base_path(to_root_relative(resolved), base_path) + anchor

    if resolved.suffix == "" and resolved.with_suffix(".md") in routes:
        return with_base_path(routes[resolved.with_suffix(".md")], base_path) + anchor

    return target


def rewrite_markdown_links(text: str, source: Path, routes: dict[Path, str], base_path: str = "/") -> str:
    def replace(match: re.Match[str]) -> str:
        prefix, target, suffix = match.groups()
        return prefix + rewrite_link_target(target, source, routes, base_path) + suffix

    return MARKDOWN_LINK_RE.sub(replace, text)


def build_markdown_html(text: str) -> str:
    engine = markdown.Markdown(
        extensions=["extra", "admonition", "codehilite", "toc"],
        extension_configs={"toc": {"permalink": True}},
    )
    return engine.convert(text)


def source_url_for(path: Path) -> str | None:
    repo = os.environ.get("GITHUB_REPOSITORY")
    ref_name = os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_SHA")
    if not repo or not ref_name:
        return None
    rel = path.relative_to(ROOT).as_posix()
    return f"https://github.com/{repo}/blob/{ref_name}/{rel}"


def section_label(path: Path) -> str:
    if path == ROOT / "README.md":
        return "首页"
    if path.match(str(ROOT / "s[0-9][0-9]_*" / "README.md")):
        return "课程章节"
    if path.parent == ROOT / "docs":
        return "补充文档"
    if "examples" in path.parts:
        return "示例"
    return "项目文档"


def build_nav(title_map: dict[Path, str], routes: dict[Path, str], base_path: str, current_route: str) -> str:
    def link_item(label: str, route: str) -> str:
        href = with_base_path(route, base_path)
        active = " nav-link-active" if route == current_route else ""
        return (
            '<li><a class="nav-link'
            + active
            + '" href="'
            + href
            + '">'
            + html.escape(label)
            + "</a></li>"
        )

    parts = [
        '<nav class="sidebar">',
        '<div class="brand-card">',
        f'<a class="brand" href="{with_base_path("/", base_path)}">learn-workbuddy</a>',
        '<p class="brand-copy">从 agent loop 到桌面 AI 助手架构的 24 章工程化教程。</p>',
        "</div>",
        '<div class="nav-group"><div class="nav-title">开始阅读</div><ul>',
    ]
    quick_paths = [
        ROOT / "README.md",
        ROOT / "docs" / "learning-guide.md",
        ROOT / "docs" / "visual-tour.md",
        ROOT / "docs" / "chapter-map.md",
    ]
    for path in quick_paths:
        if path in routes:
            parts.append(link_item(title_map[path], routes[path]))
    parts.append("</ul></div>")

    chapters = sorted(path for path in routes if path.match(str(ROOT / "s[0-9][0-9]_*" / "README.md")))
    parts.append('<div class="nav-group"><div class="nav-title">24 章课程</div><ul>')
    for path in chapters:
        parts.append(link_item(title_map[path], routes[path]))
    parts.append("</ul></div>")

    docs = sorted(
        path for path in routes
        if path.parent == ROOT / "docs"
        and path.name not in {"learning-guide.md", "visual-tour.md", "chapter-map.md"}
    )
    if docs:
        parts.append('<div class="nav-group"><div class="nav-title">补充文档</div><ul>')
        for path in docs:
            parts.append(link_item(title_map[path], routes[path]))
        parts.append("</ul></div>")

    examples = sorted(path for path in routes if "examples" in path.parts)
    if examples:
        parts.append('<div class="nav-group"><div class="nav-title">示例</div><ul>')
        for path in examples:
            parts.append(link_item(title_map[path], routes[path]))
        parts.append("</ul></div>")

    project_docs = sorted(
        path for path in routes
        if path.parent == ROOT and path.name != "README.md"
    )
    if project_docs:
        parts.append('<div class="nav-group"><div class="nav-title">项目文档</div><ul>')
        for path in project_docs:
            parts.append(link_item(title_map[path], routes[path]))
        parts.append("</ul></div>")

    parts.append("</nav>")
    return "\n".join(parts)


def page_template(
    *,
    page_title: str,
    content: str,
    nav: str,
    source_url: str | None,
    base_path: str,
    page_section: str,
) -> str:
    source_html = ""
    if source_url:
        source_html = (
            '<p class="source-link"><a class="source-button" href="'
            + html.escape(source_url)
            + '" target="_blank" rel="noreferrer">查看源码</a></p>'
        )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(page_title)} | learn-workbuddy</title>
  <link rel="stylesheet" href="{with_base_path('/assets/site.css', base_path)}">
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: false, theme: "neutral" }});
    window.addEventListener("DOMContentLoaded", async () => {{
      document.querySelectorAll("pre code.language-mermaid").forEach((codeBlock) => {{
        const wrapper = document.createElement("div");
        wrapper.className = "mermaid";
        wrapper.textContent = codeBlock.textContent || "";
        codeBlock.parentElement.replaceWith(wrapper);
      }});
      await mermaid.run({{ querySelector: ".mermaid" }});
    }});
  </script>
</head>
<body>
  <div class="layout">
    {nav}
    <main class="content-shell">
      <header class="page-header">
        <div class="page-header-copy">
          <span class="page-eyebrow">{html.escape(page_section)}</span>
          <h1>{html.escape(page_title)}</h1>
        </div>
        {source_html}
      </header>
      <article class="markdown-body">
        {content}
      </article>
    </main>
  </div>
</body>
</html>
"""


def write_assets(output_dir: Path) -> None:
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "site.css").write_text(
        """\
:root {
  color-scheme: light;
  --bg: #f4f7fb;
  --bg-accent: rgba(96, 165, 250, 0.14);
  --panel: rgba(255, 255, 255, 0.9);
  --panel-strong: #ffffff;
  --sidebar-bg: linear-gradient(180deg, #0f172a 0%, #111827 100%);
  --sidebar-border: rgba(148, 163, 184, 0.16);
  --border: rgba(148, 163, 184, 0.22);
  --text: #0f172a;
  --muted: #5b6474;
  --heading: #111827;
  --link: #2563eb;
  --link-strong: #1d4ed8;
  --code-bg: #0f172a;
  --code-fg: #e2e8f0;
  --code-inline-bg: #e8eefb;
  --shadow-soft: 0 18px 40px rgba(15, 23, 42, 0.08);
  --shadow-strong: 0 28px 80px rgba(15, 23, 42, 0.14);
  --radius-lg: 24px;
  --radius-md: 18px;
  --radius-sm: 12px;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
  background-image:
    radial-gradient(circle at top left, var(--bg-accent), transparent 26rem),
    radial-gradient(circle at right 12%, rgba(167, 139, 250, 0.12), transparent 24rem);
}
a {
  color: var(--link);
  text-decoration: none;
  transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
}
a:hover { color: var(--link-strong); }
.layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 28px;
  min-height: 100vh;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
}
.sidebar {
  position: sticky;
  top: 24px;
  align-self: start;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  padding: 20px 16px 28px;
  background: var(--sidebar-bg);
  color: #e5e7eb;
  border: 1px solid var(--sidebar-border);
  border-radius: 28px;
  box-shadow: var(--shadow-strong);
  backdrop-filter: blur(18px);
}
.brand-card {
  padding: 12px 10px 18px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
}
.brand {
  display: inline-block;
  color: #ffffff;
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}
.brand-copy {
  margin: 10px 0 0;
  font-size: 0.92rem;
  line-height: 1.6;
  color: #94a3b8;
}
.nav-group {
  margin-top: 18px;
  padding: 14px 10px 0;
}
.nav-title {
  margin-bottom: 10px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7dd3fc;
}
.nav-group ul { margin: 0; padding: 0; list-style: none; }
.nav-group li { margin: 0 0 6px; }
.nav-link {
  display: block;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  color: #dbeafe;
  font-size: 0.93rem;
  line-height: 1.45;
}
.nav-link:hover {
  background: rgba(37, 99, 235, 0.16);
  border-color: rgba(96, 165, 250, 0.28);
  color: #ffffff;
  text-decoration: none;
}
.nav-link-active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.28), rgba(147, 197, 253, 0.14));
  border-color: rgba(125, 211, 252, 0.35);
  color: #ffffff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
.content-shell {
  min-width: 0;
  padding: 8px 8px 56px 0;
}
.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
  padding: 28px 30px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.72));
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(16px);
}
.page-header-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.page-eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: var(--link-strong);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.page-header h1 {
  margin: 0;
  color: var(--heading);
  font-size: clamp(2rem, 3vw, 2.8rem);
  line-height: 1.08;
  letter-spacing: -0.03em;
}
.source-link { margin: 0; color: var(--muted); }
.source-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 14px;
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--link-strong);
  font-weight: 600;
  box-shadow: 0 10px 20px rgba(37, 99, 235, 0.08);
}
.source-button:hover {
  text-decoration: none;
  transform: translateY(-1px);
}
.markdown-body {
  max-width: 980px;
  padding: 40px 42px 48px;
  background: var(--panel-strong);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-soft);
  line-height: 1.82;
  font-size: 1rem;
}
.markdown-body > *:first-child { margin-top: 0; }
.markdown-body > *:last-child { margin-bottom: 0; }
.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4 {
  color: var(--heading);
  letter-spacing: -0.02em;
  line-height: 1.2;
}
.markdown-body h1 { font-size: 2.2rem; margin: 0 0 1.2rem; }
.markdown-body h2 {
  margin-top: 2.6rem;
  margin-bottom: 1rem;
  padding-top: 0.2rem;
  font-size: 1.55rem;
}
.markdown-body h3 {
  margin-top: 1.8rem;
  margin-bottom: 0.8rem;
  font-size: 1.2rem;
}
.markdown-body p,
.markdown-body li,
.markdown-body td,
.markdown-body th {
  color: #334155;
}
.markdown-body ul,
.markdown-body ol {
  padding-left: 1.35rem;
}
.markdown-body li + li {
  margin-top: 0.45rem;
}
.markdown-body hr {
  margin: 2rem 0;
  border: 0;
  border-top: 1px solid var(--border);
}
.markdown-body img {
  max-width: 100%;
  height: auto;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
}
.markdown-body table {
  display: block;
  overflow-x: auto;
  width: 100%;
  border-collapse: collapse;
  margin: 1.3rem 0;
  border-radius: 16px;
  background: #fbfdff;
}
.markdown-body th,
.markdown-body td {
  padding: 12px 14px;
  border: 1px solid var(--border);
  vertical-align: top;
}
.markdown-body th {
  background: #f5f8ff;
  font-weight: 700;
}
.markdown-body pre {
  overflow-x: auto;
  padding: 18px 20px;
  border-radius: 18px;
  background: var(--code-bg);
  color: var(--code-fg);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
.markdown-body code {
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: 0.95em;
}
.markdown-body :not(pre) > code {
  padding: 0.15rem 0.35rem;
  border-radius: 8px;
  background: var(--code-inline-bg);
  color: #1e3a8a;
}
.markdown-body blockquote {
  margin: 1.4rem 0;
  padding: 1rem 1.1rem 1rem 1.2rem;
  border-left: 4px solid #60a5fa;
  border-radius: 0 14px 14px 0;
  color: #334155;
  background: linear-gradient(90deg, rgba(219, 234, 254, 0.95), rgba(239, 246, 255, 0.7));
}
.mermaid {
  overflow-x: auto;
  margin: 1.8rem 0;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(255, 255, 255, 0.96));
}
.markdown-body a {
  font-weight: 600;
}
.markdown-body a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}
.markdown-body strong {
  color: #0f172a;
}
.markdown-body .toc {
  margin: 1.5rem 0;
  padding: 1rem 1.2rem;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: #f8fbff;
}
@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 16px;
  }
  .sidebar {
    position: static;
    max-height: none;
    border-radius: 22px;
  }
  .content-shell {
    padding: 0 0 40px;
  }
  .page-header {
    padding: 22px 20px;
  }
  .page-header h1 {
    font-size: 1.7rem;
  }
  .markdown-body {
    padding: 24px 20px 30px;
    border-radius: 20px;
  }
}
""",
        encoding="utf-8",
    )


def copy_static_files(output_dir: Path) -> None:
    for path in ROOT.rglob("*"):
        if path.is_dir() or is_skipped(path):
            continue
        rel = path.relative_to(ROOT)
        destination = output_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def build_site(output_dir: Path = DEFAULT_OUTPUT) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_path = detect_base_path()
    markdown_sources = iter_markdown_sources()
    routes = {path.resolve(): route_for_markdown(path.resolve()) for path in markdown_sources}
    title_map = {path.resolve(): read_title(path.resolve()) for path in markdown_sources}
    copy_static_files(output_dir)
    write_assets(output_dir)

    for path in markdown_sources:
        source = path.resolve()
        current_route = routes[source]
        nav = build_nav(title_map, routes, base_path, current_route)
        text = source.read_text(encoding="utf-8")
        rewritten = rewrite_markdown_links(text, source, routes, base_path)
        content = build_markdown_html(rewritten)
        page = page_template(
            page_title=title_map[source],
            content=content,
            nav=nav,
            source_url=source_url_for(source),
            base_path=base_path,
            page_section=section_label(source),
        )
        destination = output_path_for_route(output_dir, routes[source])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(page, encoding="utf-8")

    shutil.copy2(output_dir / "index.html", output_dir / "404.html")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a static GitHub Pages site for learn-workbuddy.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Static site output directory.",
    )
    args = parser.parse_args()
    output_dir = build_site(args.output)
    print(f"Built pages site at {output_dir} (base path: {detect_base_path()})")


if __name__ == "__main__":
    main()
