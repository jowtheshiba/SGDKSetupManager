import os
import shutil
import subprocess
import tempfile

from sgdk_setup.runner import PhaseError, run_cmd


def check_host_tools(required, hint):
    missing = [tool for tool in required if shutil.which(tool) is None]
    if missing:
        raise PhaseError(
            "Missing tools: " + ", ".join(missing) + ". " + hint
        )
    return "Found: " + ", ".join(required)


def host_cc():
    for tool in ("cc", "gcc"):
        path = shutil.which(tool)
        if path:
            return path
    raise PhaseError("No C compiler found (cc/gcc). Install your system build tools.")


def first_existing(candidates, what):
    for item in candidates:
        if os.path.isfile(item):
            return item
    raise PhaseError("No " + what + " found in " + candidates[0] + ".")


def build_bintos(sgdk_dir, emit):
    cc = host_cc()
    src = first_existing(
        [
            os.path.join(sgdk_dir, "tools", "bintos", "src", "bintos.c"),
            os.path.join(sgdk_dir, "tools", "bintos", "bintos.c"),
        ],
        "bintos.c",
    )
    out = os.path.join(sgdk_dir, "bin", "bintos")
    run_cmd([cc, src, "-o", out], sgdk_dir, emit)
    os.chmod(out, 0o755)
    return out


def build_sjasm(sgdk_dir, emit):
    src_dir = first_existing(
        [
            os.path.join(sgdk_dir, "tools", "sjasm", "src", "Makefile"),
            os.path.join(sgdk_dir, "tools", "sjasm", "Makefile"),
        ],
        "sjasm Makefile",
    )
    src_dir = os.path.dirname(src_dir)
    run_cmd(["make", "-C", src_dir], sgdk_dir, emit)
    built = os.path.join(src_dir, "sjasm")
    target = os.path.join(sgdk_dir, "bin", "sjasm")
    with open(built, "rb") as source:
        data = source.read()
    with open(target, "wb") as dest:
        dest.write(data)
    os.chmod(target, 0o755)
    probe = subprocess.run(
        [target], capture_output=True, text=True, timeout=30
    )
    if "v0.39j" not in (probe.stdout + probe.stderr):
        raise PhaseError("Unexpected sjasm binary, expected SGDK fork v0.39j.")
    return target


def build_xgmtool(sgdk_dir, emit):
    src = os.path.dirname(
        first_existing(
            [
                os.path.join(sgdk_dir, "tools", "xgmtool", "src", "CMakeLists.txt"),
                os.path.join(sgdk_dir, "tools", "xgmtool", "CMakeLists.txt"),
            ],
            "xgmtool CMakeLists.txt",
        )
    )
    emit("xgmtool sources at " + src + ".")
    build_dir = tempfile.mkdtemp(prefix="sgdk-xgmtool-build.")
    try:
        run_cmd(["cmake", "-S", src, "-B", build_dir], sgdk_dir, emit)
        run_cmd(["cmake", "--build", build_dir], sgdk_dir, emit)
        built = os.path.join(build_dir, "xgmtool")
        target = os.path.join(sgdk_dir, "bin", "xgmtool")
        with open(built, "rb") as source:
            data = source.read()
        with open(target, "wb") as dest:
            dest.write(data)
        os.chmod(target, 0o755)
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)
    return target


def build_convsym(sgdk_dir, emit):
    src_dir = os.path.dirname(
        first_existing(
            [os.path.join(sgdk_dir, "tools", "convsym", "Makefile")],
            "convsym Makefile",
        )
    )
    run_cmd(["make", "-C", src_dir], sgdk_dir, emit)
    built = os.path.join(src_dir, "build", "convsym")
    target = os.path.join(sgdk_dir, "bin", "convsym")
    with open(built, "rb") as source:
        data = source.read()
    with open(target, "wb") as dest:
        dest.write(data)
    os.chmod(target, 0o755)
    return target


def patch_sources(sgdk_dir, emit):
    jobs = [
        (
            os.path.join(sgdk_dir, "src", "snd", "pcm", "snd_pcm.c"),
            "SND_PCM_startPlay(const u8 *sample, const u32 len, "
            "const SoundPcmSampleRate rate, const SoundPanning pan, const u8 loop)",
            "SND_PCM_startPlay(const u8 *sample, const u32 len, "
            "const SoundPcmSampleRate rate, const SoundPanning pan, const bool loop)",
        ),
        (
            os.path.join(sgdk_dir, "src", "snd", "pcm", "snd_pcm4.c"),
            "SND_PCM4_startPlay(const u8 *sample, const u32 len, "
            "const SoundPCMChannel channel, const u8 loop)",
            "SND_PCM4_startPlay(const u8 *sample, const u32 len, "
            "const SoundPCMChannel channel, const bool loop)",
        ),
    ]
    patched = 0
    for path, old, new in jobs:
        with open(path, "r") as handle:
            text = handle.read()
        if new in text:
            emit(os.path.basename(path) + " already patched, skipping.")
            continue
        if old not in text:
            raise PhaseError("Unexpected content in " + path + ", patch does not apply.")
        with open(path, "w") as handle:
            handle.write(text.replace(old, new))
        emit("Patched " + os.path.basename(path) + ".")
        patched += 1
    return "Patched " + str(patched) + " file(s)."


def build_env(sgdk_dir):
    env = dict(os.environ)
    env["GDK"] = sgdk_dir
    env["PATH"] = os.path.join(sgdk_dir, "bin") + os.pathsep + env.get("PATH", "")
    return env


def build_libs(sgdk_dir, emit):
    env = build_env(sgdk_dir)
    run_cmd(["make", "-f", "makelib.gen", "release"], sgdk_dir, emit, env)
    run_cmd(["make", "-f", "makelib.gen", "debug"], sgdk_dir, emit, env)
    return "libmd.a and libmd_debug.a built."


def test_rom(sgdk_dir, emit):
    env = build_env(sgdk_dir)
    sample = os.path.join(sgdk_dir, "sample", "basics", "hello-world")
    run_cmd(["make", "-f", os.path.join(sgdk_dir, "makefile.gen"), "release"], sample, emit, env)
    rom = os.path.join(sample, "out", "rom.bin")
    if not os.path.isfile(rom):
        raise PhaseError("Test ROM was not produced at " + rom + ".")
    run_cmd(["make", "-f", os.path.join(sgdk_dir, "makefile.gen"), "clean"], sample, emit, env)
    return "Test ROM built and cleaned: " + rom + "."
