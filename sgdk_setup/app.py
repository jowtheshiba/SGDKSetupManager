import os
import shutil
import threading

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
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

from sgdk_setup import blastem, download, newproject, runner, system_info
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
    BINDINGS = [
        ("1", "setup_install", "Install SGDK"),
        ("2", "setup_create", "Create Project"),
        ("3", "setup_rescan", "Rescan System"),
        ("4", "setup_quit", "Quit"),
        ("5", "setup_blastem", "Install BlastEm"),
    ]

    def compose(self):
        yield Header()
        yield Vertical(
            Static("SGDK Setup Manager", id="title"),
            Static(self.app.status_text(), id="status"),
            Static(""),
            Button("Install SGDK", id="install", variant="primary"),
            Button("Create Project", id="create", variant="success"),
            Button("Install BlastEm", id="blastem"),
            Button("Rescan System", id="rescan"),
            Button("Quit", id="quit"),
            id="main",
        )
        yield Footer()

    def on_mount(self):
        self.refresh_buttons()
        if not self.query_one("#install", Button).disabled:
            self.query_one("#install", Button).focus()
        elif not self.query_one("#create", Button).disabled:
            self.query_one("#create", Button).focus()

    def refresh_buttons(self):
        has_sgdk = self.app.sgdk_dir is not None
        self.query_one("#install", Button).disabled = has_sgdk
        self.query_one("#create", Button).disabled = not has_sgdk
        self.query_one("#blastem", Button).disabled = not has_sgdk

    def do_install(self):
        if not self.query_one("#install", Button).disabled:
            self.app.push_screen(RepoScreen())

    def do_create(self):
        if not self.query_one("#create", Button).disabled:
            self.app.push_screen(CreateScreen())

    def do_rescan(self):
        self.app.rescan()
        self.query_one("#status", Static).update(self.app.status_text())
        self.refresh_buttons()

    def do_blastem(self):
        if not self.query_one("#blastem", Button).disabled:
            self.app.push_screen(BlastEmScreen())

    def action_setup_install(self):
        self.do_install()

    def action_setup_create(self):
        self.do_create()

    def action_setup_rescan(self):
        self.do_rescan()

    def action_setup_quit(self):
        self.app.exit()

    def action_setup_blastem(self):
        self.do_blastem()

    def on_button_pressed(self, event):
        pressed = event.button.id
        if pressed == "install":
            self.do_install()
        elif pressed == "create":
            self.do_create()
        elif pressed == "blastem":
            self.do_blastem()
        elif pressed == "rescan":
            self.do_rescan()
        elif pressed == "quit":
            self.app.exit()


