# jiexi (解析)

A command-line tool that breaks down Chinese sentences for English speakers. Give it a sentence and it shows you the translation, a word-for-word literal gloss, each word's pinyin and meaning, grammar notes, and a tip about common learner mistakes.

Runs entirely on your own machine with a local LLM through [Ollama](https://ollama.com), so there are no API keys and no costs.

![demo](docs/demo.png)

## Why

Translation apps give you the English but doesn't always show you why the sentence is built the way it is, which I learned was a huge barrier when I TA'd for Chinese speakers.
jiexi is meant to fill that gap, it shows the Chinese word order next to the English so structures like 把, 了, and 是...的 actually make sense (b/c these structures don't always exist in English)

## Setup

Requires Python 3.10+ and macOS/Linux/Windows with Ollama installed.

1. Install Ollama from https://ollama.com and pull the model!!!:
```bash
   ollama pull qwen2.5:7b
```
   On machines with 8 GB RAM or less, use `qwen2.5:3b` instead its a smaller version and slightly dumber.

2. Clone and install:
```bash
   git clone https://github.com/nico-song/jiexi.git
   cd jiexi
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
```

## Usage

```bash
jiexi "我昨天把作业交了"
```

Raw JSON output (useful for piping into other tools):

```bash
jiexi "他是坐飞机来的" --json
```

Read from stdin:

```bash
echo "你吃饭了吗" | jiexi
```

Use a different model:

```bash
jiexi "我喜欢喝茶" --model qwen2.5:3b
# or set it once
export JIEXI_MODEL=qwen2.5:3b
```

## How it works

The sentence is sent to a local Qwen model with a system prompt that asks for a fixed JSON schema (translation, literal gloss, per-word breakdown, grammar notes, tip). Ollama's JSON mode constrains the output so it always parses, and the result is rendered as a terminal table with [Rich](https://github.com/Textualize/rich).

Qwen was picked because it's trained heavily on Chinese text and handles segmentation and pinyin better than most models its size. (and free!)

## Limitations

- It's an LLM, so pinyin and segmentation can occasionally be wrong, especially tone and rare words or if you give it a sentence that doesn't work. Double check anything important.
- Speed depends on your hardware :( Expect a few seconds per sentence on a recent laptop.

## Roadmap

- [ ] Eval set of hand-checked sentences to measure pinyin accuracy
- [ ] Local cache so repeat lookups are instant
- [ ] Publish to PyPI
EOF
