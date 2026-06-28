<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0f172a&height=180&section=header&text=Exam%20Agent&fontSize=42&fontColor=38bdf8&animation=fadeIn&fontAlignY=35&desc=AI-Powered%20PDF%20Exam%20Solver&descSize=16&descColor=94a3b8" width="100%" />

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)]()

**Extract · Detect · Solve · Report**

[Features](#-features) · [Installation](#-installation) · [Usage](#-usage) · [Architecture](#-architecture) · [Examples](#-examples)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **PDF Extraction** | Extracts text from PDF files with pdfplumber |
| 🔍 **AI Question Detection** | Automatically detects and separates exam questions |
| 🧠 **AI Solver** | Solves each question with step-by-step reasoning |
| ⚡ **Parallel Processing** | Solves up to 3 questions simultaneously |
| 🔄 **Auto Retry** | 3 attempts per question with exponential backoff |
| 💾 **Resume Support** | Cache system — resume from where you stopped |
| 📊 **Confidence Scoring** | Each answer includes 0-100% confidence score |
| 🎨 **HTML Report** | Beautiful responsive RTL report with progress bars |
| 🖥️ **Rich CLI** | Professional terminal UI with spinners, tables, and progress |
| 🌐 **Built-in Server** | One command to serve the report in browser |

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/TssHack/exam-agent.git
cd exam-agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> **requirements.txt**
> ```
> pdfplumber>=0.11.0
> requests>=2.31.0
> rich>=13.0.0
> ```

---

## 🚀 Usage

### Solve an Exam

```bash
python main.py solve exam.pdf
```

### Solve Fresh (Ignore Cache)

```bash
python main.py solve exam.pdf --fresh
```

### View Report

```bash
python main.py serve
# → http://localhost:3000/report.html
```

### Clear Cache

```bash
python main.py clear
```

### Help

```bash
python main.py help
```

---

## 🏗 Architecture

```
exam-agent/
├── config.py      # Constants, API config, logging setup
├── pipeline.py    # Extract → Clean → Split → Solve → Aggregate
├── html_gen.py    # HTML report generator
├── main.py        # CLI interface with Rich terminal UI
├── .cache/        # Intermediate JSON results (auto-generated)
└── reports/       # Final HTML + JSON reports (auto-generated)
```

### Pipeline Flow

```
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────┐
│  📄 PDF   │───▶│  🧹 Clean │───▶│ 🔍 AI Split  │───▶│ 🧠 Solve │
└──────────┘    └──────────┘    └──────────────┘    └────┬─────┘
                                                         │
                    ┌──────────────┐    ┌──────────┐      │
                    │  🎨 HTML     │◀───│ 📊 Merge  │◀─────┘
                    └──────────────┘    └──────────┘
```

### Key Design Decisions

- **Cache-per-question**: Each solved question is saved individually — if the process crashes, it resumes seamlessly
- **Concurrency limit of 3**: Prevents API rate-limiting while keeping speed
- **JSON-first**: All intermediate data stored as JSON for debuggability
- **No framework overhead**: Pure Python with `requests` + `rich` — zero bloat

---

## 📸 Examples

### CLI Output

```
    ╔═══════════════════════════════════════════════╗
    ║     EXAM AGENT v1.0.0                        ║
    ║     PDF Exam Solver · AI-Powered             ║
    ╚═══════════════════════════════════════════════╝

  ✓ Raw text extracted  (12,847 chars)
  ✓ Text cleaned        (11,203 chars)
  ✓ 12 questions detected

    ✓ Q  1  f'(x) = 6x + 2                                90%
    ✓ Q  2  {2, 3}                                        95%
    ✓ Q  3  (500/3)π cm³                                   85%
    ...

  Q  1 ████████████████████░░  90% HIGH
  Q  2 █████████████████████░  95% HIGH
  Q  3 ███████████████████░░░  85% HIGH
```

### HTML Report

> Responsive RTL design with step-by-step solutions, color-coded confidence indicators, and clean typography.

---

## ⚙️ Configuration

Edit `config.py` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `https://api.binjie.fun/api/generateStream` | AI endpoint |
| `MAX_CONCURRENCY` | `3` | Parallel solve limit |
| `MAX_RETRIES` | `3` | Retry attempts per question |
| `RETRY_DELAY` | `2` | Base delay in seconds |

---

## 🛠 Tech Stack

| Tool | Purpose |
|------|---------|
| `pdfplumber` | PDF text extraction |
| `requests` | HTTP calls to AI API |
| `rich` | Terminal UI (tables, progress, spinners) |
| `concurrent.futures` | Thread pool for parallel solving |

---

## 📋 TODO

- [ ] OCR fallback for scanned PDFs (Tesseract)
- [ ] Support for images/diagrams in questions
- [ ] Export to PDF report
- [ ] Multiple AI provider support (OpenAI, Anthropic)
- [ ] Web UI dashboard
- [ ] Batch processing folder of PDFs

---

## 👤 Author

<div align="center">

**Ehsan Fazli**

[![GitHub](https://img.shields.io/badge/GitHub-TssHack-181717?style=flat-square&logo=github)](https://github.com/TssHack)
[![Telegram](https://img.shields.io/badge/Telegram-ABj0o-26A5E4?style=flat-square&logo=telegram)](https://t.me/ABj0o)
[![Email](https://img.shields.io/badge/Email-ehsanfazlinejad@gmail.com-EA4335?style=flat-square&logo=gmail)](mailto:ehsanfazlinejad@gmail.com)

</div>

---

<div align="center">

**If you found this useful, leave a ⭐**

</div>

---