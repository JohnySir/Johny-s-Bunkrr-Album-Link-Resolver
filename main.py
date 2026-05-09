import asyncio
import os
import sys
import random
from typing import List, Optional

import aiohttp
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Center, Middle
from textual.widgets import Header, Footer, Input, Button, Static, Label, ProgressBar, RichLog, ListItem, ListView, LoadingIndicator
from textual.binding import Binding
from textual.screen import Screen
from textual import work

from resolver import BunkrResolver, check_link, sanitize

class SplashScreen(Screen):
    """A visually stunning splash screen with a glitchy animation."""
    
    CSS = """
    SplashScreen {
        align: center middle;
        background: #000000;
    }

    #logo_container {
        width: auto;
        height: auto;
        align: center middle;
    }

    #logo_wrapper {
        width: 62;
        height: 6;
        margin-bottom: 1;
    }

    #splash_logo {
        width: 100%;
        height: 100%;
        text-style: bold;
        color: #ff00ff;
    }

    #loading_text {
        color: #00ffff;
        text-style: italic;
        text-align: center;
        width: 62;
    }

    #splash_bar {
        width: 40;
        color: #ff00ff;
        margin-top: 1;
    }
    """

    LOGO_BUNKR = r"""
██████╗ ██╗   ██╗███╗   ██╗██╗  ██╗██████╗ ██████╗ 
██╔══██╗██║   ██║████╗  ██║██║ ██╔╝██╔══██╗██╔══██╗
██████╔╝██║   ██║██╔██╗ ██║█████╔╝ ██████╔╝██████╔╝
██╔══██╗██║   ██║██║╚██╗██║██╔═██╗ ██╔══██╗██╔══██╗
██████╔╝╚██████╔╝██║ ╚████║██║  ██╗██║  ██║██║  ██║
╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝""".strip("\n")

    LOGO_JOHNY = r"""
     ██╗ ██████╗ ██╗  ██╗███╗   ██╗██╗   ██╗
     ██║██╔═══██╗██║  ██║████╗  ██║╚██╗ ██╔╝
     ██║██║   ██║███████║██╔██╗ ██║ ╚████╔╝ 
██   ██║██║   ██║██╔══██║██║╚██╗██║  ╚██╔╝  
╚█████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║   
 ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝      """.strip("\n")

    def compose(self) -> ComposeResult:
        with Vertical(id="logo_container"):
            with Container(id="logo_wrapper"):
                yield Static(self.LOGO_BUNKR, id="splash_logo")
            yield Label("INITIALIZING CORE SYSTEMS...", id="loading_text")
            yield ProgressBar(total=100, id="splash_bar", show_eta=False)

    def on_mount(self) -> None:
        self.query_one("#splash_bar").advance(0)
        self.run_worker(self.animate_loading())

    async def animate_loading(self) -> None:
        bar = self.query_one("#splash_bar")
        text = self.query_one("#loading_text")
        logo = self.query_one("#splash_logo")
        
        steps = 50
        for i in range(steps + 1):
            progress = (i / steps) * 100
            
            # Update bar and text normally
            bar.progress = progress
            if progress > 20 and progress <= 50: text.update("ESTABLISHING ENCRYPTED TUNNEL...")
            elif progress > 50 and progress <= 80: text.update("BYPASSING CDN RESTRICTIONS...")
            elif progress > 80: text.update("DECRYPTING API HANDSHAKE...")
            
            # Blending effect: Phase between Johny and Bunkr
            # Use hex with alpha to avoid rgba parsing issues
            alpha = int((0.5 + (i % 5) / 10) * 255)
            alpha_hex = f"{alpha:02x}"
            
            if (i // 5) % 2 == 0:
                # Show Johny (Cyan)
                logo.update(self.LOGO_JOHNY)
                logo.styles.color = f"#00ffff{alpha_hex}"
            else:
                # Show Bunkr (Magenta)
                logo.update(self.LOGO_BUNKR)
                logo.styles.color = f"#ff00ff{alpha_hex}"
            
            await asyncio.sleep(0.04)

        await asyncio.sleep(0.1)
        self.app.pop_screen()

class ResolverApp(App):
    """A Textual app to resolve Bunkr albums with style."""

    CSS = """
    Screen {
        background: #1a1a1a;
    }

    #main_container {
        padding: 1 2;
    }

    .title {
        text-align: center;
        width: 100%;
        color: #ff00ff;
        text-style: bold;
        margin-bottom: 1;
    }

    #input_container {
        height: auto;
        margin-bottom: 1;
        border: round #333;
        padding: 1;
    }

    Input {
        width: 100%;
        border: none;
        background: #262626;
    }

    Input:focus {
        border: none;
    }

    #stats_container {
        height: 3;
        margin-bottom: 1;
        content-align: center middle;
    }

    .stat-box {
        width: 25%;
        text-align: center;
        background: #262626;
        color: #00ffff;
        margin: 0 1;
        border: solid #333;
    }

    #progress_container {
        height: 3;
        margin-bottom: 1;
        padding: 0 1;
        align: center middle;
    }

    ProgressBar {
        width: 1fr;
        color: #ff00ff;
    }

    #working_indicator {
        width: 5;
        height: 1;
        color: #00ffff;
        display: none;
        margin-left: 1;
    }

    RichLog {
        height: 1fr;
        border: round #333;
        background: #0d0d0d;
        color: #cccccc;
    }

    .success { color: #00ff00; }
    .error { color: #ff0000; }
    .info { color: #00ffff; }
    .warning { color: #ffff00; }

    #help_label {
        text-align: center;
        width: 100%;
        color: #666;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("q", "quit", "Quit", show=False),
        Binding("ctrl+l", "clear_log", "Clear Log", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main_container"):
            yield Label("Johny's BUNKR LINK RESOLVER", classes="title")
            
            with Vertical(id="input_container"):
                yield Label("Album URL:")
                yield Input(placeholder="https://bunkr.su/a/...", id="url_input")
            
            with Horizontal(id="stats_container"):
                yield Static("Found: 0", id="stat_found", classes="stat-box")
                yield Static("Resolved: 0", id="stat_resolved", classes="stat-box")
                yield Static("Failed: 0", id="stat_failed", classes="stat-box")
                yield Static("Status: BOOORING..😴", id="stat_status", classes="stat-box")

            with Horizontal(id="progress_container"):
                yield ProgressBar(total=100, show_eta=True, id="progress_bar")
                yield LoadingIndicator(id="working_indicator")
            
            yield RichLog(id="log_view", highlight=True, markup=True)
            yield Label("Press [bold]CTRL+C[/] or [bold]Q[/] to exit", id="help_label")
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(SplashScreen())
        self.log_message("[bold info]Application started. Ready to resolve.[/]")
        self.query_one("#url_input").focus()

    def log_message(self, message: str) -> None:
        log_view = self.query_one("#log_view", RichLog)
        log_view.write(message)

    def action_clear_log(self) -> None:
        self.query_one("#log_view", RichLog).clear()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        url = event.value.strip()
        if not url:
            return
        
        if "bunkr" not in url and "/a/" not in url:
            self.log_message("[bold error]Invalid Bunkr URL format.[/]")
            return

        event.input.value = ""
        self.start_resolution(url)

    @work(exclusive=True)
    async def start_resolution(self, url: str) -> None:
        self.query_one("#stat_status").update("Status: AT WORK")
        self.query_one("#stat_found").update("Found: 0")
        self.query_one("#stat_resolved").update("Resolved: 0")
        self.query_one("#stat_failed").update("Failed: 0")
        self.query_one("#working_indicator").styles.display = "block"
        
        try:
            async with aiohttp.ClientSession() as session:
                resolver = BunkrResolver(session)
                self.log_message(f"[info]Fetching album info: {url}[/]")
                
                album_name, items = await resolver.fetch_album_info(url)
                
                if not items:
                    self.log_message("[bold error]No items found or failed to fetch album metadata.[/]")
                    return

                self.query_one("#stat_found").update(f"Found: {len(items)}")
                self.log_message(f"[success]Found {len(items)} items in '{album_name or 'Unknown Album'}'[/]")
                
                pbar = self.query_one("#progress_bar", ProgressBar)
                pbar.update(total=len(items), progress=0)
                
                resolved_urls = []
                failed_count = 0
                # Increased concurrency for large albums, but kept safe to avoid 429s
                sem = asyncio.Semaphore(12)

                async def resolve_item(item):
                    async with sem:
                        try:
                            res = await resolver.get_direct_url(item, url)
                            return res
                        except Exception:
                            return None

                self.log_message(f"[info]Starting concurrent resolution with 12 workers...[/]")
                
                tasks = [resolve_item(item) for item in items]
                
                # Use a counter to update UI in batches for very large albums to prevent lag
                batch_size = max(1, len(items) // 100)
                
                for i, task in enumerate(asyncio.as_completed(tasks), 1):
                    res = await task
                    if res:
                        resolved_urls.append(res)
                    else:
                        failed_count += 1
                    
                    if i % batch_size == 0 or i == len(items):
                        self.query_one("#stat_resolved").update(f"Resolved: {len(resolved_urls)}")
                        self.query_one("#stat_failed").update(f"Failed: {failed_count}")
                        pbar.advance(i - pbar.progress)

                if not resolved_urls:
                    self.log_message("[bold error]Failed to resolve any direct links.[/]")
                    return

                # Link check
                check_url = random.choice(resolved_urls)
                self.log_message(f"[info]Validating random link health...[/]")
                is_ok = await check_link(session, check_url)
                
                if is_ok:
                    self.log_message("[bold success]LINK CHECK: PASSED[/]")
                else:
                    self.log_message("[bold warning]LINK CHECK: FAILED (Link may be expired or restricted)[/]")

                # Export
                safe_name = sanitize(album_name)
                filename = f"{safe_name}.txt"
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(filename):
                    filename = f"{base} ({counter}){ext}"
                    counter += 1

                with open(filename, "w", encoding="utf-8") as f:
                    for rurl in resolved_urls:
                        f.write(rurl + "\n")
                
                self.log_message(f"[bold success]Exported {len(resolved_urls)} links to {filename}[/]")
                
        except Exception as e:
            self.log_message(f"[bold error]Error: {str(e)}[/]")
        finally:
            self.query_one("#stat_status").update("Status: BOOORING..😴")
            self.query_one("#working_indicator").styles.display = "none"

if __name__ == "__main__":
    # Ensure sys.path includes the resolver module
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    app = ResolverApp()
    app.run()
