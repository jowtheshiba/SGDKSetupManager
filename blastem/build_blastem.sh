#!/usr/bin/env bash
set -e
GDK="${1:-${GDK:-$HOME/SGDK}}"
REPO="https://github.com/libretro/blastem"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d /tmp/blastem-build.XXXXXX)"

echo "Cloning $REPO (latest commit) ..."
git clone --depth 1 "$REPO" "$WORK/src"
echo "Commit: $(git -C "$WORK/src" rev-parse --short HEAD)"

echo "Applying patches ..."
patch -N -p1 -d "$WORK/src" -i "$HERE/patches/01-gdb-remote-tolerance.patch"
patch -N -p1 -d "$WORK/src" -i "$HERE/patches/02-font-mac-stdout.patch"

echo "Checking dependencies ..."
for tool in cc make patch pkg-config; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool"; exit 1; }
done
pkg-config --exists sdl2 || { echo "Missing SDL2 development files"; exit 1; }
pkg-config --exists glew || { echo "Missing GLEW development files"; exit 1; }

if [ "$(uname)" = "Darwin" ]; then
  PCP="/opt/homebrew/lib/pkgconfig:/opt/homebrew/share/pkgconfig"
  export PKG_CONFIG_PATH="$PCP:${PKG_CONFIG_PATH:-}"
fi

echo "Building ..."
make -C "$WORK/src" -j8

echo "Installing to $GDK/blastem ..."
rm -rf "$GDK/blastem"
mkdir -p "$GDK/blastem"
tar --exclude=.git --exclude=obj -cf - -C "$WORK/src" . | tar -xf - -C "$GDK/blastem"
chmod +x "$GDK/blastem/blastem"

test -x "$GDK/blastem/blastem" || { echo "Install failed: binary missing"; exit 1; }
rm -rf "$WORK"
echo "BlastEm installed at $GDK/blastem"
