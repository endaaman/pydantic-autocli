#!/usr/bin/env python3
"""
Tests for --help priority handling.
"""

import unittest
import io
from contextlib import redirect_stdout
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param
from unittest.mock import patch


class ExitCalled(Exception):
    """Exception to signal sys.exit was called."""
    def __init__(self, code):
        self.code = code


def mock_exit(code):
    raise ExitCalled(code)


class TestHelpPriority(unittest.TestCase):
    """Test --help takes priority over all other options."""

    def _run_and_capture(self, cli, argv):
        """Helper to run CLI and capture output and exit code."""
        exit_code = None
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with patch('sys.exit', side_effect=mock_exit):
                try:
                    cli.run(argv)
                except ExitCalled as e:
                    exit_code = e.code
        return stdout.getvalue(), exit_code

    def test_help_without_subcommand_no_default(self):
        """Test --help shows full help when no subcommand and no default."""

        class NormalCLI(AutoCLI):
            class GreetArgs(BaseModel):
                name: str = param("World")

            def run_greet(self, args):
                return f"Hello, {args.name}!"

        cli = NormalCLI()
        output, exit_code = self._run_and_capture(cli, ['script.py', '--help'])

        self.assertEqual(exit_code, 0)
        self.assertIn('AutoCLI patterns', output)
        self.assertIn('greet', output)

    def test_help_without_subcommand_with_default(self):
        """Test --help shows default help when no subcommand but default exists."""

        class DefaultCLI(AutoCLI):
            class DefaultArgs(BaseModel):
                message: str = param("Hello", l="--message")

            def run_default(self, args):
                return f"default:{args.message}"

        cli = DefaultCLI()
        output, exit_code = self._run_and_capture(cli, ['script.py', '--help'])

        self.assertEqual(exit_code, 0)
        # Should show default command help, not full help
        self.assertIn('--message', output)
        self.assertNotIn('AutoCLI patterns', output)

    def test_help_with_subcommand(self):
        """Test --help shows subcommand help when subcommand provided."""

        class MultiCLI(AutoCLI):
            class GreetArgs(BaseModel):
                name: str = param("World", l="--name")

            def run_greet(self, args):
                return f"Hello, {args.name}!"

            class CountArgs(BaseModel):
                value: int = param(0, l="--value")

            def run_count(self, args):
                return f"Count: {args.value}"

        cli = MultiCLI()
        output, exit_code = self._run_and_capture(cli, ['script.py', 'greet', '--help'])

        self.assertEqual(exit_code, 0)
        self.assertIn('--name', output)
        self.assertNotIn('--value', output)
        self.assertNotIn('AutoCLI patterns', output)

    def test_help_priority_over_required_args(self):
        """Test --help works even with required arguments not provided."""

        class RequiredCLI(AutoCLI):
            class FileArgs(BaseModel):
                filename: str = param(..., l="--file")  # required

            def run_file(self, args):
                return f"File: {args.filename}"

        cli = RequiredCLI()
        output, exit_code = self._run_and_capture(cli, ['script.py', 'file', '--help'])

        self.assertEqual(exit_code, 0)
        self.assertIn('--file', output)

    def test_help_priority_over_other_args(self):
        """Test --help takes priority even when other args are provided."""

        class TestCLI(AutoCLI):
            class TestArgs(BaseModel):
                value: str = param("default", l="--value")

            def run_test(self, args):
                return f"Value: {args.value}"

        cli = TestCLI()
        output, exit_code = self._run_and_capture(cli, ['script.py', 'test', '--value', 'something', '--help'])

        self.assertEqual(exit_code, 0)
        self.assertIn('--value', output)


class TestHelpReserved(unittest.TestCase):
    """Test that '--help' option is reserved."""

    def test_help_field_raises_error(self):
        """Test that defining 'help' field raises ValueError."""

        with self.assertRaises(ValueError) as ctx:
            class BadCLI(AutoCLI):
                class BadArgs(BaseModel):
                    name: str = param("World")
                    help: bool = False

                def run_bad(self, args):
                    pass

            BadCLI()

        self.assertIn("--help", str(ctx.exception))
        self.assertIn("reserved", str(ctx.exception))

    def test_help_option_raises_error(self):
        """Test that using l='--help' raises ValueError."""

        with self.assertRaises(ValueError) as ctx:
            class BadCLI(AutoCLI):
                class BadArgs(BaseModel):
                    name: str = param("World")
                    show_help: bool = param(False, l="--help")

                def run_bad(self, args):
                    pass

            BadCLI()

        self.assertIn("--help", str(ctx.exception))
        self.assertIn("reserved", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
