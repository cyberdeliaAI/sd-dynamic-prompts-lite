# Dynamic Prompts Lite

A lightweight fork of [sd-dynamic-prompts](https://github.com/adieyal/sd-dynamic-prompts) by [@adieyal](https://github.com/adieyal), stripped down to the essentials: **wildcards and variant syntax** — nothing more.

> **The idea is simple:** drop your `.txt` wildcard files into a folder, reference them in your prompts with `__filename__`, and let the extension do the rest. No bloat, no AI models, no network calls.

---

## What's included

| Feature                   | Description                                                  |
| ------------------------- | ------------------------------------------------------------ |
| **Wildcard files**        | Place `.txt` files in the `wildcards/` folder, use `__filename__` in your prompt |
| **Variant syntax**        | `{red\|green\|blue}` picks one randomly                      |
| **Weighted variants**     | `{0.5::red\|0.3::green\|0.2::blue}`                          |
| **Multi-select**          | `{2$$red\|green\|blue}` picks two                            |
| **Range select**          | `{1-3$$red\|green\|blue}` picks between 1 and 3              |
| **Combinatorial mode**    | Generate all possible prompt combinations                    |
| **Wildcards Manager tab** | Browse and preview your wildcard files (read-only)           |
| **Nested wildcards**      | Subfolders supported: `__animals/cats__`                     |
| **Variables**             | `${color=red}` and `${color}` for reusable snippets          |
| **Configurable syntax**   | Change variant brackets and wildcard wrapping in Settings    |

## What's removed

Compared to the full [sd-dynamic-prompts](https://github.com/adieyal/sd-dynamic-prompts):

| Removed                                       | Why                                                          |
| --------------------------------------------- | ------------------------------------------------------------ |
| **Magic Prompt**                              | Requires downloading large AI models (300MB–1.4GB), uses VRAM |
| **I'm Feeling Lucky**                         | Network calls to lexica.art                                  |
| **Attention Grabber**                         | Rarely used, adds complexity                                 |
| **Jinja2 templates**                          | Too advanced for most users, adds dependency weight          |
| **Wildcard editing in UI**                    | Manage your files on disk — simpler and safer                |
| **Collection copy/download**                  | No bundled 28MB wildcard library — bring your own            |
| **`send2trash` dependency**                   | Only needed for UI delete, which is removed                  |
| **`magicprompt` + `attentiongrabber` extras** | Heavy optional dependencies eliminated                       |

**Result:** ~29 MB → ~78 KB. One Python dependency (`dynamicprompts`) instead of three.

---

## Installation

### Option 1: Clone directly into extensions

```bash
cd /path/to/stable-diffusion-webui/extensions
git clone https://github.com/cyberdeliaAI/sd-dynamic-prompts-lite.git
```

### Option 2: Manual install

1. Download and extract the ZIP into your `extensions/` directory.
2. Restart the WebUI — `dynamicprompts` is installed automatically.

---

## Usage

### 1. Add wildcard files

Place `.txt` files in the `wildcards/` folder (inside the extension directory, or set a custom path in **Settings → Dynamic Prompts**). Each file should have **one option per line**:

```
wildcards/
├── animals.txt
├── colors.txt
└── styles/
    ├── painting.txt
    └── photography.txt
```

**Example `animals.txt`:**

```
cat
dog
owl
fox
wolf
```

### 2. Use wildcards in your prompt

```
a photo of a __animals__ wearing a __colors__ hat
```

Each generation randomly picks one line from each referenced file.

### 3. Variant syntax

Inline randomization without needing a file:

```
a {beautiful|stunning|gorgeous} {photo|painting|sketch} of a __animals__
```

### 4. Combine techniques

```
a __styles/painting__ of {1-3$$flowers|trees|mountains|rivers} in a {warm|cool|dramatic} light
```

---

## Syntax Reference

| Syntax                     | Description      | Example                            |
| -------------------------- | ---------------- | ---------------------------------- |
| `{A\|B\|C}`                | Random choice    | `{red\|blue}` → `red`              |
| `{2$$A\|B\|C}`             | Pick N           | `{2$$r\|g\|b}` → `r, g`            |
| `{1-3$$A\|B\|C}`           | Pick N in range  | `{1-3$$r\|g\|b}` → `r, b`          |
| `{2$$ and $$A\|B\|C}`      | Custom separator | → `r and b`                        |
| `{0.5::A\|0.3::B\|0.2::C}` | Weighted         | A picked 50% of the time           |
| `__name__`                 | Wildcard file    | random line from `name.txt`        |
| `__folder/name__`          | Nested wildcard  | random line from `folder/name.txt` |
| `${var=value}`             | Set variable     | `${gem={ruby\|emerald}}`           |
| `${var}`                   | Use variable     | reuses the same pick               |

For the full syntax specification, see the [Dynamic Prompts documentation](https://github.com/adieyal/sd-dynamic-prompts/blob/main/docs/SYNTAX.md).

---

## Settings

Under **Settings → Dynamic Prompts** you'll find:

- **Ignore whitespace** — collapse newlines/tabs/multiple spaces into a single space
- **Save template to metadata** — write the raw prompt template into PNG metadata
- **Write prompts to file** — save generated prompts as `.txt` alongside images
- **Variant bracket syntax** — change `{` and `}` to something else
- **Wildcard wrap syntax** — change `__` to something else
- **Auto purge cache** — reload wildcard files on every generation
- **De-duplication / sorting / shuffling** — control how wildcard values are processed

---

## Credits

This is a stripped-down fork of [sd-dynamic-prompts](https://github.com/adieyal/sd-dynamic-prompts) by [Adiel Ashkenazy](https://github.com/adieyal) and contributors. The core prompt engine is [dynamicprompts](https://github.com/adieyal/dynamicprompts). All original code is under the [MIT License](LICENSE).

---

## License

[MIT](LICENSE)
