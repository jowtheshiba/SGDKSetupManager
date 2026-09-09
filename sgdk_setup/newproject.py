import json
import os
import re

GENIO = "genio"
PALADIN = "paladin"

MAIN_C = """#include <genesis.h>

int main(bool hardReset)
{
    VDP_drawText("Hello world!", 14, 13);

    while (TRUE)
    {
        SYS_doVBlankProcess();
    }

    return 0;
}
"""

VSCODE_SETTINGS = {
    "files.exclude": {
        "**/*.o": True,
        "**/*.d": True,
        "**/*.out": True,
        "**/cmd_": True,
        "**/out.lst": True,
    }
}

MAKEFILE_WRAPPER = """GDK ?= __GDK__

all: release

release:
\tmake -f $(GDK)/makefile.gen release

debug:
\tmake -f $(GDK)/makefile.gen debug

clean:
\tmake -f $(GDK)/makefile.gen clean
"""

GENIO_YAML = """build_mode: 1
build_file_path: ""
project_release_build_command: make -f __GDK__/makefile.gen release
project_release_clean_command: make -f __GDK__/makefile.gen clean
project_release_execute_args: ""
project_release_target: __ROM_RELEASE__
project_debug_build_command: make -f __GDK__/makefile.gen debug
project_debug_clean_command: make -f __GDK__/makefile.gen clean
project_debug_execute_args: ""
project_debug_target: __ROM_DEBUG__
project_run_in_terminal: false
"""

PALADIN_PLD = """NAME=__NAME__
TARGETNAME=__NAME__
PLATFORM=HaikuGCC4
SCM=git
GROUP=Source files
EXPANDGROUP=yes
SOURCEFILE=src/main.c
LOCALINCLUDE=inc
LOCALINCLUDE=__GDK__/inc
LOCALINCLUDE=__GDK__/res
CCEXTRA=-m68000 -DSGDK_GCC
"""

README_TEXT = """# __NAME__ (SGDK hello-world)

Minimal Sega Mega Drive project built against SGDK (libmd).

## Build

In VS Code press Cmd+Shift+B (default: release with symbols stripped)
or pick a task via Tasks: Run Task:

    SGDK: build release
    SGDK: build debug
    SGDK: clean

Same from the terminal:

    make -f __GDK__/makefile.gen release
    make -f __GDK__/makefile.gen debug

Load the ROM (__ROM_RELEASE__ for release, __ROM_DEBUG__ for debug)
in an emulator or flash it to a Mega EverDrive.

## Genesis-Code extension

The zerasul/genesis-code extension is only partly usable here:
its Compile buttons go through Wine and will not work with this
native toolchain, keep building with Cmd+Shift+B.
Still useful: .res file completion, BitmapViewer and TMX import.

## Debug

Prerequisites (one time, debug only):

    m68k-elf-gdb (no Homebrew bottle, build from source):
    wget https://ftp.gnu.org/gnu/gdb/gdb-17.2.tar.gz
    tar xzf gdb-17.2.tar.gz && mkdir build-gdb && cd build-gdb
    ../gdb-17.2/configure --target=m68k-elf --program-prefix=m68k-elf- --disable-nls
    make -j8 && sudo make install

    BlastEm for the GDB stub (debug only):
    the Homebrew formula is deprecated, upstream macOS builds
    are Intel-only and need Rosetta. On Apple Silicon build
    https://github.com/libretro/blastem natively (the x86 JIT
    is skipped automatically, generated cores are used instead),
    answer unknown RSP packets with an empty reply in gdb_remote.c
    and silence the font_mac.m stdout prints in -D mode,
    then put the resulting `blastem` on PATH.

For quick runs without debugging, OpenEmu is enough:

    /Applications/OpenEmu.app/Contents/MacOS/OpenEmu __ROM_RELEASE__

Then run the VS Code task `SGDK: debug in BlastEm`:
it rebuilds the debug ROM (__ROM_DEBUG__) and starts m68k-elf-gdb connected
to BlastEm (`target remote | blastem __ROM_DEBUG__ -D`).
Set breakpoints before continuing, e.g. `b main`, then `c`.

A `launch.json` attach template (localhost:1234) is included
for socket-capable GDB stubs.
"""


