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

BIN := $(GDK)/bin
LIB := $(GDK)/lib
SRC_LIB := $(GDK)/src
RES_LIB := $(GDK)/res
INC_LIB := $(GDK)/inc

SHELL := sh
RM := rm
CP := cp
MKDIR := mkdir
ECHO := echo

CC := m68k-elf-gcc
LD := m68k-elf-ld
NM := m68k-elf-nm
OBJCPY := m68k-elf-objcopy
CONVSYM := $(BIN)/convsym
ASMZ80 := $(BIN)/sjasm
MACCER := mac68k
BINTOS := $(BIN)/bintos
LTO_PLUGIN :=
LIBGCC := -lgcc
LIBGCCDIR := $(shell dirname $(shell $(CC) -print-file-name=libgcc.a))

JAVA := java
SIZEBND := $(JAVA) -jar $(BIN)/sizebnd.jar
RESCOMP := $(JAVA) -jar $(BIN)/rescomp.jar

BUILD_TYPE := release
ifeq ($(MAKECMDGOALS),debug)
	BUILD_TYPE := debug
else ifeq ($(MAKECMDGOALS),Debug)
	BUILD_TYPE := debug
else ifeq ($(MAKECMDGOALS),clean-debug)
	BUILD_TYPE := debug
endif

CLEAN := FALSE
ifeq ($(findstring clean,$(MAKECMDGOALS)),clean)
CLEAN := TRUE
endif

SRC_DIR := src
RES_DIR := res
INC_DIR := inc
OUT_DIR := out/$(BUILD_TYPE)
DEP_DIR = $(OUT_DIR)/_deps
OUT_DIR_LIB := $(GDK)/$(OUT_DIR)

SRC_C = $(wildcard *.c)
SRC_C += $(wildcard $(SRC_DIR)/*.c)
SRC_C += $(wildcard $(SRC_DIR)/*/*.c)
SRC_C += $(wildcard $(SRC_DIR)/*/*/*.c)
SRC_C += $(wildcard $(SRC_DIR)/*/*/*/*.c)
SRC_C += $(wildcard $(SRC_DIR)/*/*/*/*/*.c)
SRC_C := $(filter-out $(SRC_DIR)/rom_header.c,$(SRC_C))
SRC_S = $(wildcard *.s)
SRC_S += $(wildcard $(SRC_DIR)/*.s)
SRC_S += $(wildcard $(SRC_DIR)/*/*.s)
SRC_S += $(wildcard $(SRC_DIR)/*/*/*.s)
SRC_S += $(wildcard $(SRC_DIR)/*/*/*/*.s)
SRC_S += $(wildcard $(SRC_DIR)/*/*/*/*/*.s)
SRC_ASM = $(wildcard *.asm)
SRC_ASM += $(wildcard $(SRC_DIR)/*.asm)
SRC_ASM += $(wildcard $(SRC_DIR)/*/*.asm)
SRC_ASM += $(wildcard $(SRC_DIR)/*/*/*.asm)
SRC_ASM += $(wildcard $(SRC_DIR)/*/*/*/*.asm)
SRC_ASM += $(wildcard $(SRC_DIR)/*/*/*/*/*.asm)
SRC_ASM := $(SRC_ASM)
SRC_S80 = $(wildcard *.s80)
SRC_S80 += $(wildcard $(SRC_DIR)/*.s80)
SRC_S80 += $(wildcard $(SRC_DIR)/*/*.s80)
SRC_S80 += $(wildcard $(SRC_DIR)/*/*/*.s80)
SRC_S80 += $(wildcard $(SRC_DIR)/*/*/*/*.s80)
SRC_S80 += $(wildcard $(SRC_DIR)/*/*/*/*/*.s80)
SRC_S80 := $(SRC_S80)

RES_RES = $(wildcard *.res)
RES_RES += $(wildcard $(RES_DIR)/*.res)
RES_RES += $(wildcard $(RES_DIR)/*/*.res)
RES_RES += $(wildcard $(RES_DIR)/*/*/*.res)
RES_RES += $(wildcard $(RES_DIR)/*/*/*/*.res)
RES_RES += $(wildcard $(RES_DIR)/*/*/*/*/*.res)
RES_RES := $(RES_RES)

RES_O = $(RES_RES:.res=.o)
RES_O := $(addprefix $(OUT_DIR)/, $(RES_O))

OBJS = $(RES_RES:.res=.o)
OBJS += $(SRC_S80:.s80=.o)
OBJS += $(SRC_ASM:.asm=.o)
OBJS += $(SRC_S:.s=.o)
OBJS += $(SRC_C:.c=.o)
OBJS := $(addprefix $(OUT_DIR)/, $(OBJS))

