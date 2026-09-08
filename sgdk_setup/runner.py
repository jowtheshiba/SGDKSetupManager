import subprocess


class PhaseError(Exception):
    pass


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
