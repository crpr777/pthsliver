# picklesliver

`picklesliver` is a small proof-of-concept generator for demonstrating Python
`.pth` startup-file persistence during sanctioned red-team engagements and
capture-the-flag exercises. It writes a single `.pth` file that starts an
executable already present at an absolute path on the target system.

> [!CAUTION]
> This project creates a persistence artifact. Use it only on systems you own
> or have explicit permission to test. Do not use this repository to distribute
> implants, manage command-and-control infrastructure, or support an active
> unauthorized campaign. You are responsible for complying with applicable
> law, engagement rules, and platform policies.

No payloads, binaries, downloaders, or C2 configuration are included.

## Why this exists

Python processes executable `import` lines in `.pth` files found in active
site-packages directories during interpreter startup. Defenders can use this
project to reproduce and detect that behavior in an isolated lab; authorized
operators can use it to validate whether controls alert on the technique.

## Requirements

- Python 3.9 or newer on the system running the generator
- An absolute, target-native path for the executable that will already exist on
  the authorized test target

The generator itself has no third-party dependencies.

## Usage

```text
python3 picklesliver.py /opt/lab/demo-agent --os linux -o picklesliver.pth
python3 picklesliver.py /tmp/demo-agent --os macos -o picklesliver.pth
python3 picklesliver.py 'C:\Lab\demo-agent.exe' --os windows -o picklesliver.pth
```

The positional argument is the path **on the target**, not a path to a local
file being packaged. `picklesliver` never copies or embeds the executable.

Existing output files are not overwritten unless `--force` is supplied.
Run `python3 picklesliver.py --help` for all options.

### macOS quarantine removal

Quarantine removal is opt-in. Include `--remove-quarantine` when generating the
artifact for a macOS host:

```text
python3 picklesliver.py /Users/Shared/demo-agent \
  --os macos \
  --remove-quarantine \
  -o picklesliver.pth
```

This does **not** modify a file on the generator system. It embeds a call to
`/usr/bin/xattr -d com.apple.quarantine` in the generated `.pth` line. Later,
when a macOS Python interpreter processes that `.pth` file from one of its
active site-packages directories, the line performs these actions in order:

1. Adds executable permission bits to `/Users/Shared/demo-agent`.
2. Requests removal of the `com.apple.quarantine` attribute.
3. Starts the executable.

The macOS account running Python must have permission to modify the referenced
file. A missing quarantine attribute is harmless: `xattr` can return a nonzero
status, which the generated line deliberately ignores before continuing.

To confirm that removal was embedded without executing the artifact, inspect
the generated line:

```text
grep -F "com.apple.quarantine" picklesliver.pth
```

To trigger it in an authorized disposable lab, place the `.pth` file in an
active site-packages directory reported by `python3 -m site`, then start that
same interpreter normally. Python can be invoked with `-S` to disable automatic
`site` processing; in that case the `.pth` file will not run. This option does
not bypass code-signing, execution-policy, or other macOS security controls.

## Safe lab validation

Use a disposable virtual machine or container and a harmless executable you
control. Inspect the generated artifact before moving it anywhere:

```text
python3 -m unittest discover -s tests -v
python3 -m py_compile picklesliver.py
python3 picklesliver.py /tmp/demo-agent --os linux -o /tmp/picklesliver.pth
cat /tmp/picklesliver.pth
```

The automated tests only inspect and compile generated text; they do not launch
the generated command.

## Detection and cleanup

Defenders should inventory `.pth` files in system and user site-packages
directories and review executable lines beginning with `import`. Removal means
deleting the unauthorized `.pth` artifact and separately containing or removing
the referenced executable according to the organization's incident-response
process. Preserve evidence first when an investigation is active.

## Responsible use and reporting

See [SECURITY.md](SECURITY.md) for reporting security or abuse concerns. This
repository intentionally does not accept or host executable payloads.

## License

Released under the [MIT License](LICENSE).
