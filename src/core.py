"""Wine prefix setup & Windows app installer planner for SigmaOS-wine-installer.

The engine plans Wine prefixes (WINEPREFIX/WINEARCH env, wineboot init),
lists distro dependency packages, plans installer runs (exe/msi/msix) and
app launches with a prefix environment. Running wine is the thin
side-effecting execute layer -- self_test() only exercises the pure
plan/validate layer (no subprocess, no wine, no /home writes).
Principles: Defensive Programming, Fail-Fast, Separation of Concerns, KISS.
"""
import argparse, os, re, sys

ENGINE = {
    "name": "sigma-wine",
    "summary": "Plan Wine prefixes, dependency installs and app launches",
    "language": "python",
    "verbs": ["prefix-plan", "deps", "install-plan", "run"],
    "principles": ["Defensive Programming", "Fail-Fast",
                   "Separation of Concerns", "KISS", "Deterministic Testing"],
}

cli_doc = """\
$ sigma-wine prefix-plan games
WINEPREFIX=~/.local/share/wine/prefixes/games  WINEARCH=win64
$ sigma-wine deps --manager apt
cabextract p7zip-full samba wine wine32 wine64 winetricks
$ sigma-wine install-plan setup.msi --prefix games
wine msiexec /i setup.msi /qn
$ sigma-wine run Launcher.exe --prefix games -- --fullscreen
wine Launcher.exe --fullscreen
"""


class WineError(Exception):
    pass


DEFAULT_ROOT = os.path.expanduser("~/.local/share/wine/prefixes")
SUPPORTED_ARCH = ("win32", "win64")
INSTALLER_EXTS = (".exe", ".msi", ".msix", ".bat", ".cmd")
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

DEPS = {
    "apt": ["cabextract", "p7zip-full", "samba", "wine", "wine32", "wine64",
            "winetricks"],
    "dnf": ["cabextract", "p7zip", "samba-client", "wine", "winetricks"],
    "pacman": ["cabextract", "p7zip", "samba", "wine", "winetricks"],
}


# --------------------------------------------------------------------------- #
#  PURE plan layer
# --------------------------------------------------------------------------- #
def _check_prefix_name(name):
    if not isinstance(name, str) or not _NAME_RE.match(name) or name in (".", ".."):
        raise WineError(f"bad prefix name: {name!r} "
                        "(letters, digits, dot, underscore, dash only)")
    return name


def prefix_env(prefix, arch="win64"):
    """Build the environment for a Wine prefix (pure dict)."""
    _check_prefix_name(os.path.basename(str(prefix)))
    if arch not in SUPPORTED_ARCH:
        raise WineError(f"unknown architecture {arch!r} "
                        f"(choose from {', '.join(SUPPORTED_ARCH)})")
    return {"WINEPREFIX": str(prefix), "WINEARCH": arch, "WINEDEBUG": "-all"}


def prefix_plan(name, root=DEFAULT_ROOT, arch="win64"):
    """Plan a fresh Wine prefix: path, env and the wineboot init argv."""
    _check_prefix_name(name)
    prefix = os.path.join(os.path.expanduser(root), name)
    return {"name": name, "prefix": prefix, "env": prefix_env(prefix, arch),
            "argv": ["wineboot", "--init"]}


def deps(manager="apt"):
    """List distro packages required for Wine (deterministic order)."""
    if manager not in DEPS:
        raise WineError(f"unknown package manager {manager!r} "
                        f"(choose from {', '.join(sorted(DEPS))})")
    return list(DEPS[manager])


def install_plan(installer, prefix, arch="win64", silent=True):
    """Plan running a Windows installer inside a prefix."""
    if not isinstance(installer, str) or not installer:
        raise WineError("no installer given")
    ext = os.path.splitext(installer)[1].lower()
    if ext not in INSTALLER_EXTS:
        raise WineError(f"unsupported installer type: {ext or '(none)'} "
                        f"(choose from {', '.join(INSTALLER_EXTS)})")
    env = prefix_env(prefix, arch)
    if ext == ".msi":
        argv = ["wine", "msiexec", "/i", installer]
        if silent:
            argv.append("/qn")
    else:
        argv = ["wine", installer]
    return {"argv": argv, "env": env, "installer": installer, "prefix": prefix}


