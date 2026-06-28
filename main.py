#!/usr/bin/env python3
import sys
import os
import json
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress, SpinnerColumn, BarColumn,
    TaskProgressColumn, TextColumn, TimeElapsedColumn,
)
from rich.text import Text
from rich.align import Align
from rich.box import SIMPLE, ROUNDED

from config import log, CACHE_DIR, REPORTS_DIR
from pipeline import extract_text, clean_text, split_questions, solve_one, solve_all, aggregate
from html_gen import render_html

console = Console()

BANNER = """
[bold cyan]
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║     [white]EXAM[/white] [bold yellow]AGENT[/bold yellow] [dim]v1.0.0[/dim]                    ║
    ║     [dim]PDF Exam Solver · AI-Powered[/dim]           ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
[/bold cyan]
"""

DIVIDER = "[dim]" + "─" * 52 + "[/dim]"


def print_banner():
    console.print(BANNER)


def print_section(title: str, icon: str = "◆"):
    console.print()
    console.print(Panel(
        f"[bold white]{icon}  {title}[/bold white]",
        border_style="cyan", padding=(0, 2), expand=False,
    ))


def clear_cache():
    files = list(Path(CACHE_DIR).glob("*"))
    if not files:
        console.print("[dim]  Cache is already empty.[/dim]")
        return
    with Progress(
        TextColumn("  [dim]Removing[/dim]"),
        BarColumn(bar_width=20, style="red", complete_style="bright_red"),
        TaskProgressColumn(),
        console=console,
    ) as prog:
        task = prog.add_task("", total=len(files))
        for f in files:
            f.unlink()
            prog.advance(task)
    console.print(f"  [green bold]✓[/green bold] [white]{len(files)} cache files removed.[/white]")
    console.print()