DEPS = $(RES_RES:.res=.d)
DEPS += $(SRC_S:.s=.d)
DEPS += $(SRC_C:.c=.d)
DEPS := $(addprefix $(DEP_DIR)/, $(DEPS))

INCS := -I. -I$(INC_DIR) -I$(RES_DIR) -I$(OUT_DIR) -isystem$(INC_LIB) -isystem$(OUT_DIR_LIB)
DEFAULT_FLAGS := $(EXTRA_FLAGS) -DSGDK_GCC -m68000 -fdiagnostics-color=always -Wall -Wextra -Wno-shift-negative-value -Wno-main -Wno-unused-parameter -fno-builtin -ffunction-sections -fdata-sections -fms-extensions -B$(BIN)
Z80_FLAGS := -i. -i$(SRC_DIR) -i$(INC_DIR) -i$(RES_DIR) -i$(OUT_DIR) -i$(SRC_LIB) -i$(INC_LIB) -i$(INC_LIB)/snd -i$(OUT_DIR_LIB)

ifeq ($(BUILD_TYPE),debug)
FLAGS := $(INCS) $(DEFAULT_FLAGS) -O1 -DDEBUG=1
CFLAGS := $(FLAGS) -ggdb -g
AFLAGS := -x assembler-with-cpp -Wa,--register-prefix-optional,--bitwise-or $(FLAGS)
LIBMD := $(LIB)/libmd_debug.a
else
FLAGS := $(INCS) $(DEFAULT_FLAGS) -O3 -fuse-linker-plugin -fno-web -fno-gcse -fno-tree-loop-ivcanon -fomit-frame-pointer -flto -flto=auto -ffat-lto-objects
CFLAGS := $(FLAGS)
AFLAGS := -x assembler-with-cpp -Wa,--register-prefix-optional,--bitwise-or $(FLAGS)
LIBMD := $(LIB)/libmd.a
endif

.PHONY: default
.PHONY: all
.PHONY: release
.PHONY: Release
.PHONY: debug
.PHONY: Debug
.PHONY: clean
.PHONY: clean-release
.PHONY: clean-debug
.PHONY: clean-all

default: release
all: release

Release: release
Debug: debug
clean: clean-all

release: $(OUT_DIR)/rom.bin $(OUT_DIR)/symbol.txt
release: padROM
.PHONY: padROM

debug: $(OUT_DIR)/rom.bin $(OUT_DIR)/symbol.txt
debug: injectSymbolsInROM
debug: padROM
.PHONY: injectSymbolsInROM

clean-all:
	$(RM) -r -f out

clean-release: clean-task
clean-debug: clean-task

clean-task:
	$(RM) -r -f $(OUT_DIR)
.PHONY: clean-task

padROM:	$(OUT_DIR)/rom.bin
	$(SIZEBND) $(OUT_DIR)/rom.bin -sizealign 131072 -checksum
	@$(CP) $(OUT_DIR)/rom.bin out/rom.bin

injectSymbolsInROM:	$(OUT_DIR)/rom.bin $(OUT_DIR)/symbol.txt
	$(CONVSYM) $(OUT_DIR)/symbol.txt $(OUT_DIR)/rom.bin -in txt -inopt " /fmt='%X %*[TtBbCcDd] %511s' /offsetFirst+" -range 0 FFFFFF -a -ref @MDDBG__SymbolDataPtr

$(OUT_DIR)/rom.bin: $(OUT_DIR)/rom.out $(OUT_DIR)/symbol.txt
	$(OBJCPY) -O binary $(OUT_DIR)/rom.out $(OUT_DIR)/rom.bin

$(OUT_DIR)/symbol.txt: $(OUT_DIR)/rom.out
	$(NM) $(LTO_PLUGIN) -n -l $(OUT_DIR)/rom.out > $(OUT_DIR)/symbol.txt

$(OUT_DIR)/rom.out: $(OUT_DIR)/sega.o $(OUT_DIR)/cmd_ $(LIBMD)
	@$(MKDIR) -p $(dir $@)
ifeq ($(shell uname),Haiku)
	$(LD) -T $(GDK)/md.ld --gc-sections -nostdlib $(OUT_DIR)/sega.o @$(OUT_DIR)/cmd_ $(LIBMD) -L$(LIBGCCDIR) -lgcc -o $(OUT_DIR)/rom.out
