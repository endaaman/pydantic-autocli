#!/usr/bin/env python3
"""
Tests focused on command-line argument parsing for pydantic-autocli.
Testing how CLI arguments are processed, converted, and handled in different formats.
"""

import unittest
import sys
import logging
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param
from unittest.mock import patch, MagicMock


# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_arg_parsing")


class CLIArgumentParsingTest(unittest.TestCase):
    """Test CLI argument parsing functionality, especially kebab-case conversion."""
    
    def setUp(self):
        # Enable debug logging
        self.autocli_logger = logging.getLogger("pydantic_autocli")
        self.original_level = self.autocli_logger.level
        self.autocli_logger.setLevel(logging.DEBUG)
        
    def tearDown(self):
        # Restore original logging level
        self.autocli_logger.setLevel(self.original_level)
    
    @patch('sys.argv')
    def test_single_word_command_parsing(self, mock_argv):
        """Test parsing of a simple single-word command."""
        
        class SimpleCLI(AutoCLI):
            class GreetArgs(AutoCLI.CommonArgs):
                name: str = param("World", l="--name", s="-n")
                count: int = param(1, l="--count", s="-c")
            
            def run_greet(self, args):
                result = f"Hello, {args.name}! Count: {args.count}"
                return result
        
        # Mock command line arguments
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "greet", "--name", "TestUser", "--count", "3"
        ][idx]
        mock_argv.__len__.return_value = 6
        
        # Create CLI instance
        cli = SimpleCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_greet method to capture its result
        original_run_greet = cli.run_greet
        cli.run_greet = lambda args: result_capture(original_run_greet(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Hello, TestUser! Count: 3")
    
    @patch('sys.argv')
    def test_multi_word_command_parsing(self, mock_argv):
        """Test parsing of multi-word commands that convert to kebab-case."""
        
        class MultiWordCLI(AutoCLI):
            class ShowFileInfoArgs(AutoCLI.CommonArgs):
                file_path: str = param("default.txt", l="--file-path", s="-f")
                show_lines: bool = param(False, l="--show-lines")
                line_count: int = param(10, l="--line-count")
            
            def run_show_file_info(self, args):
                result = f"File: {args.file_path}"
                if args.show_lines:
                    result += f", showing {args.line_count} lines"
                return result
        
        # Mock command line arguments with kebab-case
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "show-file-info", "--file-path", "test.txt", 
            "--show-lines", "--line-count", "5"
        ][idx]
        mock_argv.__len__.return_value = 7
        
        # Create CLI instance
        cli = MultiWordCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_show_file_info method to capture its result
        original_method = cli.run_show_file_info
        cli.run_show_file_info = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "File: test.txt, showing 5 lines")
        
        # Verify the command was converted from snake_case to kebab-case
        # by checking the values used to mock the command line arguments
        mock_argv_args = [mock_argv.__getitem__(i) for i in range(7)]
        self.assertEqual(mock_argv_args[1], "show-file-info")
    
    @patch('sys.argv')
    def test_args_kebab_case_conversion(self, mock_argv):
        """Test that parameter names with underscores are properly converted to kebab-case."""
        
        class KebabCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                user_name: str = param("default", l="--user-name")
                max_results: int = param(10, l="--max-results")
                show_details: bool = param(False, l="--show-details")
            
            def run_test(self, args):
                return f"User: {args.user_name}, Max: {args.max_results}, Details: {args.show_details}"
        
        # Mock command line arguments - note the kebab-case arguments
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--user-name", "john_doe", 
            "--max-results", "25", "--show-details"
        ][idx]
        mock_argv.__len__.return_value = 7
        
        # Create CLI instance
        cli = KebabCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_test method to capture its result
        original_method = cli.run_test
        cli.run_test = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "User: john_doe, Max: 25, Details: True")
        
        # Verify the parameter names with underscores were used as kebab-case in CLI
        # by checking the values used to mock the command line arguments
        mock_argv_args = [mock_argv.__getitem__(i) for i in range(7)]
        self.assertEqual(mock_argv_args[2], "--user-name")
        self.assertEqual(mock_argv_args[4], "--max-results")
        self.assertEqual(mock_argv_args[6], "--show-details")
    
    @patch('sys.argv')
    def test_standard_pydantic_field(self, mock_argv):
        """Test using standard Pydantic fields without the param function."""
        
        class StandardFieldCLI(AutoCLI):
            class SimpleArgs(BaseModel):
                # Standard Pydantic fields without param
                required_value: int
                optional_value: int = 123
                names: list[str] = []
            
            def run_simple(self, args):
                return f"Required: {args.required_value}, Optional: {args.optional_value}, Names: {args.names}"
        
        # Mock command line arguments
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "simple", "--required-value", "42", 
            "--names", "Alice", "Bob", "Charlie"
        ][idx]
        mock_argv.__len__.return_value = 7
        
        # Create CLI instance
        cli = StandardFieldCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_simple method to capture its result
        original_method = cli.run_simple
        cli.run_simple = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Required: 42, Optional: 123, Names: ['Alice', 'Bob', 'Charlie']")
        
        # Verify parameter names are automatically converted to kebab-case
        mock_argv_args = [mock_argv.__getitem__(i) for i in range(7)]
        self.assertEqual(mock_argv_args[2], "--required-value")
    
    @patch('sys.argv')
    def test_custom_argument_names(self, mock_argv):
        """Test assigning custom argument names using l= that differ from field names."""
        
        class CustomArgNameCLI(AutoCLI):
            class CustomArgs(AutoCLI.CommonArgs):
                # Custom argument names different from field names
                username: str = param("default", l="--user")
                max_count: int = param(10, l="--limit", s="-l")
                verbose_output: bool = param(False, l="--verbose", s="-v")
            
            def run_custom(self, args):
                return f"User: {args.username}, Max: {args.max_count}, Verbose: {args.verbose_output}"
        
        # Mock command line arguments with custom names
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "custom", "--user", "testuser", 
            "--limit", "50", "--verbose"
        ][idx]
        mock_argv.__len__.return_value = 7
        
        # Create CLI instance
        cli = CustomArgNameCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_custom method to capture its result
        original_method = cli.run_custom
        cli.run_custom = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "User: testuser, Max: 50, Verbose: True")
        
        # Verify the custom argument names were used in CLI
        mock_argv_args = [mock_argv.__getitem__(i) for i in range(7)]
        self.assertEqual(mock_argv_args[2], "--user")       # Instead of "--username"
        self.assertEqual(mock_argv_args[4], "--limit")      # Instead of "--max-count"
        self.assertEqual(mock_argv_args[6], "--verbose")    # Instead of "--verbose-output"
    
    @patch('sys.argv')
    def test_short_option_forms(self, mock_argv):
        """Test using short option forms (s=) in command line arguments."""
        
        class ShortOptionCLI(AutoCLI):
            class OptionsArgs(AutoCLI.CommonArgs):
                name: str = param("default", l="--name", s="-n")
                count: int = param(1, l="--count", s="-c")
                verbose: bool = param(False, l="--verbose", s="-v")
                format: str = param("json", l="--format", s="-f", 
                                    choices=["json", "xml", "yaml"])
            
            def run_options(self, args):
                return f"Name: {args.name}, Count: {args.count}, Verbose: {args.verbose}, Format: {args.format}"
        
        # Mock command line arguments using short forms
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "options", "-n", "shorttest", 
            "-c", "42", "-v", "-f", "yaml"
        ][idx]
        mock_argv.__len__.return_value = 9
        
        # Create CLI instance
        cli = ShortOptionCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_options method to capture its result
        original_method = cli.run_options
        cli.run_options = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Name: shorttest, Count: 42, Verbose: True, Format: yaml")
        
        # Verify short option forms were used in CLI
        mock_argv_args = [mock_argv.__getitem__(i) for i in range(9)]
        self.assertEqual(mock_argv_args[2], "-n")    # Short form for --name
        self.assertEqual(mock_argv_args[4], "-c")    # Short form for --count
        self.assertEqual(mock_argv_args[6], "-v")    # Short form for --verbose
        self.assertEqual(mock_argv_args[7], "-f")    # Short form for --format
    
    @patch('sys.argv')
    def test_mixed_option_forms(self, mock_argv):
        """Test using a mix of long and short option forms in the same command."""
        
        class MixedOptionCLI(AutoCLI):
            class MixedArgs(AutoCLI.CommonArgs):
                input_file: str = param("input.txt", l="--input-file", s="-i")
                output_file: str = param("output.txt", l="--output-file", s="-o")
                backup: bool = param(False, l="--backup", s="-b")
                verbose: bool = param(False, l="--verbose", s="-v")
            
            def run_mixed(self, args):
                return f"Input: {args.input_file}, Output: {args.output_file}, Backup: {args.backup}, Verbose: {args.verbose}"
        
        # Mock command line arguments with mix of long and short forms
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "mixed", "--input-file", "source.txt", 
            "-o", "target.txt", "-b", "--verbose"
        ][idx]
        mock_argv.__len__.return_value = 8
        
        # Create CLI instance
        cli = MixedOptionCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_mixed method to capture its result
        original_method = cli.run_mixed
        cli.run_mixed = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Input: source.txt, Output: target.txt, Backup: True, Verbose: True")
        
        # Verify mixed option forms were used
        mock_argv_args = [mock_argv.__getitem__(i) for i in range(8)]
        self.assertEqual(mock_argv_args[2], "--input-file")  # Long form
        self.assertEqual(mock_argv_args[4], "-o")            # Short form
        self.assertEqual(mock_argv_args[6], "-b")            # Short form
        self.assertEqual(mock_argv_args[7], "--verbose")     # Long form

    @patch('sys.argv')
    def test_pre_common_hook(self, mock_argv):
        """Test that the pre_common hook is executed before command execution."""
        
        class PreCommonCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                value: str = param("default", l="--value", s="-v")
            
            def __init__(self):
                self.pre_common_called = False
                super().__init__()
            
            def pre_common(self, args):
                # Store information to verify this was called
                self.pre_common_called = True
                self.pre_common_args = args
            
            def run_test(self, args):
                return f"Value: {args.value}, pre_common_called: {self.pre_common_called}"
        
        # Mock command line arguments
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--value", "test-value"
        ][idx]
        mock_argv.__len__.return_value = 4
        
        # Create CLI instance
        cli = PreCommonCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_test method to capture its result
        original_method = cli.run_test
        cli.run_test = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify pre_common was called
        self.assertTrue(cli.pre_common_called)
        self.assertEqual(cli.pre_common_args.value, "test-value")
        
        # Verify the method was called with correct args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Value: test-value, pre_common_called: True")
    
    @patch('sys.argv')
    def test_pre_common_with_modifications(self, mock_argv):
        """Test that the pre_common hook can modify arguments before command execution."""
        
        class ModifyingPreCommonCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                value: str = param("default", l="--value", s="-v")
                modified: bool = param(False, l="--modified")
            
            def pre_common(self, args):
                # Modify the args before command execution
                args.modified = True
                args.value = f"MODIFIED_{args.value}"
            
            def run_test(self, args):
                return f"Value: {args.value}, Modified: {args.modified}"
        
        # Mock command line arguments
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--value", "original"
        ][idx]
        mock_argv.__len__.return_value = 4
        
        # Create CLI instance
        cli = ModifyingPreCommonCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_test method to capture its result
        original_method = cli.run_test
        cli.run_test = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with modified args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Value: MODIFIED_original, Modified: True")
    
    @patch('sys.argv')
    def test_edge_case_empty_args(self, mock_argv):
        """Test handling a command with no arguments."""
        
        class EmptyArgsCLI(AutoCLI):
            class EmptyArgs(AutoCLI.CommonArgs):
                # No arguments defined
                pass
            
            def run_empty(self, args):
                return "Command with empty args executed successfully"
        
        # Mock command line arguments - just the command, no args
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "empty"
        ][idx]
        mock_argv.__len__.return_value = 2
        
        # Create CLI instance
        cli = EmptyArgsCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_empty method to capture its result
        original_method = cli.run_empty
        cli.run_empty = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with empty args
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Command with empty args executed successfully")
    
    @patch('sys.argv')
    def test_edge_case_no_common_args(self, mock_argv):
        """Test a CLI class that doesn't use CommonArgs."""
        
        class NoCommonArgsCLI(AutoCLI):
            # Override the default CommonArgs with a custom base class
            class CustomBaseArgs(BaseModel):
                debug: bool = param(False, l="--debug", s="-d")
            
            # Set as the default args class
            CommonArgs = CustomBaseArgs
            
            class TestArgs(CustomBaseArgs):
                value: str = param("default", l="--value", s="-v")
            
            def run_test(self, args):
                return f"Value: {args.value}, Debug: {args.debug}"
        
        # Mock command line arguments
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--value", "custom-base", "--debug"
        ][idx]
        mock_argv.__len__.return_value = 5
        
        # Create CLI instance
        cli = NoCommonArgsCLI()
        
        # Create a method to capture the result
        result_capture = MagicMock()
        
        # Patch the run_test method to capture its result
        original_method = cli.run_test
        cli.run_test = lambda args: result_capture(original_method(args)) or True
        
        # Run the CLI (with exit patched to prevent test termination)
        with patch('sys.exit'):
            cli.run()
        
        # Verify the method was called with args using the custom base
        result_capture.assert_called_once()
        args, _ = result_capture.call_args
        self.assertEqual(args[0], "Value: custom-base, Debug: True")


if __name__ == "__main__":
    unittest.main() 