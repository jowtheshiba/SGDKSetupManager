from sgdk_setup import posix

TOOLCHAIN_HINT = (
    "Install the m68k-elf toolchain with Homebrew "
    "(brew install m68k-elf-gcc), plus openjdk and cmake."
)

PHASES = [
    ("Check prerequisites", "Verify m68k-elf-gcc, Java, CMake and build tools."),
    ("Build bintos", "Compile the Z80 .o80 to .s converter."),
    ("Build sjasm", "Compile the SGDK Z80 assembler fork v0.39j."),
    ("Build xgmtool", "Compile the VGM/XGM converter with CMake."),
    ("Build convsym", "Compile the symbol converter for debug builds."),
    ("Patch sources", "Fix bool/u8 mismatch for modern GCC."),
    ("Build libraries", "Compile libmd.a and libmd_debug.a."),
    ("Test ROM", "Build and clean the hello-world sample."),
]


def run_phase(index, sgdk_dir, emit):
    if index == 0:
        return posix.check_host_tools(
            ["m68k-elf-gcc", "java", "cmake", "make"], TOOLCHAIN_HINT
        )
    if index == 1:
        return posix.build_bintos(sgdk_dir, emit)
    if index == 2:
        return posix.build_sjasm(sgdk_dir, emit)
    if index == 3:
        return posix.build_xgmtool(sgdk_dir, emit)
    if index == 4:
        return posix.build_convsym(sgdk_dir, emit)
    if index == 5:
        return posix.patch_sources(sgdk_dir, emit)
    if index == 6:
        return posix.build_libs(sgdk_dir, emit)
    if index == 7:
        return posix.test_rom(sgdk_dir, emit)
    raise IndexError("Unknown phase " + str(index))
