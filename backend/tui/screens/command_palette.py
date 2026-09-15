"""Searchable command palette for Sovereign TUI."""
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

class CommandModal(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "dismiss_modal", "Close")]
    
    PALETTE_COMMANDS: list[tuple[str, str]] = [
        ("Ask Agent", "agent"), 
        ("Upload File", "upload-file"), 
        ("Upload Folder", "upload-folder"), 
        ("Open Documents", "documents"), 
        ("Add Ready to Knowledge", "index-all"), 
        ("Ask Knowledge", "knowledge"), 
        ("Analyze Data", "data"), 
        ("Run Python", "sandbox"), 
        ("Open Artifacts", "artifacts"), 
        ("Open Jobs", "jobs"), 
        ("Refresh", "refresh"), 
        ("Help", "help")
    ]
    
    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield Input(placeholder="Search commands...", id="command-search")
            yield OptionList(id="command-palette-list")
            
    def on_mount(self) -> None:
        self.populate_options(self.PALETTE_COMMANDS)
        self.query_one("#command-search", Input).focus()
        
    def populate_options(self, commands: list[tuple[str, str]]) -> None:
        option_list = self.query_one("#command-palette-list", OptionList)
        option_list.clear_options()
        for label, cmd_id in commands:
            option_list.add_option(Option(label, id=cmd_id))
            
    @on(Input.Changed, "#command-search")
    def filter_commands(self) -> None:
        query = self.query_one("#command-search", Input).value.lower()
        filtered = [(label, cmd_id) for label, cmd_id in self.PALETTE_COMMANDS if query in label.lower()]
        self.populate_options(filtered)
        
    @on(Input.Submitted, "#command-search")
    def submit_search(self) -> None:
        option_list = self.query_one("#command-palette-list", OptionList)
        if option_list.option_count > 0:
            idx = option_list.highlighted if option_list.highlighted is not None else 0
            option = option_list.get_option_at_index(idx)
            self.dismiss(option.id)
            
    @on(OptionList.OptionSelected, "#command-palette-list")
    def execute_command(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)
        
    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
        
    def on_key(self, event) -> None:
        if event.key == "down" and isinstance(self.focused, Input):
            self.query_one("#command-palette-list", OptionList).focus()
            event.stop()
