from __future__ import annotations

from pathlib import Path

from scripts.build_pages import build_site, rewrite_link_target, route_for_markdown


def test_route_for_markdown_handles_root_chapters_and_docs(root: Path) -> None:
    assert route_for_markdown(root / "README.md") == "/"
    assert route_for_markdown(root / "s01_agent_loop" / "README.md") == "/s01_agent_loop/"
    assert route_for_markdown(root / "docs" / "learning-guide.md") == "/docs/learning-guide/"


def test_rewrite_link_target_maps_markdown_and_assets(root: Path) -> None:
    routes = {
        (root / "README.md").resolve(): "/",
        (root / "docs" / "learning-guide.md").resolve(): "/docs/learning-guide/",
        (root / "s01_agent_loop" / "README.md").resolve(): "/s01_agent_loop/",
    }
    source = (root / "README.md").resolve()

    assert rewrite_link_target("./s01_agent_loop/", source, routes) == "/s01_agent_loop/"
    assert rewrite_link_target("./docs/learning-guide.md", source, routes) == "/docs/learning-guide/"
    assert rewrite_link_target("./images/architecture-overview.svg", source, routes) == "/images/architecture-overview.svg"
    assert rewrite_link_target("./LICENSE", source, routes) == "/LICENSE"


def test_build_site_generates_core_pages(root: Path, tmp_path: Path) -> None:
    output_dir = build_site(tmp_path / "site")

    home = (output_dir / "index.html").read_text(encoding="utf-8")
    chapter = (output_dir / "s01_agent_loop" / "index.html").read_text(encoding="utf-8")
    guide = (output_dir / "docs" / "learning-guide" / "index.html").read_text(encoding="utf-8")

    assert "learn-workbuddy" in home
    assert "/s01_agent_loop/" in home
    assert "language-mermaid" in chapter
    assert "<h1>Learning Guide</h1>" in guide
