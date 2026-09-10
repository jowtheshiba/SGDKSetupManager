#!/usr/bin/env bash
set -e
PREFIX="$HOME/m68k-elf"
GCC_VER="13.2.0"
BINUTILS_VER="2.44"
KEEP=0
JOBS="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"

usage() {
  echo "Usage: ./m68k-toolchain.sh [--prefix DIR] [--jobs N] [--gcc VER] [--binutils VER] [--keep]"
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) PREFIX="$2"; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --gcc) GCC_VER="$2"; shift 2 ;;
    --binutils) BINUTILS_VER="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
done

OS="$(uname)"
echo "Target: m68k-elf, prefix: $PREFIX, jobs: $JOBS"
echo "Versions: binutils $BINUTILS_VER, gcc $GCC_VER"

echo "Checking host tools ..."
for tool in make tar; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool"; exit 1; }
done
if command -v curl >/dev/null; then
  FETCH="curl -L -o"
elif command -v wget >/dev/null; then
  FETCH="wget -O"
else
  echo "Missing tool: curl or wget"
  exit 1
fi
if [ "$OS" = "Darwin" ]; then
  for tool in gcc-15 gcc-14 gcc-13; do
    if command -v "$tool" >/dev/null; then
      export CC="$tool"
      export CXX="${tool/gcc-/g++-}"
      break
    fi
  done
  if [ -z "${CC:-}" ]; then
    echo "Install a brew GCC first: brew install gcc"
    exit 1
  fi
  echo "Host compiler: $CC"
else
  command -v cc >/dev/null || { echo "Missing tool: cc (install build-essential / Development Tools)"; exit 1; }
fi
for tool in bison flex makeinfo; do
  command -v "$tool" >/dev/null || echo "Warning: $tool not found, install it if the build fails (Linux: bison flex texinfo)"
done

WORK="$PREFIX/build-work"
SRC="$WORK/src"
BUILD="$WORK/build"
mkdir -p "$SRC" "$BUILD"

fetch() {
  if [ -f "$SRC/$2" ]; then
    echo "Reusing $2"
  else
    echo "Downloading $2 ..."
    $FETCH "$SRC/$2" "$1"
  fi
}

fetch "https://ftp.gnu.org/gnu/binutils/binutils-$BINUTILS_VER.tar.xz" "binutils-$BINUTILS_VER.tar.xz"
fetch "https://ftp.gnu.org/gnu/gcc/gcc-$GCC_VER/gcc-$GCC_VER.tar.xz" "gcc-$GCC_VER.tar.xz"

echo "Extracting ..."
tar xf "$SRC/binutils-$BINUTILS_VER.tar.xz" -C "$SRC"
tar xf "$SRC/gcc-$GCC_VER.tar.xz" -C "$SRC"
(cd "$SRC/gcc-$GCC_VER" && ./contrib/download_prerequisites)

echo "Building binutils ..."
mkdir -p "$BUILD/binutils-$BINUTILS_VER"
(cd "$BUILD/binutils-$BINUTILS_VER" && "$SRC/binutils-$BINUTILS_VER/configure" --target=m68k-elf --prefix="$PREFIX" --disable-nls --disable-werror)
make -C "$BUILD/binutils-$BINUTILS_VER" -j"$JOBS"
make -C "$BUILD/binutils-$BINUTILS_VER" install
export PATH="$PREFIX/bin:$PATH"

echo "Building gcc ..."
export CXXFLAGS="-g -O2 -std=gnu++11"
if [ "$OS" = "Haiku" ]; then
  export CFLAGS="-g -O2 -fPIC"
  export CXXFLAGS="-g -O2 -std=gnu++11 -fPIC"
fi
mkdir -p "$BUILD/gcc-$GCC_VER"
(cd "$BUILD/gcc-$GCC_VER" && "$SRC/gcc-$GCC_VER/configure" --target=m68k-elf --prefix="$PREFIX" --enable-languages=c --without-headers --disable-shared --disable-threads --disable-libssp --disable-libgomp --disable-libquadmath --disable-nls --with-cpu=68000)
make -C "$BUILD/gcc-$GCC_VER" -j"$JOBS" all-gcc
make -C "$BUILD/gcc-$GCC_VER" -j"$JOBS" all-target-libgcc
make -C "$BUILD/gcc-$GCC_VER" install-gcc
make -C "$BUILD/gcc-$GCC_VER" install-target-libgcc

echo "Verifying ..."
"$PREFIX/bin/m68k-elf-gcc" --version | head -n 1
echo 'int main(void){return 0;}' | "$PREFIX/bin/m68k-elf-gcc" -m68000 -c -x c - -o "$WORK/smoke.o"
echo "Smoke test OK: $WORK/smoke.o"

if [ "$OS" = "Haiku" ]; then
  echo "Linking toolchain into non-packaged bin ..."
  mkdir -p "$HOME/config/non-packaged/bin"
  ln -sf "$PREFIX/bin/m68k-elf-"* "$HOME/config/non-packaged/bin/"
fi

if [ "$KEEP" = "0" ]; then
  echo "Cleaning work dirs ..."
  rm -rf "$BUILD" "$SRC"
fi

echo "Done. Add to your shell profile:"
echo "  export PATH=\"$PREFIX/bin:\$PATH\""
