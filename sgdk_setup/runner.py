import os
import shutil
import subprocess


class PhaseError(Exception):
    pass


INSTALL_DIRS = ("bin", "lib", "inc", "res", os.path.join("src", "boot"))
INSTALL_FILES = ("common.mk", "md.ld", "makefile.gen", "makelib.gen")


def install_to_prefix(sgdk_dir, prefix, emit):
    os.makedirs(prefix, exist_ok=True)
    for item in INSTALL_DIRS:
        src = os.path.join(sgdk_dir, item)
        dst = os.path.join(prefix, item)
        if not os.path.isdir(src):
            raise PhaseError("Expected directory missing: " + src + ".")
        shutil.copytree(src, dst, dirs_exist_ok=True)
        emit("Installed " + item + ".")
    for item in INSTALL_FILES:
        src = os.path.join(sgdk_dir, item)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(prefix, item))
            emit("Installed " + item + ".")
    return prefix


def remove_sources(sgdk_dir, prefix):
    if os.path.abspath(sgdk_dir) == os.path.abspath(prefix):
        return "Install location is the source checkout, keeping it."
    shutil.rmtree(sgdk_dir)
    return "Removed source checkout: " + sgdk_dir + "."


def run_cmd(args, cwd, emit, env=None):
    proc = subprocess.Popen(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    for line in proc.stdout:
        emit(line.rstrip())
    code = proc.wait()
    if code != 0:
        raise PhaseError(" ".join(args) + " exited with code " + str(code))
