import os
import shutil
import subprocess
import tempfile

from sgdk_setup import system_info
from sgdk_setup.runner import PhaseError, run_cmd

REPO = "https://github.com/libretro/blastem"
PATCH_FILES = (
    "01-gdb-remote-tolerance.patch",
    "02-font-mac-stdout.patch",
    "03-vdp-read-no-debugger.patch",
)

PHASES = [
    ("Fetch sources", "Clone the latest libretro/blastem commit."),
    ("Apply patches", "Apply the GDB stub and stdout fixes."),
    ("Check dependencies", "Verify compiler, SDL2 and GLEW."),
    ("Build", "Compile the native BlastEm binary."),
    ("Install to SDK", "Copy BlastEm into the SGDK folder."),
    ("Verify", "Check the installed binary runs."),
]

_WORK = {}


def patches_dir():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "blastem", "patches")


def exe_name(os_id):
    if os_id == system_info.WINDOWS:
        return "blastem.exe"
    return "blastem"


def install_dir(gdk):
    return os.path.join(gdk, "blastem")


def binary_path(gdk, os_id):
    return os.path.join(install_dir(gdk), exe_name(os_id))


def is_installed(gdk, os_id):
    path = binary_path(gdk, os_id)
    if not os.path.isfile(path):
        return False
    if os_id == system_info.WINDOWS:
        return True
    return os.access(path, os.X_OK)


def gdb_available():
    return shutil.which("m68k-elf-gdb") is not None


def cleanup_work():
    tmp = _WORK.pop("tmp", None)
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)


def jobs():
    try:
        return str(os.cpu_count() or 4)
    except NotImplementedError:
        return "4"


def run_phase(index, os_id, gdk, emit):
    if os_id == system_info.WINDOWS:
        raise PhaseError(
            "BlastEm from source is not supported on Windows. "
            "Use a prebuilt Windows binary instead."
        )
    if index == 0:
        return fetch(gdk, emit)
    if index == 1:
        return apply_patches(emit)
    if index == 2:
        return check_deps(os_id, emit)
    if index == 3:
        return build(emit)
    if index == 4:
        return install(os_id, gdk, emit)
    if index == 5:
        return verify(os_id, gdk, emit)
    raise IndexError("Unknown phase " + str(index))


