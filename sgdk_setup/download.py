import subprocess


def repo_reachable(url, timeout=20):
    try:
        proc = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def clone_repo(url, dest, emit):
    proc = subprocess.Popen(
        ["git", "clone", "--depth", "1", url, dest],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in proc.stdout:
        emit(line.rstrip())
    code = proc.wait()
    if code != 0:
        raise RuntimeError("git clone exited with code " + str(code))
    return dest
