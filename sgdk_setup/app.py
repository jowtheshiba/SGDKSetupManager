import os
import shutil
import threading

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RadioButton,
    RadioSet,
    RichLog,
    Static,
)

from sgdk_setup import download, newproject, system_info
from sgdk_setup.installers import haiku as install_haiku
from sgdk_setup.installers import linux as install_linux
from sgdk_setup.installers import macos as install_macos
from sgdk_setup.installers import windows as install_windows

INSTALLERS = {
    system_info.LINUX: install_linux,
    system_info.MACOS: install_macos,
    system_info.WINDOWS: install_windows,
    system_info.HAIKU: install_haiku,
}


def emit_to(log):
    def emit(line):
        log.write(Text(line))
    return log.write


class MainScreen(Screen):
    def compose(self):
        yield Header()
        yield Vertical(
            Static("SGDK Setup Manager", id="title"),
            Static(self.app.status_text(), id="status"),
            Center(Button("Install SGDK", id="install", variant="primary")),
            Center(Button("Create Project", id="create", variant="success")),
            Center(Button("Rescan System", id="rescan")),
            Center(Button("Quit", id="quit")),
            id="main",
        )
        yield Footer()

    def on_mount(self):
        self.refresh_buttons()

    def refresh_buttons(self):
        has_sgdk = self.app.sgdk_dir is not None
        self.query_one("#install", Button).disabled = has_sgdk
        self.query_one("#create", Button).disabled = not has_sgdk

    def on_button_pressed(self, event):
        pressed = event.button.id
        if pressed == "install":
            self.app.push_screen(RepoScreen())
        elif pressed == "create":
            self.app.push_screen(CreateScreen())
        elif pressed == "rescan":
            self.app.rescan()
            self.query_one("#status", Static).update(self.app.status_text())
            self.refresh_buttons()
        elif pressed == "quit":
            self.app.exit()


