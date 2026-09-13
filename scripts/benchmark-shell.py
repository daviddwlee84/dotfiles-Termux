#!/usr/bin/env python3
"""Measure native interactive rc-to-first-prompt latency in owned PTYs.

Run on the device; no SSH transport time, login profile, or OS cache eviction.
Cold means an empty, private completion/dev/prompt cache. No user history is kept.
"""
import argparse
import json
import math
import os
from pathlib import Path
import pty
import select
import shlex
import signal
import statistics
import subprocess
import tempfile
import time
import uuid


def measure(binary, args, cwd, env, marker):
    start = time.monotonic()
    pid, master = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvpe(str(binary), [str(binary), *args], env)
    data = b""
    try:
        deadline = start + 10
        while marker not in data and time.monotonic() < deadline:
            if select.select([master], [], [], 0.2)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                data = (data + chunk)[-65536:]
        elapsed = (time.monotonic() - start) * 1000
        if marker not in data:
            raise RuntimeError("shell never reached its prompt: " + data[-1500:].decode(errors="replace"))
        os.write(master, b"exit\n")
        return elapsed
    finally:
        os.close(master)
        for _ in range(20):
            if os.waitpid(pid, os.WNOHANG)[0]:
                break
            time.sleep(0.05)
        else:
            os.killpg(pid, signal.SIGKILL)
            os.waitpid(pid, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-config", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--managed-bash", action="store_true", help="compare the new managed Bash config instead of the existing rc")
    args = parser.parse_args()
    if args.samples < 30:
        parser.error("at least 30 warm samples are required")
    prefix = Path(os.environ["PREFIX"])
    subprocess.run([str(prefix / "bin/bash"), str(Path(__file__).parent / "guard.sh")], check=True)
    candidate = args.candidate_config.resolve()
    with tempfile.TemporaryDirectory(prefix="shell-bench-", dir=prefix / "tmp") as temporary:
        root = Path(temporary)
        records = {}
        for label, cwd in (("home", Path.home()), ("repo", args.repo.resolve())):
            specs = {}
            for kind in ("bash", "zsh"):
                private = root / label / kind
                private.mkdir(parents=True)
                marker = "__DFT_READY_" + uuid.uuid4().hex + "__"
                history = shlex.quote(str(private / "history"))
                if kind == "bash":
                    body = (f'source {shlex.quote(str(candidate / "shell.bash"))}\n' if args.managed_bash else 'source "$HOME/.bashrc"\n') + f'HISTFILE={history}\n'
                    body += '__dft_bench_precmd() { PS1="${PS1}' + marker + '"; }\nPROMPT_COMMAND+=(__dft_bench_precmd)\n'
                    rc = private / "bashrc"
                    argv = ["--noprofile", "--rcfile", str(rc), "-i"]
                else:
                    body = f'source {shlex.quote(str(candidate / "shell.zsh"))}\nHISTFILE={history}\n'
                    body += '__dft_bench_precmd() { PROMPT="${PROMPT}' + marker + '"; }\nprecmd_functions+=(__dft_bench_precmd)\n'
                    rc = private / ".zshrc"
                    argv = ["-i"]
                rc.write_text(body)
                env = dict(os.environ, TERM="xterm-256color", ZDOTDIR=str(private),
                           XDG_CACHE_HOME=str(private / "cache"),
                           STARSHIP_CACHE=str(private / "cache/starship"),
                           DOTFILES_TERMUX_CACHE_DIR=str(private / "cache/termux"))
                env.pop("BASH_ENV", None)
                env.pop("ENV", None)
                if kind == "zsh" or args.managed_bash:
                    env["DOTFILES_TERMUX_CONFIG_DIR"] = str(candidate)
                else:
                    env.pop("DOTFILES_TERMUX_CONFIG_DIR", None)
                specs[kind] = (prefix / "bin" / kind, argv, cwd, env, marker.encode())
                records[f"{label}_{kind}"] = {"cold_ms": measure(*specs[kind]), "warm_ms": []}
            # Interleave to reduce time/temperature/load bias between candidates.
            for _ in range(args.samples):
                for kind in ("bash", "zsh"):
                    records[f"{label}_{kind}"]["warm_ms"].append(measure(*specs[kind]))
        summary = {}
        for key, value in records.items():
            samples = sorted(value["warm_ms"])
            summary[key] = {"cold_ms": round(value["cold_ms"], 2),
                            "median_ms": round(statistics.median(samples), 2),
                            "p95_ms": round(samples[math.ceil(len(samples) * .95) - 1], 2)}
        passed = all(summary[f"{label}_zsh"]["cold_ms"] <= 1000
                     and summary[f"{label}_zsh"]["median_ms"] - summary[f"{label}_bash"]["median_ms"] <= 100
                     and summary[f"{label}_zsh"]["p95_ms"] - summary[f"{label}_bash"]["p95_ms"] <= 200
                     for label in ("home", "repo"))
        print(json.dumps({"samples": args.samples, "managed_bash": args.managed_bash, "method": "native PTY interactive rc to first prompt",
                          "results": summary, "passed": passed}, indent=2))
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