else
	$(CC) -m68000 -B$(BIN) -n -T $(GDK)/md.ld -nostdlib $(OUT_DIR)/sega.o @$(OUT_DIR)/cmd_ $(LIBMD) $(LIBGCC) -o $(OUT_DIR)/rom.out -Wl,--gc-sections -flto -flto=auto -ffat-lto-objects
endif
	@$(RM) $(OUT_DIR)/cmd_

$(OUT_DIR)/cmd_: $(OBJS)
	@$(MKDIR) -p $(dir $@)
	$(ECHO) "$(OBJS)" > $(OUT_DIR)/cmd_

$(OUT_DIR)/sega.o: out/rom_header.bin
	@$(MKDIR) -p $(dir $@)
	$(CP) $(SRC_LIB)/boot/sega.s $(OUT_DIR)/sega.s
	$(CC) $(AFLAGS) -c $(OUT_DIR)/sega.s -o $@

out/rom_header.bin: $(OUT_DIR)/rom_header.o
	$(OBJCPY) -O binary $< $@

$(OUT_DIR)/rom_header.o: $(SRC_DIR)/rom_header.c
	@$(MKDIR) -p $(dir $@)
	$(CC) $(INCS) $(DEFAULT_FLAGS) -c $< -o $@

$(SRC_DIR)/rom_header.c: | $(SRC_LIB)/boot/rom_header.c
	@$(MKDIR) -p $(dir $@)
	$(CP) $| $@

$(OUT_DIR)/%.o: %.c $(DEP_DIR)/%.d
	@$(MKDIR) -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT_DIR)/%.o: %.s $(DEP_DIR)/%.d
	@$(MKDIR) -p $(dir $@)
	$(CC) $(AFLAGS) -c $< -o $@

$(OUT_DIR)/%.o: %.asm
	@$(MKDIR) -p $(dir $@)
	$(MACCER) -o $(OUT_DIR)/$*.s $<
	$(CC) $(AFLAGS) -c $(OUT_DIR)/$*.s -o $@

$(OUT_DIR)/%.o: %.s80
	@$(MKDIR) -p $(dir $@)
	$(ASMZ80) $(Z80_FLAGS) $< $(OUT_DIR)/$*.o80 $(OUT_DIR)/out.lst
	$(BINTOS) $(OUT_DIR)/$*.o80 $(OUT_DIR)/$*.s
	$(CC) $(AFLAGS) -c $(OUT_DIR)/$*.s -o $@

$(OUT_DIR)/%.o: %.res
	@$(MKDIR) -p $(dir $@)
	@$(MKDIR) -p $(dir $(DEP_DIR)/$*.d)
	$(RESCOMP) $< $(OUT_DIR)/$*.s -dep $(OUT_DIR)/$*.o
	@$(CP) $(OUT_DIR)/$*.d $(DEP_DIR)/$*.d
	@$(RM) $(OUT_DIR)/$*.d
	@$(CP) $(OUT_DIR)/$*.h $*.h
	@$(RM) $(OUT_DIR)/$*.h
	$(CC) $(AFLAGS) -c $(OUT_DIR)/$*.s -o $@

$(DEP_DIR)/%.d: %.c $(RES_O)
	@$(MKDIR) -p $(dir $@)
	$(CC) $(CFLAGS) $< -E -MG -MM -MP -MT $(OUT_DIR)/$*.o -MF $(DEP_DIR)/$*.d

$(DEP_DIR)/%.d: %.s
	@$(MKDIR) -p $(dir $@)
	$(CC) $(AFLAGS) $< -E -MG -MM -MP -MT $(OUT_DIR)/$*.o -MF $(DEP_DIR)/$*.d

ifeq ($(CLEAN),FALSE)
-include $(DEPS)
endif
"""

GENIO_YAML = """build_mode: 1
build_file_path: ""
project_release_build_command: make release
project_release_clean_command: make clean
project_release_execute_args: ""
project_release_target: __ROM_RELEASE__
project_debug_build_command: make debug
project_debug_clean_command: make clean
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

## Genio (Haiku)

Build with the hammer button. The green Play button does not apply:
a Genesis ROM is not a Haiku executable, Genio has nothing to run.
Run the ROM with an emulator instead, e.g. `pkgman install mednafen`
then `mednafen __ROM_RELEASE__`.

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