class RepoScreen(Screen):
    def compose(self):
        yield Header()
        yield Vertical(
            Static("Download SGDK", id="title"),
            Label("Repository URL (edit if the default is unreachable):"),
            Input(value=self.app.repo_url, id="url"),
            RichLog(id="clone-log"),
            Static("", id="clone-status"),
            Horizontal(
                Button("Download", id="clone", variant="primary"),
                Button("Back", id="back"),
                Button("Continue", id="continue", variant="success"),
            ),
            id="repo",
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#continue", Button).disabled = True

    def on_button_pressed(self, event):
        pressed = event.button.id
        if pressed == "back":
            self.app.pop_screen()
        elif pressed == "continue":
            self.app.push_screen(InstallScreen())
        elif pressed == "clone":
            self.start_clone()

    def start_clone(self):
        url = self.query_one("#url", Input).value.strip()
        self.app.repo_url = url
        log = self.query_one("#clone-log", RichLog)
        status = self.query_one("#clone-status", Static)
        self.query_one("#clone", Button).disabled = True
        thread = threading.Thread(target=self.clone_work, args=(url, log, status))
        thread.daemon = True
        thread.start()

    def clone_work(self, url, log, status):
        app = self.app
        write = emit_to(log)
        app.call_from_thread(write, Text("Checking " + url + " ..."))
        if not system_info.git_available():
            app.call_from_thread(status.update, "Git is not installed. Install git first.")
            app.call_from_thread(self.query_one("#clone", Button).remove_class, "disabled")
            return
        if not download.repo_reachable(url):
            app.call_from_thread(
                status.update,
                "Repository is unreachable. Check the URL or enter a custom one.",
            )
            app.call_from_thread(self.enable_clone)
            return
        dest = os.path.join(os.getcwd(), "SGDK")
        if os.path.exists(dest):
            app.call_from_thread(status.update, "Using existing checkout: " + dest)
        else:
            try:
                app.call_from_thread(write, Text("Cloning into " + dest + " ..."))

                def emit(line):
                    app.call_from_thread(write, Text(line))

                download.clone_repo(url, dest, emit)
            except RuntimeError as exc:
                app.call_from_thread(status.update, "Clone failed: " + str(exc))
                app.call_from_thread(self.enable_clone)
                return
        app.sgdk_dir = dest
        app.call_from_thread(status.update, "SGDK sources ready: " + dest)
        app.call_from_thread(self.enable_continue)

    def enable_clone(self):
        self.query_one("#clone", Button).disabled = False

    def enable_continue(self):
        self.query_one("#clone", Button).disabled = False
        self.query_one("#continue", Button).disabled = False


class InstallScreen(Screen):
    def compose(self):
        yield Header()
        installer = self.app.installer
        yield Vertical(
            Static("Install SGDK (" + system_info.os_label(self.app.os_id) + ")", id="title"),
            Static("Press Start Install, progress follows the install phases.", id="phase"),
            ProgressBar(total=len(installer.PHASES), show_eta=False, id="bar"),
            RichLog(id="install-log"),
            Static("", id="install-status"),
            Horizontal(
                Button("Start Install", id="start", variant="primary"),
                Button("Create Project", id="create", variant="success"),
                Button("Back", id="back"),
            ),
            id="install",
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#create", Button).disabled = True

    def on_button_pressed(self, event):
        pressed = event.button.id
        if pressed == "back":
            self.app.pop_screen()
        elif pressed == "create":
            self.app.push_screen(CreateScreen())
        elif pressed == "start":
            self.start_install()

    def start_install(self):
        self.query_one("#start", Button).disabled = True
        thread = threading.Thread(target=self.install_work)
        thread.daemon = True
        thread.start()

    def install_work(self):
        app = self.app
        installer = app.installer
        log = self.query_one("#install-log", RichLog)
        phase_label = self.query_one("#phase", Static)
        status = self.query_one("#install-status", Static)
        bar = self.query_one("#bar", ProgressBar)
        write = emit_to(log)
        total = len(installer.PHASES)
        for index, phase in enumerate(installer.PHASES):
            title = phase[0]
            app.call_from_thread(phase_label.update, "Phase " + str(index + 1) + "/" + str(total) + ": " + title)
            app.call_from_thread(write, Text("Phase " + str(index + 1) + "/" + str(total) + ": " + title))

            def emit(line, app=app, write=write):
                app.call_from_thread(write, Text(line))

            try:
                result = installer.run_phase(index, app.sgdk_dir, emit)
            except Exception as exc:
                app.call_from_thread(status.update, "Failed in " + title + ": " + str(exc))
                app.call_from_thread(self.enable_start)
                return
            app.call_from_thread(write, Text(str(result)))
            app.call_from_thread(bar.update, progress=index + 1)
        found = system_info.find_sgdk(app.os_id)
        if found:
            app.sgdk_dir = found
        app.call_from_thread(status.update, "SGDK installed at " + str(app.sgdk_dir))
        app.call_from_thread(self.enable_create)

    def enable_start(self):
        self.query_one("#start", Button).disabled = False

    def enable_create(self):
        self.query_one("#create", Button).disabled = False


class CreateScreen(Screen):
    def compose(self):
        yield Header()
        haiku = self.app.os_id == system_info.HAIKU
        yield Vertical(
            Static("Create Project", id="title"),
            Static(self.flavor_text(), id="flavor"),
            Label("Project name:"),
            Input(placeholder="hello-world", id="name"),
            self.flavor_widget(haiku),
            RichLog(id="create-log"),
            Static("", id="create-status"),
            Horizontal(
                Button("Create", id="go", variant="primary"),
                Button("Back", id="back"),
            ),
            id="create",
        )
        yield Footer()

    def flavor_text(self):
        if self.app.os_id == system_info.HAIKU:
            return "Haiku target: pick Genio or Paladin. Created in the current folder."
        return "VS Code project with IntelliSense and build tasks. Created in the current folder."

    def flavor_widget(self, haiku):
        if haiku:
            return RadioSet(
                RadioButton("Genio", id="genio"),
                RadioButton("Paladin", id="paladin"),
                id="flavor-pick",
            )
        return Static("Template: Visual Studio Code", id="flavor-pick")

    def on_mount(self):
        try:
            self.query_one("#genio", RadioButton).value = True
        except Exception:
            pass

    def on_button_pressed(self, event):
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "go":
            self.create_project()

    def picked_flavor(self):
        try:
            picked = self.query_one("#flavor-pick", RadioSet).pressed_button
            if picked is not None and picked.id == "paladin":
                return newproject.PALADIN
        except Exception:
            pass
        return newproject.GENIO

    def create_project(self):
        name = self.query_one("#name", Input).value.strip()
        log = self.query_one("#create-log", RichLog)
        status = self.query_one("#create-status", Static)
        write = emit_to(log)
        if not newproject.valid_name(name):
            status.update("Name must match [A-Za-z0-9_-]+.")
            return
        parent = os.getcwd()
        try:
            if self.app.os_id == system_info.HAIKU:
                if self.picked_flavor() == newproject.PALADIN:
                    path, files = newproject.create_paladin_project(parent, name, self.app.sgdk_dir)
                else:
                    path, files = newproject.create_genio_project(parent, name, self.app.sgdk_dir)
            else:
                compiler = shutil.which("m68k-elf-gcc") or ""
                path, files = newproject.create_vscode_project(parent, name, self.app.sgdk_dir, compiler)
        except (ValueError, FileExistsError, OSError) as exc:
            status.update("Failed: " + str(exc))
            return
        write(Text("Created " + path))
        for item in files:
            write(Text("  " + os.path.relpath(item, path)))
        status.update("Project ready: " + path)


class SGDKSetupApp(App):
    TITLE = "SGDK Setup Manager"

    def __init__(self):
        super().__init__()
        self.os_id = system_info.detect_os()
        self.repo_url = system_info.DEFAULT_REPO_URL
        self.installer = INSTALLERS.get(self.os_id)
        self.sgdk_dir = system_info.find_sgdk(self.os_id)
        self.git_ok = system_info.git_available()

    def status_text(self):
        lines = [
            "System: " + system_info.os_label(self.os_id),
            "Git: " + ("found" if self.git_ok else "NOT FOUND") + " " + system_info.git_version(),
        ]
        if self.sgdk_dir:
            lines.append("SGDK: installed at " + self.sgdk_dir)
            lines.append("This manager now works as a project creator.")
        else:
            lines.append("SGDK: not installed")
            lines.append("Choose Install SGDK to download, build and install it.")
        if self.os_id not in INSTALLERS:
            lines.append("No installer for this system.")
        return "\n".join(lines)

    def rescan(self):
        self.git_ok = system_info.git_available()
        self.sgdk_dir = system_info.find_sgdk(self.os_id)

    def on_mount(self):
        self.push_screen(MainScreen())
