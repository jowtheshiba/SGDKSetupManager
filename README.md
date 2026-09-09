# SGDK Setup Manager

TUI assistant that installs SGDK and scaffolds SGDK projects.

## Run

macOS / Linux / Haiku:

    ./run.sh

Windows:

    run.bat

The launcher creates `.venv` next to the program on first start,
installs dependencies there and opens the assistant.

## Flow

1. The assistant detects the OS (Linux, macOS, Windows, Haiku).
2. It checks git and whether SGDK is already installed.
3. If SGDK is missing, it downloads it
   (default `https://github.com/Stephane-D/sgdk`, custom URL supported),
   then builds it with a per-phase progress bar, installs the tools,
   libraries and headers to `~/SGDK` (changeable) and removes
   the downloaded sources.
4. After the install, or right away when SGDK is present,
   it works as a project creator in the folder you choose:
   VS Code project on Linux/macOS/Windows,
   Genio or Paladin project on Haiku.
5. Optionally, with SGDK installed, the Install BlastEm menu
   builds the latest libretro/blastem (with GDB fixes) into
   the SGDK folder. A manual build script plus patches live
   in blastem/.
6. No m68k-elf-gcc on the system? Build it from sources with
   toolchain/m68k-toolchain.sh (binutils + GCC for m68k-elf,
   default prefix ~/m68k-elf, takes a while).

## Tested

Build (native tools, libmd, test ROM): macOS arm64, Linux aarch64 (Fedora 44).

Debug via GDB + BlastEm: works on macOS arm64 with reservations
(native BlastEm build with bundled GDB-stub fixes, Z80 core issues
work around with the no-Z80 run task). Other systems not tested.
