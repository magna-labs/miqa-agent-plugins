#!/usr/bin/env python3
"""Check that Miqa report templates stay one family and render cleanly.

A report template is a `reference/template.html` file under plugins/. Templates that use the shared
Miqa report design (they define the `--paper` design token) must carry the same font link and the same
design tokens as the canonical template. Every template, shared design or not, must also keep its
HTML comments well formed: comments cannot nest, and a comment that holds the text of another
comment ends early and leaves its instructions visible on the published page.

Run from the repository root:  python3 scripts/check_report_templates.py
Exits 1 and prints what differs if a template has drifted.
"""

import difflib
import glob
import re
import sys

CANONICAL = "plugins/miqa/skills/version-rollup/reference/template.html"
TEMPLATE_GLOB = "plugins/**/reference/template.html"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def font_link(html):
    match = re.search(r'<link rel="stylesheet"[^>]*>', html)
    return match.group(0) if match else None


def design_tokens(html):
    """the `--name: value;` lines of the first <style> block, whitespace-normalised"""
    style = re.search(r"<style>(.*?)</style>", html, re.S)
    if not style:
        return []
    lines = [line.strip() for line in style.group(1).splitlines()]
    return [line for line in lines if re.match(r"--[a-z0-9-]+:", line)]


def uses_shared_design(html):
    return any(line.startswith("--paper:") for line in design_tokens(html))


def nested_comments(html):
    """offsets where a comment opens inside another comment (the outer one then ends early)"""
    return [m.start() for m in re.finditer(r"<!--(?:(?!-->).)*?<!--", html, re.S)]


def check(path, canonical_link, canonical_tokens):
    html = read(path)
    problems = []
    if nested_comments(html):
        line = html[: nested_comments(html)[0]].count("\n") + 1
        problems.append(
            f"a comment contains another '<!--' (near line {line}); comments cannot nest, so the "
            "outer one ends early and its remaining text shows on the page"
        )
    if uses_shared_design(html):
        if font_link(html) != canonical_link:
            problems.append("the font <link> differs from the canonical template")
        tokens = design_tokens(html)
        if tokens != canonical_tokens:
            diff = difflib.unified_diff(
                canonical_tokens, tokens, "canonical", path, lineterm="", n=0
            )
            problems.append("design tokens differ from the canonical template:\n" + "\n".join(diff))
    return problems


def main():
    canonical = read(CANONICAL)
    canonical_link, canonical_tokens = font_link(canonical), design_tokens(canonical)
    if not canonical_tokens:
        print(f"{CANONICAL}: no design tokens found, so there is nothing to compare against")
        return 1
    failed = False
    paths = sorted(glob.glob(TEMPLATE_GLOB, recursive=True))
    for path in paths:
        problems = check(path, canonical_link, canonical_tokens)
        if problems:
            failed = True
            print(f"FAIL {path}")
            for problem in problems:
                print("  - " + problem.replace("\n", "\n    "))
        else:
            kind = "shared design" if uses_shared_design(read(path)) else "own design"
            print(f"ok   {path} ({kind})")
    print(f"{len(paths)} template(s) checked")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