def valid_name(name):
    return re.match(r"^[A-Za-z0-9_-]+$", name) is not None


def vscode_cpp_properties(gdk, compiler):
    return {
        "configurations": [
            {
                "name": "sgdk",
                "includePath": [
                    "${workspaceFolder}/src",
                    "${workspaceFolder}/inc",
                    "${workspaceFolder}/res",
                    gdk + "/inc",
                    gdk + "/res",
                ],
                "compilerPath": compiler,
                "compilerArgs": ["-m68000", "-DSGDK_GCC"],
                "cStandard": "c99",
            }
        ],
        "version": 4,
    }


def split_out_dirs(gdk):
    try:
        with open(os.path.join(gdk, "makefile.gen")) as handle:
            return "OUT_DIR" in handle.read()
    except OSError:
        return False


def rom_paths(gdk):
    if split_out_dirs(gdk):
        return "out/release/rom.bin", "out/debug/rom.bin"
    return "out/rom.bin", "out/rom.bin"


def blastem_resolve(gdk):
    return (
        "B=\"" + gdk + "/blastem/blastem\"; "
        "[ -x \"$B\" ] || B=$(command -v blastem); "
        "L=$(readlink \"$B\" 2>/dev/null) || L=\"$B\"; "
        "case \"$L\" in /*) B=\"$L\";; *) B=\"$(dirname \"$B\")/$L\";; esac; "
        "cd \"$(dirname \"$B\")\""
    )


def vscode_tasks(gdk, openemu=False):
    path_value = gdk + "/bin:/opt/homebrew/bin:${env:PATH}"
    env = {"GDK": gdk, "PATH": path_value}
    presentation = {"reveal": "always", "panel": "shared"}
    tasks = []
    for label, target, kind in (
        ("SGDK: build release", "release", {"kind": "build", "isDefault": True}),
        ("SGDK: build debug", "debug", "build"),
        ("SGDK: clean", "clean", "build"),
    ):
        tasks.append(
            {
                "label": label,
                "type": "shell",
                "command": "make",
                "args": ["-f", gdk + "/makefile.gen", target],
                "options": {"cwd": "${workspaceFolder}", "env": env},
                "group": kind,
                "presentation": presentation,
                "problemMatcher": "$gcc",
            }
        )
    tasks.append(
        {
            "label": "SGDK: debug in BlastEm",
            "type": "shell",
            "command": "sh",
            "args": [
                "-c",
                blastem_resolve(gdk)
                + " && exec m68k-elf-gdb -q \"${workspaceFolder}/"
                + rom_paths(gdk)[1].replace("rom.bin", "rom.out")
                + "\" -ex \"set pagination off\" -ex \"target remote | "
                + "./blastem ${workspaceFolder}/" + rom_paths(gdk)[1] + " -D\"",
            ],
            "options": {"cwd": "${workspaceFolder}", "env": env},
            "group": "build",
            "presentation": presentation,
            "problemMatcher": "$gcc",
            "dependsOn": "SGDK: build debug",
        }
    )
    rom_release = rom_paths(gdk)[0]
    run_cmd = (
        blastem_resolve(gdk)
        + " && exec ./blastem \"${workspaceFolder}/" + rom_release + "\""
    )
    tasks.append(
        {
            "label": "SGDK: run in BlastEm",
            "type": "shell",
            "command": "sh",
            "args": ["-c", run_cmd],
            "options": {"cwd": "${workspaceFolder}", "env": env},
            "group": "none",
            "presentation": presentation,
            "dependsOn": "SGDK: build release",
        }
    )
    tasks.append(
        {
            "label": "SGDK: run in BlastEm (no Z80)",
            "type": "shell",
            "command": "sh",
            "args": [
                "-c",
                blastem_resolve(gdk)
                + " && exec ./blastem -n \"${workspaceFolder}/" + rom_release + "\"",
            ],
            "options": {"cwd": "${workspaceFolder}", "env": env},
            "group": "none",
            "presentation": presentation,
            "dependsOn": "SGDK: build release",
        }
    )
    if openemu:
        tasks.append(
            {
                "label": "SGDK: run in OpenEmu",
                "type": "shell",
                "command": "/Applications/OpenEmu.app/Contents/MacOS/OpenEmu",
                "args": ["${workspaceFolder}/" + rom_release],
                "options": {"cwd": "${workspaceFolder}", "env": env},
                "group": "none",
                "presentation": presentation,
                "dependsOn": "SGDK: build release",
            }
        )
    return {"version": "2.0.0", "tasks": tasks}