def run(pdf_path: str, fresh: bool = False):
    print_banner()

    if not os.path.isfile(pdf_path):
        console.print(f"  [bold red]✗[/bold red] File not found: [white]{pdf_path}[/white]")
        sys.exit(1)

    file_size = os.path.getsize(pdf_path)
    size_str = (
        f"{file_size / 1024:.1f} KB"
        if file_size < 1024 * 1024
        else f"{file_size / (1024 * 1024):.1f} MB"
    )

    info = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    info.add_column(style="dim", width=18)
    info.add_column(style="white")
    info.add_row("TARGET FILE", pdf_path)
    info.add_row("FILE SIZE", size_str)
    info.add_row("FRESH MODE", "ON" if fresh else "OFF")
    info.add_row("MAX WORKERS", "3")
    info.add_row("MAX RETRIES", "3")
    console.print(Panel(
        info, title="[bold]Session Info[/bold]",
        border_style="dim", padding=(1, 2), expand=False,
    ))

    if fresh:
        clear_cache()

    # ── Step 1 & 2 ──
    print_section("EXTRACTING TEXT", "📄")
    with console.status("[bold cyan]Reading PDF pages...[/bold cyan]", spinner="dots"):
        raw_text = extract_text(pdf_path)
    console.print(f"  [green bold]✓[/green bold] [white]Raw text extracted[/white]  [dim]({len(raw_text):,} chars)[/dim]")

    with console.status("[bold cyan]Cleaning & normalizing...[/bold cyan]", spinner="dots"):
        clean = clean_text(raw_text)
    console.print(f"  [green bold]✓[/green bold] [white]Text cleaned[/white]  [dim]({len(clean):,} chars)[/dim]")

    # ── Step 3 ──
    print_section("DETECTING QUESTIONS", "🔍")
    with console.status("[bold cyan]Sending to AI for question detection...[/bold cyan]", spinner="bouncingBar"):
        questions = split_questions(clean)

    qt = Table(
        title="[bold white]Detected Questions[/bold white]",
        box=SIMPLE, header_style="bold cyan",
        border_style="dim", padding=(0, 1), expand=False,
    )
    qt.add_column("#", style="dim", width=4, justify="center")
    qt.add_column("Preview", style="white", max_width=70, no_wrap=True)
    for q in questions:
        preview = q["question"][:65] + "..." if len(q["question"]) > 65 else q["question"]
        qt.add_row(str(q["id"]), preview)
    console.print()
    console.print(qt)
    console.print(f"\n  [green bold]✓[/green bold] [white]{len(questions)} questions detected[/white]")

    # ── Step 4 ──
    print_section("SOLVING QUESTIONS", "🧠")

    already = [
        f for f in os.listdir(CACHE_DIR)
        if f.startswith("answer_") and f.endswith(".json")
    ]
    if already:
        console.print(f"  [dim]↳ {len(already)} answers loaded from cache[/dim]")

    to_solve = [
        q for q in questions
        if not os.path.exists(os.path.join(CACHE_DIR, f"answer_{q['id']}.json"))
    ]

    if to_solve:
        console.print(f"  [cyan]↳ {len(to_solve)} questions to solve (max 3 parallel)[/cyan]")
        console.print()

        lock = threading.Lock()

        def solve_and_track(q):
            result = solve_one(q)
            conf = result.get("confidence", 0)
            with lock:
                prog.advance(task)
            ok = conf > 0
            icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
            ans = result["final_answer"][:50]
            console.print(f"    {icon} [dim]Q{q['id']:>3}[/dim]  {ans:<50}  [dim]{conf}%[/dim]")
            return result

        with Progress(
            SpinnerColumn(spinner_name="dots", style="cyan"),
            TextColumn("[bold white]{task.description}[/bold white]"),
            BarColumn(
                bar_width=30, style="dim",
                complete_style="green", finished_style="bright_green",
            ),
            TaskProgressColumn(style="white"),
            TimeElapsedColumn(),
            console=console,
        ) as prog:
            task = prog.add_task("Solving...", total=len(to_solve))
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {pool.submit(solve_and_track, q): q for q in to_solve}
                for f in as_completed(futures):
                    try:
                        f.result()
                    except Exception as e:
                        q = futures[f]
                        console.print(f"    [red]✗[/red] [dim]Q{q['id']:>3}[/dim]  Failed: {e}")

    # ── Step 5 ──
    print_section("AGGREGATING RESULTS", "📊")
    with console.status("[bold cyan]Merging results...[/bold cyan]", spinner="dots"):
        answers = solve_all(questions)
        data = aggregate(answers)

    solved_n = sum(1 for a in answers if a.get("confidence", 0) > 0)
    failed_n = len(answers) - solved_n

    st = Table(
        title="[bold white]Solve Summary[/bold white]",
        box=SIMPLE, header_style="bold cyan",
        border_style="dim", padding=(0, 1), expand=False,
    )
    st.add_column("Metric", style="dim", width=22)
    st.add_column("Value", style="bold white", justify="center")
    st.add_row("Total Questions", str(data["count"]))
    st.add_row("Solved", f"[green]{solved_n}[/green]")
    st.add_row("Failed", f"[red]{failed_n}[/red]" if failed_n else "[green]0[/green]")
    st.add_row("Avg Confidence", f"[yellow]{data['average_confidence']}%[/yellow]")
    console.print()
    console.print(st)

    console.print()
    console.print("[bold white]Confidence Breakdown:[/bold white]")
    console.print()
    for a in answers:
        conf = a.get("confidence", 0)
        filled = int(conf / 5)
        empty = 20 - filled
        if conf >= 70:
            c, label = "green", "HIGH"
        elif conf >= 40:
            c, label = "yellow", "MID"
        else:
            c, label = "red", "LOW"
        bar = f"[{c}]{'█' * filled}[dim]{'░' * empty}[/dim][/{c}]"
        console.print(f"  [dim]Q{a['id']:>3}[/dim] {bar} [bold {c}]{conf:>3}%[/bold {c}] [dim]{label}[/dim]")

    # ── Step 6 ──
    print_section("GENERATING REPORT", "🎨")
    with console.status("[bold cyan]Rendering HTML report...[/bold cyan]", spinner="dots"):
        html_path = render_html(data)

    json_path = os.path.join(REPORTS_DIR, "result.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    console.print(f"  [green bold]✓[/green bold] [white]HTML →[/white] [cyan]{html_path}[/cyan]")
    console.print(f"  [green bold]✓[/green bold] [white]JSON →[/white] [cyan]{json_path}[/cyan]")

    # ── Done ──
    console.print(DIVIDER)
    console.print()
    console.print(Align.center(Panel(
        "[bold green]ALL DONE[/bold green]\n\n"
        "[white]Open in browser:[/white]\n"
        "[bold cyan underline]http://localhost:3000/report.html[/bold cyan underline]\n\n"
        "[dim]Run: python main.py serve[/dim]",
        border_style="green", padding=(1, 3), expand=False,
    )))
    console.print()


def serve():
    print_banner()
    import http.server
    import socketserver
    os.chdir(REPORTS_DIR)
    port = 3000
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        console.print()
        console.print(Panel(
            f"[bold green]● Server running[/bold green]\n\n"
            f"[bold white underline]http://localhost:{port}/report.html[/bold white underline]\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            border_style="green", padding=(1, 3), expand=False,
        ))
        console.print()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n  [dim]Server stopped.[/dim]\n")


def show_help():
    print_banner()
    ht = Table(
        title="[bold white]Commands[/bold white]",
        box=ROUNDED, header_style="bold cyan",
        border_style="cyan", padding=(0, 2), expand=False,
    )
    ht.add_column("Command", style="bold yellow", width=38)
    ht.add_column("Description", style="white")
    ht.add_row("solve <file.pdf>", "Extract, detect, and solve all questions")
    ht.add_row("solve <file.pdf> --fresh", "Same but ignore cached results")
    ht.add_row("serve", "Start HTTP server to view report")
    ht.add_row("clear", "Remove all cached intermediate files")
    ht.add_row("help", "Show this help message")
    console.print()
    console.print(ht)
    console.print()


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        show_help()
        sys.exit(0)

    cmd = args[0]

    if cmd == "solve":
        fresh = "--fresh" in args
        pdf = None
        for a in args[1:]:
            if not a.startswith("--"):
                pdf = a
                break
        if not pdf:
            console.print("[bold red]✗[/bold red] [white]No PDF file specified.[/white]")
            console.print("[dim]  Usage: python main.py solve <file.pdf>[/dim]")
            sys.exit(1)
        run(pdf, fresh)

    elif cmd == "serve":
        serve()

    elif cmd == "clear":
        print_banner()
        clear_cache()

    else:
        console.print(f"[bold red]✗[/bold red] [white]Unknown command:[/white] [yellow]{cmd}[/yellow]")
        console.print("[dim]  Run: python main.py help[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()