def run_plan(app, prefix, args=(), arch="win64"):
    """Plan launching a Windows application inside a prefix."""
    if not isinstance(app, str) or not app:
        raise WineError("no application given")
    try:
        args = list(args)
    except TypeError:
        raise WineError("args must be a list of strings")
    for a in args:
        if not isinstance(a, str) or "\x00" in a or "\n" in a:
            raise WineError(f"bad application argument: {a!r}")
    env = prefix_env(prefix, arch)
    return {"argv": ["wine", app] + args, "env": env, "app": app}


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    p.add_argument("--root", default=DEFAULT_ROOT, help="prefix root directory")
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("prefix-plan", help="plan a fresh Wine prefix")
    pp.add_argument("name")
    pp.add_argument("--arch", default="win64", choices=list(SUPPORTED_ARCH))
    dp = sub.add_parser("deps", help="list distro dependencies")
    dp.add_argument("--manager", default="apt", choices=sorted(DEPS))
    ip = sub.add_parser("install-plan", help="plan running an installer")
    ip.add_argument("installer")
    ip.add_argument("--prefix", required=True)
    ip.add_argument("--arch", default="win64", choices=list(SUPPORTED_ARCH))
    ip.add_argument("--no-silent", action="store_true")
    rn = sub.add_parser("run", help="plan launching an application")
    rn.add_argument("app")
    rn.add_argument("--prefix", required=True)
    rn.add_argument("--arch", default="win64", choices=list(SUPPORTED_ARCH))
    rn.add_argument("args", nargs="*", help="arguments passed to the app")
    return p


def _print_env(env):
    for k in sorted(env):
        print(f"{k}={env[k]}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "prefix-plan":
            plan = prefix_plan(args.name, args.root, args.arch)
            _print_env(plan["env"])
            print(" ".join(plan["argv"]) + f"   # prefix: {plan['prefix']}")
        elif args.cmd == "deps":
            print(" ".join(deps(args.manager)))
        elif args.cmd == "install-plan":
            plan = install_plan(args.installer, args.prefix, args.arch,
                                silent=not args.no_silent)
            print(" ".join(plan["argv"]))
            _print_env(plan["env"])
        elif args.cmd == "run":
            plan = run_plan(args.app, args.prefix, args.args, args.arch)
            print(" ".join(plan["argv"]))
            _print_env(plan["env"])
        return 0
    except WineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


# --------------------------------------------------------------------------- #
#  Tests (pure plan layer only -- no subprocess, no wine)
# --------------------------------------------------------------------------- #
def self_test() -> None:
    plan = prefix_plan("games")
    assert plan["prefix"].endswith(os.path.join("prefixes", "games"))
    assert plan["env"] == {"WINEPREFIX": plan["prefix"], "WINEARCH": "win64",
                           "WINEDEBUG": "-all"}, plan["env"]
    assert plan["argv"] == ["wineboot", "--init"]
    assert prefix_plan("apps", arch="win32")["env"]["WINEARCH"] == "win32"
    for bad in ("my game", "bad/name", "", "..", ".",
                ("game", DEFAULT_ROOT, "win16")):
        try:
            if isinstance(bad, tuple):
                prefix_plan(*bad)
            else:
                prefix_plan(bad)
        except WineError:
            pass
        else:
            raise AssertionError(f"bad prefix not rejected: {bad!r}")
    try:
        prefix_env("/opt/x", "arm64")
    except WineError:
        pass
    else:
        raise AssertionError("bad arch not rejected")

    apt = deps("apt")
    assert "wine" in apt and "winetricks" in apt and "cabextract" in apt
    assert apt == deps("apt")                       # deterministic
    assert "wine" in deps("pacman") and "wine" in deps("dnf")
    for mgr in ("apt", "dnf", "pacman"):
        assert all(isinstance(p, str) and p for p in deps(mgr))
    try:
        deps("yum")
    except WineError:
        pass
    else:
        raise AssertionError("unknown package manager not rejected")

    plan = install_plan("setup.msi", "/home/u/.local/share/wine/prefixes/games")
    assert plan["argv"] == ["wine", "msiexec", "/i", "setup.msi", "/qn"]
    assert plan["env"]["WINEPREFIX"].endswith("games")
    plan = install_plan("setup.exe", "/pfx", silent=False)
    assert plan["argv"] == ["wine", "setup.exe"]
    plan = install_plan("bundle.msix", "/pfx")
    assert plan["argv"] == ["wine", "bundle.msix"]
    for bad in ("setup.txt", "", "/bin/evil", None):
        try:
            install_plan(bad, "/pfx")
        except WineError:
            pass
        else:
            raise AssertionError(f"bad installer not rejected: {bad!r}")

    plan = run_plan("Launcher.exe", "/pfx", ["--fullscreen", "-novid"])
    assert plan["argv"] == ["wine", "Launcher.exe", "--fullscreen", "-novid"]
    assert plan["env"]["WINEDEBUG"] == "-all"
    for bad in (("", "/pfx", ()), ("App.exe", "/pfx", ["ok", "bad\narg"]),
                ("App.exe", "/pfx", ["\x00"]), ("App.exe", "/pfx", [42])):
        try:
            run_plan(*bad)
        except WineError:
            pass
        else:
            raise AssertionError(f"bad run plan not rejected: {bad!r}")
    try:
        run_plan("App.exe", "bad prefix")
    except WineError:
        pass
    else:
        raise AssertionError("bad prefix name in run_plan not rejected")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
