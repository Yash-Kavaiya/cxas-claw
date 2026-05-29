"""
Rich-powered output renderer for cxclaw.
Supports table / json / csv output modes and a colour-coded banner.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

# ------------------------------------------------------------------ #
# Banner
# ------------------------------------------------------------------ #

BANNER = """
   ██████╗██╗  ██╗ ██████╗██╗      █████╗ ██╗    ██╗
  ██╔════╝╚██╗██╔╝██╔════╝██║     ██╔══██╗██║    ██║
  ██║      ╚███╔╝ ██║     ██║     ███████║██║ █╗ ██║
  ██║      ██╔██╗ ██║     ██║     ██╔══██║██║███╗██║
  ╚██████╗██╔╝ ██╗╚██████╗███████╗██║  ██║╚███╔███╔╝
   ╚═════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
"""


def print_banner(version: str = "0.2.0") -> None:
    console.print(
        Panel(
            Text(BANNER, style="bold cyan", justify="center"),
            subtitle=f"[dim]CX Agent Studio CLI Agent  v{version}  |  @genai_guru[/dim]",
            border_style="cyan",
            box=box.DOUBLE,
        )
    )


# ------------------------------------------------------------------ #
# Generic renderer
# ------------------------------------------------------------------ #

def render(
    data: list[dict[str, Any]],
    output: str = "table",
    title: str = "",
    columns: list[str] | None = None,
) -> None:
    """
    Render a list of dicts as table / json / csv.
    output: 'table' | 'json' | 'csv'
    """
    if not data:
        console.print("[yellow]No results.[/yellow]")
        return

    if output == "json":
        console.print_json(json.dumps(data, default=str, indent=2))
        return

    if output == "csv":
        _render_csv(data, columns)
        return

    _render_table(data, title, columns)


def _render_table(
    data: list[dict[str, Any]],
    title: str = "",
    columns: list[str] | None = None,
) -> None:
    cols = columns or list(data[0].keys())
    table = Table(
        title=title or None,
        box=box.SIMPLE_HEAD,
        header_style="bold magenta",
        show_lines=False,
    )
    for col in cols:
        table.add_column(col, overflow="fold", no_wrap=False)
    for row in data:
        table.add_row(*[str(row.get(c, "")) for c in cols])
    console.print(table)


def _render_csv(data: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    cols = columns or list(data[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    console.print(buf.getvalue())


# ------------------------------------------------------------------ #
# Convenience wrappers
# ------------------------------------------------------------------ #

def success(msg: str) -> None:
    console.print(f"[bold green]✔[/bold green]  {msg}")


def error(msg: str) -> None:
    console.print(f"[bold red]✘[/bold red]  {msg}")


def info(msg: str) -> None:
    console.print(f"[bold blue]ℹ[/bold blue]  {msg}")


def warn(msg: str) -> None:
    console.print(f"[bold yellow]⚠[/bold yellow]  {msg}")
