#!/usr/bin/env python3
"""Create labels and apply them to all issues."""
import json
import subprocess
import sys

REPO = "RAGNAROS-HS/Weles"

LABELS = [
    {"name": "backend",      "color": "0075ca", "description": "FastAPI, tools, agent logic, DB"},
    {"name": "frontend",     "color": "7057ff", "description": "React/Vite UI"},
    {"name": "agent",        "color": "e4e669", "description": "LLM/Claude integration, ToolRegistry, streaming"},
    {"name": "research",     "color": "f9d0c4", "description": "Reddit, web search, credibility scoring"},
    {"name": "db",           "color": "c5def5", "description": "Schema, migrations, repos"},
    {"name": "distribution", "color": "bfd4f2", "description": "PyInstaller, pystray, packaging"},
]

# issue number -> list of label names
ISSUE_LABELS: dict[int, list[str]] = {
    1:  ["backend", "frontend", "db"],
    2:  ["backend", "agent"],
    3:  ["backend", "db"],
    4:  ["backend"],
    5:  ["backend", "frontend", "agent"],
    6:  ["backend", "db"],
    7:  ["backend", "frontend", "agent"],
    8:  ["backend", "agent"],
    9:  ["frontend"],
    10: ["frontend"],
    11: ["backend", "agent"],
    12: ["backend", "frontend", "db"],
    13: ["backend", "agent"],
    14: ["backend", "research"],
    15: ["backend", "research"],
    16: ["backend", "research"],
    17: ["backend", "research"],
    18: ["backend", "agent", "research"],
    19: ["backend", "agent", "research"],
    20: ["backend", "agent", "research"],
    21: ["backend", "agent", "research"],
    22: ["backend", "agent", "research"],
    23: ["backend", "agent"],
    24: ["backend"],
    25: ["backend"],
    26: ["backend"],
    27: ["backend", "agent"],
    28: ["backend"],
    29: ["backend", "agent", "research"],
    30: ["backend", "research"],
    31: ["backend"],
    32: ["distribution"],
}


def gh_json(*args: str) -> dict | list:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: gh {' '.join(args)}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: gh {' '.join(args)}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def ensure_labels() -> None:
    print("Creating labels...")
    existing = {l["name"] for l in gh_json("api", f"repos/{REPO}/labels?per_page=100")}
    for label in LABELS:
        if label["name"] in existing:
            print(f"  '{label['name']}' already exists")
            continue
        gh_json(
            "api", f"repos/{REPO}/labels",
            "--method", "POST",
            "--field", f"name={label['name']}",
            "--field", f"color={label['color']}",
            "--field", f"description={label['description']}",
        )
        print(f"  Created '{label['name']}'")


def get_issue_numbers() -> dict[str, int]:
    """Return mapping of issue title prefix '#N:' -> GitHub issue number."""
    issues = gh_json("api", f"repos/{REPO}/issues?state=all&per_page=100", "--paginate")
    result = {}
    for issue in issues:
        import re
        m = re.match(r'^#(\d+):', issue["title"])
        if m:
            result[int(m.group(1))] = issue["number"]
    return result


def apply_labels(issue_map: dict[int, int]) -> None:
    print("\nApplying labels to issues...")
    for issue_num, labels in ISSUE_LABELS.items():
        gh_issue_num = issue_map.get(issue_num)
        if gh_issue_num is None:
            print(f"  WARNING: issue #{issue_num} not found on GitHub, skipping")
            continue
        label_args = []
        for label in labels:
            label_args += ["--field", f"labels[]={label}"]
        gh_json(
            "api", f"repos/{REPO}/issues/{gh_issue_num}/labels",
            "--method", "POST",
            *label_args,
        )
        print(f"  #{issue_num} -> {', '.join(labels)}")


def main() -> None:
    ensure_labels()
    issue_map = get_issue_numbers()
    print(f"\nFound {len(issue_map)} issues on GitHub")
    apply_labels(issue_map)
    print("\nDone.")


if __name__ == "__main__":
    main()
