#!/usr/bin/env python3
"""Parse issues.md and create GitHub milestones + issues via gh CLI."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "RAGNAROS-HS/Weles"

MILESTONE_MAP = {
    "v0.1": "v0.1 Skeleton",
    "v0.2": "v0.2 Personalization",
    "v0.3": "v0.3 Research Engine",
    "v0.4": "v0.4 Domain Modules",
    "v0.5": "v0.5 Learning Loop",
    "v0.6": "v0.6 Signal Quality",
    "v1.0": "v1.0 Distribution",
}

MILESTONE_DESCRIPTIONS = {
    "v0.1 Skeleton": "Working browser chat with correct tone, persistent sessions",
    "v0.2 Personalization": "Mode selector, profile, information tab, settings, history",
    "v0.3 Research Engine": "Reddit + web search, credibility, synthesis, error resilience",
    "v0.4 Domain Modules": "Shopping, diet, fitness, lifestyle mode implementations",
    "v0.5 Learning Loop": "Context compression, session-start orchestration, follow-ups, check-ins, correction, decay",
    "v0.6 Signal Quality": "Confidence calibration, anti-bias, proactive surfacing",
    "v1.0 Distribution": "System tray app, PyInstaller .exe, Windows auto-start",
}

ISSUE_MILESTONE = {
    range(1, 6): "v0.1 Skeleton",
    range(6, 13): "v0.2 Personalization",
    range(13, 19): "v0.3 Research Engine",
    range(19, 23): "v0.4 Domain Modules",
    range(23, 29): "v0.5 Learning Loop",
    range(29, 32): "v0.6 Signal Quality",
    range(32, 33): "v1.0 Distribution",
}


def get_milestone_for_issue(num: int) -> str:
    for r, milestone in ISSUE_MILESTONE.items():
        if num in r:
            return milestone
    raise ValueError(f"No milestone for issue #{num}")


def gh(*args: str) -> dict | list | str:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: gh {' '.join(args)}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def gh_json(*args: str) -> dict | list:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: gh {' '.join(args)}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def create_milestones() -> dict[str, int]:
    """Create milestones and return title -> number mapping."""
    print("Creating milestones...")
    existing = gh_json("api", f"repos/{REPO}/milestones", "--paginate")
    existing_map = {m["title"]: m["number"] for m in existing}

    milestone_numbers = {}
    for title, description in MILESTONE_DESCRIPTIONS.items():
        if title in existing_map:
            print(f"  Milestone '{title}' already exists (#{existing_map[title]})")
            milestone_numbers[title] = existing_map[title]
        else:
            resp = gh_json(
                "api",
                f"repos/{REPO}/milestones",
                "--method", "POST",
                "--field", f"title={title}",
                "--field", f"description={description}",
            )
            milestone_numbers[title] = resp["number"]
            print(f"  Created milestone '{title}' (#{resp['number']})")

    return milestone_numbers


def parse_issues(md_path: Path) -> list[dict]:
    """Extract issues from issues.md. Returns list of {num, title, body}."""
    text = md_path.read_text(encoding="utf-8")

    # Split on "### Issue #N:" headers
    pattern = re.compile(r'^### Issue #(\d+): (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    issues = []
    for i, match in enumerate(matches):
        num = int(match.group(1))
        title = match.group(2).strip()

        # Body runs from after this header to the next "### Issue" header or end of section
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw_body = text[start:end].strip()

        # Trim trailing "---" separator
        raw_body = re.sub(r'\n---\s*$', '', raw_body).strip()

        issues.append({"num": num, "title": title, "body": raw_body})

    return issues


def create_issues(issues: list[dict], milestone_numbers: dict[str, int]) -> None:
    # Check which issues already exist
    print("\nChecking existing issues...")
    existing_raw = gh_json("api", f"repos/{REPO}/issues?state=all&per_page=100", "--paginate")
    existing_titles = {i["title"] for i in existing_raw}

    with tempfile.TemporaryDirectory() as tmpdir:
        for issue in issues:
            full_title = f"#{issue['num']}: {issue['title']}"
            if full_title in existing_titles:
                print(f"  Issue '{full_title}' already exists, skipping")
                continue

            milestone_name = get_milestone_for_issue(issue["num"])
            milestone_num = milestone_numbers[milestone_name]

            # Write body to temp file to avoid shell escaping issues
            body_file = Path(tmpdir) / f"issue_{issue['num']}.md"
            body_file.write_text(issue["body"], encoding="utf-8")

            print(f"  Creating #{issue['num']}: {issue['title']}...")
            gh(
                "issue", "create",
                "--repo", REPO,
                "--title", full_title,
                "--body-file", str(body_file),
                "--milestone", milestone_name,
            )

    print("\nDone.")


def main() -> None:
    md_path = Path(__file__).parent.parent / "issues.md"
    if not md_path.exists():
        print(f"issues.md not found at {md_path}", file=sys.stderr)
        sys.exit(1)

    milestone_numbers = create_milestones()
    issues = parse_issues(md_path)
    print(f"\nParsed {len(issues)} issues from issues.md")
    create_issues(issues, milestone_numbers)


if __name__ == "__main__":
    main()