def vscode_tasks(gdk, openemu=False, retroarch=False):
    path_value = (
        gdk + "/bin:${env:HOME}/m68k-elf/bin:/opt/homebrew/bin:${env:PATH}"
    )
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
    if retroarch:
        tasks.append(
            {
                "label": "SGDK: run in RetroArch",
                "type": "shell",
                "command": "sh",
                "args": [
                    "-c",
                    "C=\"$HOME/.config/retroarch/cores/genesis_plus_gx_libretro.so\"; "
                    "[ -f \"$C\" ] || C=\"$HOME/.var/app/org.libretro.RetroArch/config/retroarch/cores/genesis_plus_gx_libretro.so\"; "
                    "[ -f \"$C\" ] || C=/usr/lib64/libretro/genesis_plus_gx_libretro.so; "
                    "[ -f \"$C\" ] || C=/usr/lib/libretro/genesis_plus_gx_libretro.so; "
                    "R=$(command -v retroarch); "
                    "if [ -n \"$R\" ]; then exec \"$R\" -L \"$C\" \"${workspaceFolder}/"
                    + rom_release
                    + "\"; else exec flatpak run org.libretro.RetroArch -L \"$C\" \"${workspaceFolder}/"
                    + rom_release
                    + "\"; fi",
                ],
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


def create_vscode_project(parent, name, gdk, compiler="", openemu=False, retroarch=False):
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
            vscode_tasks(gdk, openemu, retroarch),
        )
    )
    written.append(
        write_json(os.path.join(project_dir, ".vscode", "launch.json"), vscode_launch(gdk))
    )
    return project_dir, written


def genio_compile_commands(project_dir, gdk):
    entries = []
    src_dir = os.path.join(project_dir, "src")
    for root, dirs, files in os.walk(src_dir):
        for name in sorted(files):
            if name.endswith(".c"):
                path = os.path.join(root, name)
                entries.append(
                    {
                        "directory": project_dir,
                        "command": " ".join(
                            [
                                "m68k-elf-gcc",
                                "-DSGDK_GCC",
                                "-std=c99",
                                "-Wno-main",
                                "-I" + os.path.join(project_dir, "src"),
                                "-I" + os.path.join(project_dir, "inc"),
                                "-I" + os.path.join(project_dir, "res"),
                                "-I" + os.path.join(gdk, "inc"),
                                "-I" + os.path.join(gdk, "res"),
                                "-c",
                                path,
                            ]
                        ),
                        "file": path,
                    }
                )
    return entries


def create_genio_project(parent, name, gdk):
    if not valid_name(name):
        raise ValueError("Project name must match [A-Za-z0-9_-]+.")
    project_dir = os.path.join(parent, name)
    if os.path.exists(project_dir):
        raise FileExistsError("Destination already exists: " + project_dir)
    written = base_layout(project_dir, name, gdk)
    release_out, debug_out = rom_paths(gdk)
    release_out = release_out.rsplit("/rom.bin", 1)[0]
    debug_out = debug_out.rsplit("/rom.bin", 1)[0]
    makefile = (
        MAKEFILE_WRAPPER.replace("__GDK__", gdk)
        .replace("__OUT_RELEASE__", release_out)
        .replace("__OUT_DEBUG__", debug_out)
    )
    written.append(write_text(os.path.join(project_dir, "Makefile"), makefile))
    release_rom, debug_rom = rom_paths(gdk)
    yaml_text = (
        GENIO_YAML.replace("__GDK__", gdk)
        .replace("__ROM_RELEASE__", release_rom)
        .replace("__ROM_DEBUG__", debug_rom)
    )
    written.append(write_text(os.path.join(project_dir, ".genio.yaml"), yaml_text))
    written.append(
        write_json(
            os.path.join(project_dir, "compile_commands.json"),
            genio_compile_commands(project_dir, gdk),
        )
    )
    return project_dir, written


def create_paladin_project(parent, name, gdk):
    if not valid_name(name):
        raise ValueError("Project name must match [A-Za-z0-9_-]+.")
    project_dir = os.path.join(parent, name)
    if os.path.exists(project_dir):
        raise FileExistsError("Destination already exists: " + project_dir)
    written = base_layout(project_dir, name, gdk)
    release_out, debug_out = rom_paths(gdk)
    release_out = release_out.rsplit("/rom.bin", 1)[0]
    debug_out = debug_out.rsplit("/rom.bin", 1)[0]
    makefile = (
        MAKEFILE_WRAPPER.replace("__GDK__", gdk)
        .replace("__OUT_RELEASE__", release_out)
        .replace("__OUT_DEBUG__", debug_out)
    )
    written.append(write_text(os.path.join(project_dir, "Makefile"), makefile))
    pld = PALADIN_PLD.replace("__NAME__", name).replace("__GDK__", gdk)
    written.append(write_text(os.path.join(project_dir, name + ".pld"), pld))
    return project_dir, written