class RepoScreen(Screen):
    BINDINGS = [
        ("d", "clone_now", "Download"),
        ("n", "go_next", "Continue"),
        ("b", "go_back", "Back"),
    ]

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
        self.query_one("#clone", Button).focus()

    def action_clone_now(self):
        if not self.query_one("#clone", Button).disabled:
            self.start_clone()

    def action_go_next(self):
        if not self.query_one("#continue", Button).disabled:
            self.app.push_screen(InstallScreen())

    def action_go_back(self):
        self.app.refresh_main()
        self.app.pop_screen()

    def on_button_pressed(self, event):
        pressed = event.button.id
        if pressed == "back":
            self.action_go_back()
        elif pressed == "continue":
            self.action_go_next()
        elif pressed == "clone":
            self.action_clone_now()

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
    BINDINGS = [
        ("s", "start_now", "Start Install"),
        ("c", "make_project", "Create Project"),
        ("b", "go_back", "Back"),
    ]

    def compose(self):
        yield Header()
        installer = self.app.installer
        yield Vertical(
            Static("Install SGDK (" + system_info.os_label(self.app.os_id) + ")", id="title"),
            Static("Press Start Install, progress follows the install phases.", id="phase"),
            ProgressBar(total=len(installer.PHASES), show_eta=False, id="bar"),
            RichLog(id="install-log"),
            Static("", id="install-status"),
            Label("Install to:"),
            Input(value=system_info.default_prefix(self.app.os_id), id="prefix"),
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

    def action_start_now(self):
        if not self.query_one("#start", Button).disabled:
            self.start_install()

    def action_make_project(self):
        if not self.query_one("#create", Button).disabled:
            self.app.push_screen(CreateScreen())

    def action_go_back(self):
        self.app.refresh_main()
        self.app.pop_screen()

    def on_button_pressed(self, event):
        pressed = event.button.id
        if pressed == "back":
            self.action_go_back()
        elif pressed == "create":
            self.action_make_project()
        elif pressed == "start":
            self.action_start_now()

    def start_install(self):
        prefix = self.query_one("#prefix", Input).value.strip()
        if not prefix:
            prefix = system_info.default_prefix(self.app.os_id)
        self.query_one("#start", Button).disabled = True
        thread = threading.Thread(target=self.install_work, args=(prefix,))
        thread.daemon = True
        thread.start()

    def install_work(self, prefix):
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
        app.call_from_thread(phase_label.update, "Installing files to " + prefix + " ...")
        try:
            runner.install_to_prefix(app.sgdk_dir, prefix, emit)
            if not system_info.valid_sgdk_dir(prefix):
                raise runner.PhaseError("Install verification failed at " + prefix + ".")
            cleanup = runner.remove_sources(app.sgdk_dir, prefix)
            app.call_from_thread(write, Text(cleanup))
            system_info.save_install_dir(prefix)
        except Exception as exc:
            app.call_from_thread(status.update, "Install step failed: " + str(exc))
            app.call_from_thread(self.enable_start)
            return
        app.sgdk_dir = prefix
        app.call_from_thread(status.update, "SGDK installed at " + prefix)
        app.call_from_thread(self.enable_create)

    def enable_start(self):
        self.query_one("#start", Button).disabled = False

    def enable_create(self):
        self.query_one("#create", Button).disabled = False


class BlastEmScreen(Screen):
    BINDINGS = [
        ("s", "start_now", "Start Install"),
        ("b", "go_back", "Back"),
    ]

    def compose(self):
        yield Header()
        supported = self.app.os_id != system_info.WINDOWS
        if supported:
            info = (
                "Builds the latest libretro/blastem with GDB fixes into "
                + blastem.install_dir(self.app.sgdk_dir or "")
                + "."
            )
        else:
            info = "Source builds are not supported on Windows. Use a prebuilt binary."
        yield Vertical(
            Static("Install BlastEm (optional)", id="title"),
            Static(info),
            Static("", id="phase"),
            ProgressBar(total=len(blastem.PHASES), show_eta=False, id="bar"),
            RichLog(id="blastem-log"),
            Static("", id="blastem-status"),
            Horizontal(
                Button("Start Install", id="start", variant="primary", disabled=not supported),
                Button("Back", id="back"),
            ),
            id="blastem",
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#start", Button).focus()

    def action_start_now(self):
        if not self.query_one("#start", Button).disabled:
            self.start_install()

    def action_go_back(self):
        self.app.refresh_main()
        self.app.pop_screen()

    def on_button_pressed(self, event):
        if event.button.id == "back":
            self.action_go_back()
        elif event.button.id == "start":
            self.action_start_now()

    def start_install(self):
        self.query_one("#start", Button).disabled = True
        thread = threading.Thread(target=self.install_work)
        thread.daemon = True
        thread.start()

    def install_work(self):
        app = self.app
        log = self.query_one("#blastem-log", RichLog)
        phase_label = self.query_one("#phase", Static)
        status = self.query_one("#blastem-status", Static)
        bar = self.query_one("#bar", ProgressBar)
        write = emit_to(log)
        total = len(blastem.PHASES)
        try:
            for index, phase in enumerate(blastem.PHASES):
                title = phase[0]
                app.call_from_thread(
                    phase_label.update,
                    "Phase " + str(index + 1) + "/" + str(total) + ": " + title,
                )
                app.call_from_thread(write, Text("Phase " + str(index + 1) + "/" + str(total) + ": " + title))

                def emit(line, app=app, write=write):
                    app.call_from_thread(write, Text(line))

                result = blastem.run_phase(index, app.os_id, app.sgdk_dir, emit)
                app.call_from_thread(write, Text(str(result)))
                app.call_from_thread(bar.update, progress=index + 1)
        except Exception as exc:
            blastem.cleanup_work()
            app.call_from_thread(status.update, "Failed: " + str(exc))
            app.call_from_thread(self.enable_start)
            return
        app.call_from_thread(status.update, "BlastEm installed.")
        app.call_from_thread(self.enable_start)

    def enable_start(self):
        self.query_one("#start", Button).disabled = False


class CreateScreen(Screen):
    BINDINGS = [
        ("g", "go_create", "Create"),
        ("b", "go_back", "Back"),
    ]

    def compose(self):
        yield Header()
        haiku = self.app.os_id == system_info.HAIKU
        yield Vertical(
            Static("Create Project", id="title"),
            Static(self.flavor_text(), id="flavor"),
            Label("Project name:"),
            Input(placeholder="hello-world", id="name"),
            Label("Directory:"),
            Input(value=os.getcwd(), id="directory"),
            Label("SGDK location:"),
            Input(value=self.app.sgdk_dir or "", id="gdk"),
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
            return "Haiku target: pick Genio or Paladin. Created in the chosen folder."
        return "VS Code project with IntelliSense and build tasks. Created in the chosen folder."

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
        self.query_one("#go", Button).focus()

    def action_go_create(self):
        self.create_project()

    def action_go_back(self):
        self.app.refresh_main()
        for _ in range(10):
            if isinstance(self.app.screen, MainScreen):
                break
            self.app.pop_screen()

    def on_button_pressed(self, event):
        if event.button.id == "back":
            self.action_go_back()
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
        parent = self.query_one("#directory", Input).value.strip() or os.getcwd()
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as exc:
            status.update("Bad directory: " + str(exc))
            return
        gdk = self.query_one("#gdk", Input).value.strip() or self.app.sgdk_dir
        if not system_info.valid_sgdk_dir(gdk):
            status.update("Not a valid SGDK install: " + str(gdk))
            return
        self.app.sgdk_dir = gdk
        system_info.save_install_dir(gdk)
        try:
            if self.app.os_id == system_info.HAIKU:
                if self.picked_flavor() == newproject.PALADIN:
                    path, files = newproject.create_paladin_project(parent, name, gdk)
                else:
                    path, files = newproject.create_genio_project(parent, name, gdk)
            else:
                compiler = shutil.which("m68k-elf-gcc") or ""
                path, files = newproject.create_vscode_project(
                    parent,
                    name,
                    gdk,
                    compiler,
                    self.app.os_id == system_info.MACOS,
                    self.app.os_id == system_info.LINUX,
                )
        except (ValueError, FileExistsError, OSError) as exc:
            status.update("Failed: " + str(exc))
            return
        write(Text("Created " + path))
        for item in files:
            write(Text("  " + os.path.relpath(item, path)))
        status.update("Project ready: " + path)


class SGDKSetupApp(App):
    TITLE = "SGDK Setup Manager"

    CSS = """
    #main Button {
        width: 30;
    }
    """

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
            if blastem.is_installed(self.sgdk_dir, self.os_id):
                lines.append("BlastEm: installed at " + blastem.install_dir(self.sgdk_dir))
            else:
                lines.append("BlastEm: not installed (optional)")
            lines.append(
                "m68k-elf-gdb: " + ("found" if blastem.gdb_available() else "NOT FOUND")
            )
        else:
            lines.append("SGDK: not installed")
            lines.append("Choose Install SGDK to download, build and install it.")
        if self.os_id not in INSTALLERS:
            lines.append("No installer for this system.")
        return "\n".join(lines)

    def rescan(self):
        self.git_ok = system_info.git_available()
        self.sgdk_dir = system_info.find_sgdk(self.os_id)

    def refresh_main(self):
        self.rescan()
        for screen in self.screen_stack:
            if isinstance(screen, MainScreen):
                screen.query_one("#status", Static).update(self.status_text())
                screen.refresh_buttons()

    def on_mount(self):
        self.push_screen(MainScreen())
