"""
Entry point for running Certbox as a module.
Usage: python -m certbox [command] [options]
"""

from certbox.cli import cli


def main():
    """Main entry point for console script."""
    cli()


if __name__ == "__main__":
    main()