def fetch(gdk, emit):
    cleanup_work()
    tmp = tempfile.mkdtemp(prefix="blastem-build.")
    src = os.path.join(tmp, "src")
    run_cmd(["git", "clone", "--depth", "1", REPO, src], tmp, emit)
    proc = subprocess.run(
        ["git", "-C", src, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    _WORK["tmp"] = tmp
    _WORK["src"] = src
    return "Commit " + proc.stdout.strip() + "."


def apply_patches(emit):
    src = _WORK["src"]
    if shutil.which("patch") is None:
        raise PhaseError("Missing tool: patch.")
    for name in PATCH_FILES:
        path = os.path.join(patches_dir(), name)
        if not os.path.isfile(path):
            raise PhaseError("Patch file missing: " + path + ".")
        run_cmd(["patch", "-N", "-s", "-p1", "-i", path], src, emit)
        emit("Applied " + name + ".")
    return "All patches applied."


def pkg_config_path():
    extra = "/opt/homebrew/lib/pkgconfig:/opt/homebrew/share/pkgconfig"
    previous = os.environ.get("PKG_CONFIG_PATH", "")
    if previous:
        extra = extra + os.pathsep + previous
    return extra


def pkg_exists(name):
    env = dict(os.environ)
    env["PKG_CONFIG_PATH"] = pkg_config_path()
    proc = subprocess.run(
        ["pkg-config", "--exists", name],
        capture_output=True,
        timeout=30,
        env=env,
    )
    return proc.returncode == 0


def ensure_macos_pc_files(emit):
    pc_dir = "/opt/homebrew/lib/pkgconfig"
    gl_pc = os.path.join(pc_dir, "gl.pc")
    glew_pc = os.path.join(pc_dir, "glew.pc")
    try:
        os.makedirs(pc_dir, exist_ok=True)
        if not os.path.isfile(gl_pc):
            with open(gl_pc, "w") as handle:
                handle.write(
                    "prefix=/System/Library/Frameworks/OpenGL.framework/Versions/Current\n"
                    "\n"
                    "Name: gl\n"
                    "Description: macOS OpenGL Framework\n"
                    "Version: 4.1\n"
                    "Libs: -framework OpenGL\n"
                    "Cflags:\n"
                )
            emit("Wrote " + gl_pc + ".")
        if not os.path.isfile(glew_pc) or not os.path.exists(glew_pc):
            if os.path.islink(glew_pc):
                os.remove(glew_pc)
            with open(glew_pc, "w") as handle:
                handle.write(
                    "prefix=/opt/homebrew\n"
                    "exec_prefix=${prefix}\n"
                    "libdir=${exec_prefix}/lib\n"
                    "includedir=${prefix}/include\n"
                    "\n"
                    "Name: glew\n"
                    "Description: OpenGL Extension Wrangler Library\n"
                    "Version: 2.3.1\n"
                    "Libs: -L${libdir} -lGLEW\n"
                    "Cflags: -I${includedir}\n"
                )
            emit("Wrote " + glew_pc + ".")
    except OSError as exc:
        raise PhaseError("Cannot write pkg-config files: " + str(exc) + ".")


def brew_install(packages, emit):
    run_cmd(["brew", "install"] + list(packages), os.path.expanduser("~"), emit)


def check_deps(os_id, emit):
    for tool in ("make", "pkg-config"):
        if shutil.which(tool) is None:
            raise PhaseError("Missing tool: " + tool + ".")
    if shutil.which("cc") is None and shutil.which("gcc") is None:
        raise PhaseError("No C compiler found.")
    if os_id == system_info.MACOS:
        missing = [p for p in ("sdl2", "glew") if not pkg_exists(p)]
        if missing:
            emit("Installing missing packages: " + ", ".join(missing) + ".")
            brew_install(missing, emit)
        ensure_macos_pc_files(emit)
    elif os_id == system_info.LINUX:
        missing = [p for p in ("sdl2", "glew") if not pkg_exists(p)]
        if missing:
            raise PhaseError(
                "Missing libraries: "
                + ", ".join(missing)
                + ". Install them, e.g. "
                "sudo apt install libsdl2-dev libglew-dev pkg-config."
            )
    elif os_id == system_info.HAIKU:
        missing = [p for p in ("sdl2", "glew") if not pkg_exists(p)]
        if missing:
            raise PhaseError(
                "Missing libraries: "
                + ", ".join(missing)
                + ". Install them with pkgman, e.g. pkgman install sdl2_devel."
            )
    for name in ("sdl2", "glew"):
        if not pkg_exists(name):
            raise PhaseError("Library not found by pkg-config: " + name + ".")
    return "Dependencies OK."


def build_env():
    env = dict(os.environ)
    env["PKG_CONFIG_PATH"] = pkg_config_path()
    return env


def build(emit):
    run_cmd(["make", "-j" + jobs()], _WORK["src"], emit, build_env())
    return "Build finished."


def install(os_id, gdk, emit):
    src = _WORK["src"]
    dest = install_dir(gdk)
    binary = os.path.join(src, exe_name(os_id))
    if not os.path.isfile(binary):
        raise PhaseError("Built binary missing: " + binary + ".")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(".git", "obj", "__pycache__", "*.o", "*.d"),
    )
    emit("Copied to " + dest + ".")
    if os_id != system_info.WINDOWS:
        os.chmod(binary_path(gdk, os_id), 0o755)
    user_cfg = os.path.join(os.path.expanduser("~"), ".config", "blastem", "blastem.cfg")
    if not os.path.isfile(user_cfg):
        default_cfg = os.path.join(dest, "default.cfg")
        if os.path.isfile(default_cfg):
            os.makedirs(os.path.dirname(user_cfg), exist_ok=True)
            shutil.copy2(default_cfg, user_cfg)
            emit("Installed default BlastEm config.")
    try:
        with open(user_cfg, "r") as handle:
            cfg_text = handle.read()
        if "machine_freeze_action" not in cfg_text:
            if "ui {" in cfg_text:
                cfg_text = cfg_text.replace(
                    "ui {", "ui {\n\tmachine_freeze_action ignore", 1
                )
            else:
                cfg_text += "\nui {\n\tmachine_freeze_action ignore\n}\n"
            with open(user_cfg, "w") as handle:
                handle.write(cfg_text)
            emit("Disabled hardware lockup prompts.")
    except OSError as exc:
        raise PhaseError("Cannot update BlastEm config: " + str(exc) + ".")
    return "Installed to " + dest + "."


def verify(os_id, gdk, emit):
    path = binary_path(gdk, os_id)
    if not is_installed(gdk, os_id):
        raise PhaseError("Installed binary missing: " + path + ".")
    try:
        with open(path, "rb") as handle:
            head = handle.read(8)
    except OSError as exc:
        raise PhaseError("Cannot read installed binary: " + str(exc) + ".")
    if head[:4] == b"\x7fELF":
        emit("ELF binary OK.")
    elif head[:4] == b"\xcf\xfa\xed\xfe":
        cpu = int.from_bytes(head[4:8], "little")
        names = {16777228: "arm64", 16777223: "x86_64"}
        emit("Mach-O binary OK (" + names.get(cpu, hex(cpu)) + ").")
    elif os_id != system_info.WINDOWS:
        raise PhaseError("Installed file is not an executable binary: " + path + ".")
    cleanup_work()
    return "BlastEm ready at " + path + "."
