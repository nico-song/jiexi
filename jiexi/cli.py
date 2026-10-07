import argparse
import json
import os
import re
import sys

import ollama
from rich.console import Console
from rich.table import Table

SYSTEM = """You are a friendly Mandarin tutor for English-speaking beginners.
Write EVERY explanation in English. Only use Chinese when quoting specific words.

Step 1. Classify the input as one of:
- "correct": a natural, grammatical Chinese sentence or phrase.
- "mistake": you can tell what the writer meant, but it has errors (wrong word, missing word,
  wrong word order, wrong particle, typo, etc.).
- "nonsense": random characters with no clear intended meaning.

Step 2. Fill the fields:
- "status": one of the three above.
- "corrected": if "mistake", the most likely intended correct sentence. Otherwise "".
- "mistakes": if "mistake", 1-3 short English explanations of what was wrong and why.
  Example: "今 alone isn't used for 'today' in speech, use 今天." Otherwise [].
- "problem": if "nonsense", one short English sentence on why. Otherwise "".
- "translation": natural English of the sentence (the corrected one if "mistake"). "" if nonsense.
- "literal": word-for-word ENGLISH gloss in Chinese word order, of the corrected sentence if "mistake".
  Example: 我今天不想上学 -> "I today not want go-to-school". Never put Chinese characters here.
- "words": break down the sentence (the CORRECTED one if "mistake") into real words, keeping
  compound words together (上学 is one word, not 上 + 学). Each with:
  - "word", "pinyin" (tone marks: nǐ hǎo), "pos" (plain English: noun, verb, time word, particle,
    measure word), "meaning" (short English, as used here).
  If nonsense, list each character honestly; do NOT invent names or meanings.
- "grammar": 1-3 English notes on notable structures (把, 了, 是...的, 不 vs 没, etc.),
  comparing to English. [] if nothing notable or nonsense.
- "tip": one short English tip about a common mistake English speakers make here, or ""."""

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["correct", "mistake", "nonsense"]},
        "corrected": {"type": "string"},
        "mistakes": {"type": "array", "items": {"type": "string"}},
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
    "required": ["status", "corrected", "mistakes", "problem", "translation",
                 "literal", "words", "grammar", "tip"],
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
    status = data.get("status", "correct")
    console.print()

    if status == "nonsense":
        console.print(f"[bold red]Doesn't look like a real sentence.[/bold red] {data.get('problem', '')}")
        console.print("[dim]Character breakdown below may be unreliable.[/dim]")
    else:
        if status == "mistake" and data.get("corrected"):
            console.print(f"[bold yellow]Did you mean:[/bold yellow] {data['corrected']}")
            for m in data.get("mistakes", []):
                console.print(f"  [yellow]✗[/yellow] {m}")
            console.print()
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

    if status != "nonsense":
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
