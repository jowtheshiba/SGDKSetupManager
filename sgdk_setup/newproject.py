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
project_release_target: out/rom.bin
project_debug_build_command: make -f __GDK__/makefile.gen debug
project_debug_clean_command: make -f __GDK__/makefile.gen clean
project_debug_execute_args: ""
project_debug_target: out/rom.bin
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

    make -f __GDK__/makefile.gen release
    make -f __GDK__/makefile.gen debug

Load out/rom.bin in an emulator or flash it to a Mega EverDrive.
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


def vscode_tasks(gdk):
    path_value = gdk + "/bin:/opt/homebrew/bin:${env:PATH}"
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
                "options": {
                    "cwd": "${workspaceFolder}",
                    "env": {"GDK": gdk, "PATH": path_value},
                },
                "group": kind,
                "presentation": {"reveal": "always", "panel": "shared"},
                "problemMatcher": "$gcc",
            }
        )
    return {"version": "2.0.0", "tasks": tasks}


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
    readme = README_TEXT.replace("__NAME__", name).replace("__GDK__", gdk)
    written.append(write_text(os.path.join(project_dir, "README.md"), readme))
    return written


def create_vscode_project(parent, name, gdk, compiler=""):
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
        write_json(os.path.join(project_dir, ".vscode", "tasks.json"), vscode_tasks(gdk))
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
    yaml_text = GENIO_YAML.replace("__GDK__", gdk)
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