def vscode_launch(gdk):
    program = "${workspaceFolder}/" + rom_paths(gdk)[1].replace("rom.bin", "rom.out")
    return {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Debug with gdb remote",
                "request": "attach",
                "type": "cppdbg",
                "program": program,
                "MIMode": "gdb",
                "miDebuggerPath": "m68k-elf-gdb",
                "miDebuggerServerAddress": "localhost:1234",
                "stopAtEntry": True,
                "cwd": "${workspaceFolder}",
            }
        ],
    }


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)
    return path


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")
    return path


def base_layout(project_dir, name, gdk):
    written = []
    os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "res"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "inc"), exist_ok=True)
    written.append(write_text(os.path.join(project_dir, "src", "main.c"), MAIN_C))
    release_rom, debug_rom = rom_paths(gdk)
    readme = (
        README_TEXT.replace("__NAME__", name)
        .replace("__GDK__", gdk)
        .replace("__ROM_RELEASE__", release_rom)
        .replace("__ROM_DEBUG__", debug_rom)
    )
    written.append(write_text(os.path.join(project_dir, "README.md"), readme))
    return written


def create_vscode_project(parent, name, gdk, compiler="", openemu=False):
    if not valid_name(name):
        raise ValueError("Project name must match [A-Za-z0-9_-]+.")
    project_dir = os.path.join(parent, name)
    if os.path.exists(project_dir):
        raise FileExistsError("Destination already exists: " + project_dir)
    written = base_layout(project_dir, name, gdk)
    written.append(write_json(os.path.join(project_dir, ".vscode", "settings.json"), VSCODE_SETTINGS))
    written.append(
        write_json(
            os.path.join(project_dir, ".vscode", "c_cpp_properties.json"),
            vscode_cpp_properties(gdk, compiler),
        )
    )
    written.append(
        write_json(
            os.path.join(project_dir, ".vscode", "tasks.json"),
            vscode_tasks(gdk, openemu),
        )
    )
    written.append(
        write_json(os.path.join(project_dir, ".vscode", "launch.json"), vscode_launch(gdk))
    )
    return project_dir, written


def create_genio_project(parent, name, gdk):
    if not valid_name(name):
        raise ValueError("Project name must match [A-Za-z0-9_-]+.")
    project_dir = os.path.join(parent, name)
    if os.path.exists(project_dir):
        raise FileExistsError("Destination already exists: " + project_dir)
    written = base_layout(project_dir, name, gdk)
    makefile = MAKEFILE_WRAPPER.replace("__GDK__", gdk)
    written.append(write_text(os.path.join(project_dir, "Makefile"), makefile))
    release_rom, debug_rom = rom_paths(gdk)
    yaml_text = (
        GENIO_YAML.replace("__GDK__", gdk)
        .replace("__ROM_RELEASE__", release_rom)
        .replace("__ROM_DEBUG__", debug_rom)
    )
    written.append(write_text(os.path.join(project_dir, ".genio.yaml"), yaml_text))
    return project_dir, written


def create_paladin_project(parent, name, gdk):
    if not valid_name(name):
        raise ValueError("Project name must match [A-Za-z0-9_-]+.")
    project_dir = os.path.join(parent, name)
    if os.path.exists(project_dir):
        raise FileExistsError("Destination already exists: " + project_dir)
    written = base_layout(project_dir, name, gdk)
    makefile = MAKEFILE_WRAPPER.replace("__GDK__", gdk)
    written.append(write_text(os.path.join(project_dir, "Makefile"), makefile))
    pld = PALADIN_PLD.replace("__NAME__", name).replace("__GDK__", gdk)
    written.append(write_text(os.path.join(project_dir, name + ".pld"), pld))
    return project_dir, written
