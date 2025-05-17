"""UI utilities for the CLI."""
import asyncio
from contextlib import suppress

from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll, Container
from textual.widgets import Header, Footer, Static

from smarttel.seestar.client import SeestarClient


class SeestarUI(App):
    """Seestar UI."""

    CSS_PATH = "ui.tcss"
    TITLE = "SeestarUI"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, host, port, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.client = SeestarClient(self.host, self.port, debug=True)
        self.update_title()
        self.events: list[str] = []
        self.responses: list[str] = []

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container():
            with VerticalScroll():
                yield Static(id="response")
                yield Static(id="events")
        yield Footer()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = (
            'textual-dark' if self.theme == 'textual-light' else 'textual-light'
        )

    def update_title(self, i=0) -> None:
        """Update the app title."""
        self.title = f"SeestarUI ({self.host}:{self.port} {i})"
        self.sub_title = "Connected" if self.client.is_connected else "Disconnected"

    async def on_mount(self) -> None:
        """Event handler for when the app loads."""
        print("App loaded")
        asyncio.create_task(self.runner())

    async def runner(self):
        await self.client.connect()

        response_box = self.query_one("#response", Static)
        event_box = self.query_one("#events", Static)
        i = 0
        while self.client.is_connected:
            i += 1
            msg = await self.client.recv()
            if msg is not None:
                print(f'----> Received: {msg}')
                # self.responses.append(str(msg))
                response_box.update(str(msg))
            with suppress(IndexError):
                ev = self.client.recent_events.popleft()
                event_box.update(str(ev))
                # self.events.append(str(ev))
                # event_box.update("\n".join(self.events) + "\n")
            self.update_title(i)
            await asyncio.sleep(0.1)

        await self.client.disconnect()
