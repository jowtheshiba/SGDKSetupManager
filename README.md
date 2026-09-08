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
   then builds and installs it with a per-phase progress bar.
4. After the install, or right away when SGDK is present,
   it works as a project creator in the current folder:
   VS Code project on Linux/macOS/Windows,
   Genio or Paladin project on Haiku.
