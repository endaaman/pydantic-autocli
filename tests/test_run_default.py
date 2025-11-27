#!/usr/bin/env python3
"""
Tests for run_default command functionality.
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


class TestRunDefault(unittest.TestCase):
    """Test run_default command functionality."""

    def test_run_default_executes_without_subcommand(self):
        """Test that run_default is executed when no subcommand is provided."""

        class DefaultCLI(AutoCLI):
            class DefaultArgs(BaseModel):
                message: str = param("Hello", l="--message", s="-m")

            def run_default(self, args):
                return f"default:{args.message}"

            class OtherArgs(BaseModel):
                value: int = param(0)

            def run_other(self, args):
                return f"other:{args.value}"

        cli = DefaultCLI()
        result_holder = {}

        original_default = cli.run_default
        def capture_default(args):
            result_holder['result'] = original_default(args)
            return True
        cli.run_default = capture_default

        with patch('sys.exit'):
            cli.run(['script.py'])

        self.assertEqual(result_holder['result'], "default:Hello")

    def test_run_default_with_args(self):
        """Test that run_default receives arguments correctly."""

        class DefaultCLI(AutoCLI):
            class DefaultArgs(BaseModel):
                message: str = param("Hello", l="--message", s="-m")

            def run_default(self, args):
                return f"default:{args.message}"

        cli = DefaultCLI()
        result_holder = {}

        original_default = cli.run_default
        def capture_default(args):
            result_holder['result'] = original_default(args)
            return True
        cli.run_default = capture_default

        with patch('sys.exit'):
            cli.run(['script.py', '--message', 'Custom'])

        self.assertEqual(result_holder['result'], "default:Custom")

    def test_default_subcommand_explicit(self):
        """Test that 'default' subcommand works explicitly."""

        class DefaultCLI(AutoCLI):
            class DefaultArgs(BaseModel):
                message: str = param("Hello", l="--message")

            def run_default(self, args):
                return f"default:{args.message}"

        cli = DefaultCLI()
        result_holder = {}

        original_default = cli.run_default
        def capture_default(args):
            result_holder['result'] = original_default(args)
            return True
        cli.run_default = capture_default

        with patch('sys.exit'):
            cli.run(['script.py', 'default', '--message', 'Explicit'])

        self.assertEqual(result_holder['result'], "default:Explicit")

    def test_no_default_shows_help(self):
        """Test that without run_default, no subcommand shows help."""

        class NormalCLI(AutoCLI):
            class GreetArgs(BaseModel):
                name: str = param("World")

            def run_greet(self, args):
                return f"Hello, {args.name}!"

        cli = NormalCLI()
        exit_code = None

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with patch('sys.exit', side_effect=mock_exit):
                try:
                    cli.run(['script.py'])
                except ExitCalled as e:
                    exit_code = e.code

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn('greet', output)

    def test_default_listed_in_subcommands(self):
        """Test that 'default' appears in subcommand list when defined."""

        class DefaultCLI(AutoCLI):
            class DefaultArgs(BaseModel):
                message: str = param("Hello")

            def run_default(self, args):
                """The default command."""
                return True

        cli = DefaultCLI()
        self.assertIn('default', cli.subparsers_info)


if __name__ == "__main__":
    unittest.main()
