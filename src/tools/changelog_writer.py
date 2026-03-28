from datetime import datetime, timezone


def build_changelog(entries: list[str]) -> str:
    """Format a list of change descriptions into a timestamped Markdown changelog."""
    if not entries:
        return ""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"## Review — {now}", ""]
    for entry in entries:
        lines.append(f"- {entry}")
    lines.append("")
    return "\n".join(lines)
