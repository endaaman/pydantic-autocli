#!/usr/bin/env python3
"""
Tests focused on argument class resolution for pydantic-autocli.
Testing naming convention vs type annotation priority and warning messages.
"""

import unittest
import sys
import logging
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param
from unittest.mock import patch, MagicMock, call
import asyncio


# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_class_resolution")


class CLIClassResolutionTest(unittest.TestCase):
    """Test CLI argument class resolution functionality, especially when there are conflicts."""
    
    def setUp(self):
        # Enable debug logging for pydantic_autocli
        self.autocli_logger = logging.getLogger("pydantic_autocli")
        self.original_level = self.autocli_logger.level
        self.autocli_logger.setLevel(logging.DEBUG)
        
    def tearDown(self):
        # Restore original logging level
        self.autocli_logger.setLevel(self.original_level)
    
    def test_type_annotation_priority(self):
        """Test that type annotation takes priority over naming convention."""
        
        class TypeAnnotationCLI(AutoCLI):
            # Naming convention class (would match run_command)
            class CommandArgs(BaseModel):
                name: str = param("default", l="--name", s="-n")
                verbose: bool = param(False, l="--verbose")
            
            # Type annotation class - should be used instead
            class CustomArgs(BaseModel):
                value: int = param(42, l="--value", s="-v")
                flag: bool = param(False, l="--flag", s="-f")
            
            # Type annotation in method signature should take precedence
            def run_command(self, args: CustomArgs):
                return f"Value: {args.value}, Flag: {args.flag}"
        
        # Create CLI instance
        cli = TypeAnnotationCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_command method to capture its result
        original_method = cli.run_command
        cli.run_command = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI with direct arguments
        argv = ["test_script.py", "command", "--value", "123", "--flag"]
        with patch('sys.exit'):
            cli.run(argv)
        
        # Verify the method was called with correct args (using CustomArgs)
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Value: 123, Flag: True")
        
        # Verify that CustomArgs was used as expected
        self.assertEqual(cli.method_args_mapping["command"].__name__, "CustomArgs")
    
    @patch('builtins.print')  # Patch print to capture the warning message
    def test_naming_convention_conflict_warning(self, mock_print):
        """Test that a warning is issued when there's a conflict between naming convention and type annotation."""
        
        class ConflictCLI(AutoCLI):
            # Args class that follows naming convention
            class CommandArgs(BaseModel):
                name: str = param("default", l="--name")
                verbose: bool = param(False, l="--verbose", s="-v")
            
            # Different args class specified by type annotation
            class CustomArgs(BaseModel):
                value: int = param(42, l="--value", s="-v")
                flag: bool = param(False, l="--flag", s="-f")
            
            # Type annotation takes precedence over naming convention
            def run_command(self, args: CustomArgs):
                return f"Value: {args.value}, Flag: {args.flag}"
        
        # Create CLI instance - this should trigger the warning
        cli = ConflictCLI()
        
        # Verify the warning message was printed
        warning_printed = False
        for call_args in mock_print.call_args_list:
            call_str = str(call_args)
            if "Warning" in call_str and "has both a type annotation (CustomArgs) and a naming convention class (CommandArgs)" in call_str:
                warning_printed = True
                break
        
        self.assertTrue(warning_printed, "Warning about conflict between type annotation and naming convention was not displayed")
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_command method to capture its result
        original_method = cli.run_command
        cli.run_command = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI with direct arguments
        argv = ["test_script.py", "command", "--value", "123", "--flag"]
        with patch('sys.exit'):
            cli.run(argv)
        
        # Verify the method was called with correct args (using CustomArgs)
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Value: 123, Flag: True")
    
    def test_naming_convention_fallback(self):
        """Test that naming convention is used when no type annotation is present."""
        
        class NamingConventionCLI(AutoCLI):
            # Naming convention class that should be used
            class CommandArgs(BaseModel):
                name: str = param("default", l="--name", s="-n")
                verbose: bool = param(False, l="--verbose", s="-v")
            
            # No type annotation, so naming convention should be used
            def run_command(self, args):
                return f"Name: {args.name}, Verbose: {args.verbose}"
        
        # Create CLI instance
        cli = NamingConventionCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_command method to capture its result
        original_method = cli.run_command
        cli.run_command = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI with direct arguments
        argv = ["test_script.py", "command", "--name", "test-user", "--verbose"]
        with patch('sys.exit'):
            cli.run(argv)
        
        # Verify the method was called with correct args (using CommandArgs)
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Name: test-user, Verbose: True")
        
        # Verify that CommandArgs was used
        self.assertEqual(cli.method_args_mapping["command"].__name__, "CommandArgs")
    
    def test_default_args_fallback(self):
        """Test that default args are used when neither type annotation nor naming convention match."""
        
        class FallbackCLI(AutoCLI):
            # Custom CommonArgs class
            class CommonArgs(AutoCLI.CommonArgs):
                verbose: bool = param(False, l="--verbose", s="-v")
            
            # No matching naming convention, no type annotation
            def run_custom_command(self, args):
                return f"Verbose: {args.verbose}"
        
        # Create CLI instance
        cli = FallbackCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run method to capture its result
        original_method = cli.run_custom_command
        cli.run_custom_command = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI with direct arguments
        argv = ["test_script.py", "custom-command", "--verbose"]
        with patch('sys.exit'):
            cli.run(argv)
        
        # Verify the method was called with correct args (using CommonArgs)
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Verbose: True")
        
        # Verify that CommonArgs was used
        self.assertEqual(cli.method_args_mapping["custom_command"].__name__, "CommonArgs")
    
    @patch('asyncio.run')  # Patch asyncio.run to capture the coroutine
    def test_async_type_annotation(self, mock_asyncio_run):
        """Test that type annotations work correctly with async methods."""
        
        class AsyncCLI(AutoCLI):
            # Type annotation class
            class CustomArgs(BaseModel):
                delay: float = param(0.1, l="--delay", s="-d")
                message: str = param("Hello", l="--message", s="-m")
            
            # Async method with type annotation
            async def run_async_command(self, args: CustomArgs):
                # In a real implementation, we would await something here
                return f"Async {args.message} with delay {args.delay}"
        
        # Setup asyncio.run to return the result directly
        result = "Async World with delay 0.5"
        mock_asyncio_run.return_value = result
        
        # Create CLI instance
        cli = AsyncCLI()
        
        # Run the CLI with direct arguments
        argv = ["test_script.py", "async-command", "--delay", "0.5", "--message", "World"]
        with patch('sys.exit'):
            cli.run(argv)
        
        # Verify that asyncio.run was called (indicating async method execution)
        mock_asyncio_run.assert_called_once()
        
        # Check that the CLI used the right args class
        self.assertEqual(cli.method_args_mapping["async_command"].__name__, "CustomArgs")
    
    @patch('asyncio.run')  # Patch asyncio.run to capture the coroutine
    def test_async_naming_convention(self, mock_asyncio_run):
        """Test that naming convention works correctly with async methods."""
        
        class AsyncNamingCLI(AutoCLI):
            # Naming convention class
            class AsyncCommandArgs(BaseModel):
                count: int = param(1, l="--count", s="-c")
                verbose: bool = param(False, l="--verbose", s="-v")
            
            # Async method using naming convention
            async def run_async_command(self, args):
                # In a real implementation, we would await something here
                result = f"Count: {args.count}"
                if args.verbose:
                    result += " (verbose)"
                return result
        
        # Setup asyncio.run to return the result directly
        result = "Count: 5 (verbose)"
        mock_asyncio_run.return_value = result
        
        # Create CLI instance
        cli = AsyncNamingCLI()
        
        # Run the CLI with direct arguments
        argv = ["test_script.py", "async-command", "--count", "5", "--verbose"]
        with patch('sys.exit'):
            cli.run(argv)
        
        # Verify that asyncio.run was called (indicating async method execution)
        mock_asyncio_run.assert_called_once()
        
        # Check that the CLI used the right args class
        self.assertEqual(cli.method_args_mapping["async_command"].__name__, "AsyncCommandArgs")
    
    @patch('builtins.print')  # Patch print to capture the warning message
    @patch('asyncio.run')  # Patch asyncio.run to capture the coroutine
    def test_async_conflict_warning(self, mock_asyncio_run, mock_print):
        """Test that warnings work correctly with async methods that have naming conflicts."""
        
        class AsyncConflictCLI(AutoCLI):
            # Naming convention class
            class AsyncCommandArgs(BaseModel):
                name: str = param("default", l="--name", s="-n")
            
            # Type annotation class
            class CustomArgs(BaseModel):
                value: int = param(42, l="--value", s="-v")
            
            # Async method with type annotation (conflict with naming convention)
            async def run_async_command(self, args: CustomArgs):
                # In a real implementation, we would await something here
                return f"Value: {args.value}"
        
        # Setup asyncio.run to return the result directly
        result = "Value: 123"
        mock_asyncio_run.return_value = result
        
        # Create CLI instance - this should trigger the warning
        cli = AsyncConflictCLI()
        
        # Verify the warning message was printed
        warning_printed = False
        for call_args in mock_print.call_args_list:
            call_str = str(call_args)
            if "Warning" in call_str and "has both a type annotation (CustomArgs) and a naming convention class (AsyncCommandArgs)" in call_str:
                warning_printed = True
                break
        
        self.assertTrue(warning_printed, "Warning about conflict between type annotation and naming convention was not displayed for async method")
        
        # Run the CLI with direct arguments
        argv = ["test_script.py", "async-command", "--value", "123"]
        with patch('sys.exit'):
            cli.run(argv)
        
        # Verify that asyncio.run was called (indicating async method execution)
        mock_asyncio_run.assert_called_once()
        
        # Check that the CLI used the type annotation args class (which takes precedence)
        self.assertEqual(cli.method_args_mapping["async_command"].__name__, "CustomArgs")


if __name__ == "__main__":
    unittest.main() 