"""Offline command entry point; the visual UI is loaded only on demand."""
import sys


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "ui":
        import argparse
        parser = argparse.ArgumentParser(prog="spoollens ui", description="Visual fixed-width rule authoring")
        parser.add_argument("source", nargs="?", help="Read-only TXT/PRN source")
        parser.add_argument("--rule", help="Reopen an existing JSON rule")
        args = parser.parse_args(sys.argv[2:])
        try:
            from .tui import launch
            launch(args.source, args.rule)
        except ImportError as error:
            parser.exit(1, f"Terminal UI unavailable: {error}. Use Linux/macOS with Python curses; see README.\n")
        except (ValueError, OSError) as error:
            parser.exit(1, f"Cannot open UI: {error}\n")
    else:
        from .cli import main as cli_main
        return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
