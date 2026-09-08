import os
import platform
import shutil
import subprocess

LINUX = "linux"
MACOS = "macos"
WINDOWS = "windows"
HAIKU = "haiku"
UNKNOWN = "unknown"

DEFAULT_REPO_URL = "https://github.com/Stephane-D/sgdk"

OS_LABELS = {
    LINUX: "Linux",
    MACOS: "macOS",
    WINDOWS: "Windows",
    HAIKU: "Haiku",
    UNKNOWN: "Unknown",
}


def detect_os():
    name = platform.system()
    if name == "Linux":
        return LINUX
    if name == "Darwin":
        return MACOS
    if name == "Windows":
        return WINDOWS
    if name == "Haiku":
        return HAIKU
    return UNKNOWN


def os_label(os_id):
    return OS_LABELS.get(os_id, os_id)


def git_available():
    return shutil.which("git") is not None


def git_version():
    try:
        out = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def valid_sgdk_dir(path):
    if not path or not os.path.isdir(path):
        return False
    inc = os.path.join(path, "inc", "genesis.h")
    lib = os.path.join(path, "lib", "libmd.a")
    return os.path.isfile(inc) and os.path.isfile(lib)


def candidate_dirs(os_id):
    home = os.path.expanduser("~")
    dirs = [
        os.environ.get("GDK", ""),
        os.path.join(home, "SGDK"),
        os.path.join(home, "sgdk"),
    ]
    if os_id in (LINUX, MACOS, HAIKU):
        dirs += ["/opt/sgdk", "/usr/local/sgdk"]
    if os_id == WINDOWS:
        dirs += [
            "C:\\sgdk",
            "C:\\SGDK",
            os.path.join(home, "SGDK"),
        ]
    seen = []
    for item in dirs:
        if item and item not in seen:
            seen.append(item)
    return seen


def find_sgdk(os_id):
    for item in candidate_dirs(os_id):
        if valid_sgdk_dir(item):
            return os.path.abspath(item)
    return None


def toolchain_status(os_id):
    if os_id == WINDOWS:
        return {}
    tools = ["m68k-elf-gcc", "java", "cmake", "make"]
    return {tool: shutil.which(tool) is not None for tool in tools}
