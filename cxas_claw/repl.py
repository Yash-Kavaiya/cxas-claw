"""
Interactive REPL for cxclaw.
Supports /commands for quick navigation and chat turns forwarded to the agent.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from cxas_claw.renderer import success, error, info, warn

console = Console()

HELP_TEXT = """
Available REPL commands:
  /help           Show this help text
  /history        Print conversation history
  /reset          Start a new session (new session ID)
  /session        Show current session ID
  /exit  /quit    Exit the REPL

Any other input is sent to the agent as a chat message.
"""


class CXASRepl:
    def __init__(self, scratchpad, agent_name: str = "agent"):
        self.scratchpad = scratchpad
        self.agent_name = agent_name

    def run(self) -> None:
        info(f"Starting REPL with agent [bold cyan]{self.agent_name}[/bold cyan]")
        info(f"Session ID: [dim]{self.scratchpad.session_id}[/dim]")
        console.print("[dim]Type /help for commands, /exit to quit.[/dim]\n")

        while True:
            try:
                user_input = Prompt.ask("[bold green]you[/bold green]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Exiting REPL.[/dim]")
                break

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit"):
                console.print("[dim]Goodbye.[/dim]")
                break
            elif user_input == "/help":
                console.print(HELP_TEXT)
            elif user_input == "/history":
                for i, turn in enumerate(self.scratchpad.dump_history(), 1):
                    console.print(f"[dim]{i}.[/dim] [green]you[/green]: {turn['user']}")
                    console.print(f"   [cyan]{self.agent_name}[/cyan]: {turn['agent']}")
            elif user_input == "/reset":
                self.scratchpad.reset()
                success(f"New session started: {self.scratchpad.session_id}")
            elif user_input == "/session":
                info(f"Session ID: {self.scratchpad.session_id}")
            elif user_input.startswith("/"):
                warn(f"Unknown command '{user_input}'. Type /help for options.")
            else:
                try:
                    response = self.scratchpad.send(user_input)
                    console.print(f"[bold cyan]{self.agent_name}[/bold cyan]: {response}\n")
                except Exception as exc:
                    error(f"Agent error: {exc}")
