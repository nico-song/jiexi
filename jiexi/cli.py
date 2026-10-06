import argparse
import json
import os
import re
import sys

import ollama
from rich.console import Console
from rich.table import Table

SYSTEM = """You are a friendly Mandarin tutor for English-speaking beginners.
First decide if the input is a real, grammatical Chinese sentence or phrase.
If it is random characters or nonsense, set "valid" to false, explain briefly in "problem",
and still break down each character honestly (do NOT invent names or meanings).
Write ALL explanations in simple English.
Fields:
- "valid": true if it is a real Chinese sentence/phrase, false if it is nonsense.
- "problem": if not valid, one short sentence on why. Otherwise "".
- "translation": natural, fluent English. If not valid, "".
- "literal": a word-for-word ENGLISH gloss that keeps Chinese word order.
  Example: 我今天不想上学 -> "I today not want go-to-school". Never put Chinese characters here.
- "words": one object per word, with:
  - "word": the Chinese word
  - "pinyin": with tone marks (nǐ hǎo, not ni3 hao3)
  - "pos": plain English like "noun", "verb", "time word", "particle", "measure word"
  - "meaning": short English meaning as used in THIS sentence
- "grammar": 1-3 notes in plain English explaining notable structures (把, 了, 是...的, 不 vs 没, etc.),
  comparing to how English would say it. Empty list if nothing notable.
- "tip": one short tip about a mistake English speakers commonly make with this sentence, or "" if none."""

SCHEMA = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "problem": {"type": "string"},
        "translation": {"type": "string"},
        "literal": {"type": "string"},
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "pinyin": {"type": "string"},
                    "pos": {"type": "string"},
                    "meaning": {"type": "string"},
                },
                "required": ["word", "pinyin", "pos", "meaning"],
            },
        },
        "grammar": {"type": "array", "items": {"type": "string"}},
        "tip": {"type": "string"},
    },
    "required": ["valid", "problem", "translation", "literal", "words", "grammar", "tip"],
}

CJK = re.compile(r"[\u4e00-\u9fff]")


def analyze(sentence: str, model: str) -> dict:
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": sentence},
        ],
        format=SCHEMA,
        options={"temperature": 0},
    )
    return json.loads(resp["message"]["content"])


def render(data: dict, console: Console) -> None:
    console.print()
    if data.get("valid") is False:
        console.print(f"[bold red]Doesn't look like a real sentence:[/bold red] {data.get('problem', '')}")
        console.print("[dim]Character breakdown below may be unreliable.[/dim]")
    else:
        console.print(f"[bold]Translation:[/bold] {data.get('translation', '')}")
        literal = data.get("literal", "")
        if literal and not CJK.search(literal):
            console.print(f"[dim]Literally: {literal}[/dim]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    for col in ("Word", "Pinyin", "Type", "Meaning"):
        table.add_column(col)
    for w in data.get("words", []):
        if not isinstance(w, dict):
            continue
        table.add_row(w.get("word", ""), w.get("pinyin", ""), w.get("pos", ""), w.get("meaning", ""))
    console.print(table)

    if data.get("valid") is not False:
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
