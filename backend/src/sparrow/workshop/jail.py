"""The bubblewrap jail every agent session and build runs inside.

What the jail can see, and nothing else:

    /usr (+ the /bin /lib /lib64 /sbin links)   read-only   the OS
    a few /etc files                             read-only   DNS, TLS roots, users
    the Node prefix                              read-only   to run next
    the shared node_modules                      read-only   mounted AT <ws>/node_modules
    the DeepSeek Harness runtime                 read-only   the agent itself
    the studio profile patch                     read-only   its configuration
    <project>/workspace                          read-write  the website
    <project>/dsh-home                           read-write  the agent's sessions
    <project>/dsh-home/profiles/sdk/{cordis.patch.yml,package.json}
                                                 read-only   its configuration, once written
    /tmp                                         private tmpfs

Every path is bound at its real location, so the cwd the SDK passes and the
paths the agent prints mean the same thing inside and out.

The environment is cleared and rebuilt from an explicit list: the workshop's
own environment never leaks in, even in development where it shares a machine
with the office. Every namespace is unshared except the network — the agent has
to reach the office's LLM gateway, and in production the workshop host's
firewall is what limits it to that one destination.

DeepSeek Harness runs its own bwrap sandbox for the shell inside this one;
nesting works (measured on kernel 7.0 with bwrap 0.9).
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

# /etc entries the toolchain needs. `-try` because not every distro has all of
# them, and a missing optional file must not stop the jail from starting.
_ETC = ("resolv.conf", "hosts", "passwd", "group", "nsswitch.conf",
        "ssl", "ca-certificates", "alternatives", "localtime")


@dataclass(frozen=True)
class JailMounts:
    workspace: Path
    home: Path
    node: Path
    node_modules: Path
    readonly: tuple[Path, ...] = ()
    # Read-only re-binds of paths INSIDE the writable mounts, applied after them.
    readonly_over: tuple[Path, ...] = ()


def jail_argv(m: JailMounts, command: list[str], env: dict[str, str]) -> list[str]:
    """The argv that runs `command` jailed. Pure, so it can be tested and read."""
    a = ["bwrap",
         "--unshare-all", "--share-net", "--die-with-parent", "--new-session",
         "--ro-bind", "/usr", "/usr",
         "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
         "--symlink", "usr/lib64", "/lib64", "--symlink", "usr/sbin", "/sbin",
         "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    for name in _ETC:
        a += ["--ro-bind-try", f"/etc/{name}", f"/etc/{name}"]
    a += ["--ro-bind", str(m.node), str(m.node)]
    for p in m.readonly:
        a += ["--ro-bind", str(p), str(p)]
    a += ["--bind", str(m.workspace), str(m.workspace),
          "--bind", str(m.home), str(m.home),
          # After the workspace bind, so it lands on top of it.
          "--ro-bind", str(m.node_modules), str(m.workspace / "node_modules")]
    for p in m.readonly_over:
        a += ["--ro-bind", str(p), str(p)]
    base_env = {
        "PATH": f"{m.node}/bin:/usr/bin",
        "HOME": str(m.home),
        "LANG": "C.UTF-8",
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    a += ["--clearenv"]
    for k, v in {**base_env, **env}.items():
        a += ["--setenv", k, v]
    a += ["--chdir", str(m.workspace), "--", *command]
    return a


def launcher_script(m: JailMounts, runtime: Path, passthrough: tuple[str, ...]) -> str:
    """A shell script the DeepSeek SDK can exec as its `dsh` binary.

    The SDK launches `dsh_bin` with its own arguments and environment; this
    wraps that in the jail. Secrets in `passthrough` (the gateway token) are
    read from the launching environment at exec time, so they never sit in the
    script on disk.
    """
    argv = jail_argv(m, [str(runtime)], {})
    cut = argv.index("--chdir")
    head = " ".join(shlex.quote(x) for x in argv[:cut])
    fwd = " ".join(f'--setenv {k} "${{{k}:?}}"' for k in ("DSH_HOME", *passthrough))
    tail = " ".join(shlex.quote(x) for x in argv[cut:])
    return f'#!/bin/sh\nexec {head} {fwd} {tail} "$@"\n'
