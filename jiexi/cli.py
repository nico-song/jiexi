import argparse
import json
import os
import sys

import ollama
from rich.console import Console
from rich.table import Table

SYSTEM = """You are a friendly Mandarin tutor for English-speaking beginners.
Segment the user's Chinese sentence into words. Write ALL explanations in simple English.
Return ONLY valid JSON in exactly this shape:
{"translation": str,
 "literal": str,
 "words": [{"word": str, "pinyin": str, "pos": str, "meaning": str}],
 "grammar": [str],
 "tip": str}
Rules:
- "translation": natural, fluent English.
- "literal": word-for-word English gloss in Chinese word order, so the learner sees the structure.
- "pinyin": use tone marks (nǐ hǎo, not ni3 hao3).
- "pos": plain English like "noun", "verb", "time word", "particle", "measure word". No abbreviations.
- "meaning": short English meaning as used in THIS sentence.
- "grammar": 1-3 notes explaining notable structures (把, 了, 是...的, etc.) in plain English,
  comparing to how English would say it. [] if nothing notable.
- "tip": one short tip about a mistake English speakers commonly make with this sentence, or "" if none."""


def analyze(sentence: str, model: str) -> dict:
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": sentence},
        ],
        format="json",
    )
    return json.loads(resp["message"]["content"])


def render(data: dict, console: Console) -> None:
    console.print(f"\n[bold]Translation:[/bold] {data.get('translation', '')}")
    if data.get("literal"):
        console.print(f"[dim]Literally: {data['literal']}[/dim]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    for col in ("Word", "Pinyin", "Type", "Meaning"):
        table.add_column(col)
    for w in data.get("words", []):
        table.add_row(w.get("word", ""), w.get("pinyin", ""), w.get("pos", ""), w.get("meaning", ""))
    console.print(table)

    if data.get("grammar"):
        console.print("\n[bold]Grammar notes[/bold]")
        for note in data["grammar"]:
            console.print(f"  • {note}")

    if data.get("tip"):
        console.print(f"\n[bold yellow]Watch out:[/bold yellow] {data['tip']}")
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(prog="jiexi", description="Break down a Chinese sentence for English speakers.")
    parser.add_argument("sentence", nargs="?", help="Chinese sentence (or pipe via stdin)")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    parser.add_argument("--model", default=os.getenv("JIEXI_MODEL", "qwen2.5:7b"))
    args = parser.parse_args()

    sentence = args.sentence or (sys.stdin.read().strip() if not sys.stdin.isatty() else "")
    if not sentence:
        parser.error("give me a sentence, e.g. jiexi '我喜欢喝茶'")

    console = Console()
    try:
        with console.status("解析中..."):
            data = analyze(sentence, args.model)
    except json.JSONDecodeError:
        console.print("[red]Model returned invalid JSON, try again.[/red]")
        sys.exit(1)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        render(data, console)


if __name__ == "__main__":
    main()
