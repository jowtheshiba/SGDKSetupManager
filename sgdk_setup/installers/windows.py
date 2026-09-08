import os

from sgdk_setup.runner import PhaseError, run_cmd

TOOLCHAIN_HINT = (
    "SGDK ships its own m68k-elf GCC 13.2 toolchain in bin/. "
    "Only Java is required on top."
)

BUNDLED_TOOLS = [
    "gcc.exe",
    "make.exe",
    "sh.exe",
    "sjasm.exe",
    "bintos.exe",
    "xgmtool.exe",
    "convsym.exe",
]

PHASES = [
    ("Check prerequisites", "Verify the bundled toolchain and Java."),
    ("Verify bundled tools", "Check native Windows tool binaries and jars."),
    ("Build libraries", "Compile libmd.a and libmd_debug.a."),
    ("Test ROM", "Build and clean the hello-world sample."),
]


def run_phase(index, sgdk_dir, emit):
    if index == 0:
        return check_prereqs(sgdk_dir, emit)
    if index == 1:
        return verify_tools(sgdk_dir, emit)
    if index == 2:
        return build_libs(sgdk_dir, emit)
    if index == 3:
        return test_rom(sgdk_dir, emit)
    raise IndexError("Unknown phase " + str(index))


def check_prereqs(sgdk_dir, emit):
    gcc = os.path.join(sgdk_dir, "bin", "gcc.exe")
    make = os.path.join(sgdk_dir, "bin", "make.exe")
    if not os.path.isfile(gcc):
        raise PhaseError("Bundled compiler missing: " + gcc + ".")
    if not os.path.isfile(make):
        raise PhaseError("Bundled make missing: " + make + ".")
    run_cmd(["java", "-version"], sgdk_dir, emit)
    return "Bundled toolchain present, Java works."


def verify_tools(sgdk_dir, emit):
    missing = []
    for tool in BUNDLED_TOOLS:
        path = os.path.join(sgdk_dir, "bin", tool)
        if os.path.isfile(path):
            emit("Found " + tool + ".")
        else:
            missing.append(tool)
    for jar in ("rescomp.jar", "sizebnd.jar"):
        path = os.path.join(sgdk_dir, "bin", jar)
        if os.path.isfile(path):
            emit("Found " + jar + ".")
        else:
            missing.append(jar)
    if missing:
        raise PhaseError("Missing bundled files: " + ", ".join(missing) + ".")
    return "All bundled tools verified."


def build_libs(sgdk_dir, emit):
    make = os.path.join(sgdk_dir, "bin", "make.exe")
    run_cmd([make, "-f", "makelib.gen", "release"], sgdk_dir, emit)
    run_cmd([make, "-f", "makelib.gen", "debug"], sgdk_dir, emit)
    return "libmd.a and libmd_debug.a built."


def test_rom(sgdk_dir, emit):
    make = os.path.join(sgdk_dir, "bin", "make.exe")
    sample = os.path.join(sgdk_dir, "sample", "basics", "hello-world")
    run_cmd([make, "-f", os.path.join(sgdk_dir, "makefile.gen"), "release"], sample, emit)
    rom = os.path.join(sample, "out", "rom.bin")
    if not os.path.isfile(rom):
        raise PhaseError("Test ROM was not produced at " + rom + ".")
    run_cmd([make, "-f", os.path.join(sgdk_dir, "makefile.gen"), "clean"], sample, emit)
    return "Test ROM built and cleaned: " + rom + "."
