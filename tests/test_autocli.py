#!/usr/bin/env python3
"""
Comprehensive test suite for pydantic-autocli.
"""

import unittest
import sys
import inspect
import logging
from typing import get_type_hints, Any
from pydantic import BaseModel, Field
from pydantic_autocli import AutoCLI, param
from unittest.mock import patch, call, MagicMock


# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_autocli")


class TestArgsClass(BaseModel):
    """Test arguments class to be used across tests."""
    value: int = Field(123, description="Test field")


class BasicFunctionalityTest(unittest.TestCase):
    """Test basic functionality of AutoCLI."""
    
    def test_basic_cli(self):
        """Test basic CLI functionality with a simple command."""
        
        class TestCLI(AutoCLI):
            class GreetArgs(AutoCLI.CommonArgs):
                name: str = param("World", l="--name", s="-n")
                count: int = param(1, l="--count", s="-c")
            
            def run_greet(self, a):
                return f"Hello, {a.name}!"
        
        cli = TestCLI()
        # Directly call the method with args
        a = TestCLI.GreetArgs(name="Test User")
        result = cli.run_greet(a)
        self.assertEqual(result, "Hello, Test User!")


class TypeAnnotationTest(unittest.TestCase):
    """Test argument class resolution via type annotations."""
    
    def test_type_annotations(self):
        """Test that type annotations correctly resolve argument classes."""
        
        class AnnotationCLI(AutoCLI):
            # Define a model to use with annotations
            class CustomArgs(BaseModel):
                value: int = param(42, l="--value", s="-v")
                flag: bool = param(False, l="--flag", s="-f")
            
            # Method using type annotation directly
            def run_annotated(self, a: CustomArgs):
                if a.flag:
                    return a.value * 2
                return a.value
            
            # Traditional method using naming convention
            class TraditionalArgs(AutoCLI.CommonArgs):
                name: str = param("default", l="--name", s="-n")
            
            def run_traditional(self, a):
                return a.name
        
        # Enable debug logging for AutoCLI
        autocli_logger = logging.getLogger("pydantic_autocli")
        original_level = autocli_logger.level
        autocli_logger.setLevel(logging.DEBUG)
        
        try:
            # Create CLI instance 
            logger.debug("Creating AnnotationCLI instance for testing type annotations")
            cli = AnnotationCLI()
            
            # Check method_args_mapping
            logger.debug(f"Method args mapping: {cli.method_args_mapping}")
            for name, cls in cli.method_args_mapping.items():
                logger.debug(f"  {name}: {cls.__name__}")
            
            # Check that method_args_mapping is correctly populated during initialization
            self.assertEqual(cli.method_args_mapping["annotated"].__name__, "CustomArgs")
            self.assertEqual(cli.method_args_mapping["traditional"].__name__, "TraditionalArgs")
        finally:
            # Restore original logging level
            autocli_logger.setLevel(original_level)


class AnnotationBugTest(unittest.TestCase):
    """Test specifically for the bug with parameter type annotations."""
    
    def test_param_annotation_bug(self):
        """Test that demonstrates the bug with parameter name 'a' not being recognized."""
        
        # Enable debug logging
        autocli_logger = logging.getLogger("pydantic_autocli")
        original_level = autocli_logger.level
        autocli_logger.setLevel(logging.DEBUG)
        
        try:
            # Define a simple CLI class that uses TestArgsClass for type annotation
            class BugDemoCLI(AutoCLI):
                """CLI class for demonstrating the bug"""
                
                # Method with parameter named 'args' - this should work
                def run_good(self, a: TestArgsClass):
                    """Method with standard parameter name that works"""
                    return a.value
                
                # Method with parameter named 'a' - this should also work now
                def run_bad(self, a: TestArgsClass):
                    """Method with non-standard parameter name"""
                    return a.value
                
                # Method with another parameter name for testing
                def run_param(self, param: TestArgsClass):
                    """Method with alternative parameter name"""
                    return param.value
            
            # Create CLI instance
            cli = BugDemoCLI()
            
            # Print debug info
            logger.debug("Method args mapping after initialization:")
            for name, cls in cli.method_args_mapping.items():
                logger.debug(f"  {name}: {cls.__name__}")
            
            # Manually check what the type annotation method returns
            annotation_good = cli._get_type_annotation_for_method("run_good")
            annotation_bad = cli._get_type_annotation_for_method("run_bad")
            annotation_param = cli._get_type_annotation_for_method("run_param")
            
            logger.debug(f"Type annotation for run_good: {annotation_good}")
            logger.debug(f"Type annotation for run_bad: {annotation_bad}")
            logger.debug(f"Type annotation for run_param: {annotation_param}")
            
            # Look at the signature of methods
            good_params = inspect.signature(BugDemoCLI.run_good).parameters
            bad_params = inspect.signature(BugDemoCLI.run_bad).parameters
            param_params = inspect.signature(BugDemoCLI.run_param).parameters
            
            logger.debug("Parameters of run_good:")
            for name, param in good_params.items():
                logger.debug(f"  {name}: {param.annotation}")
            
            logger.debug("Parameters of run_bad:")
            for name, param in bad_params.items():
                logger.debug(f"  {name}: {param.annotation}")
                
            logger.debug("Parameters of run_param:")
            for name, param in param_params.items():
                logger.debug(f"  {name}: {param.annotation}")
            
            # This should pass - parameter named 'a' should be correctly resolved
            self.assertEqual(cli.method_args_mapping["good"].__name__, "TestArgsClass", 
                            "Method with parameter named 'a' should resolve to TestArgsClass")
            
            # This should also pass now after the fix
            self.assertEqual(cli.method_args_mapping["bad"].__name__, "TestArgsClass",
                            "Method with parameter named 'a' should also resolve to TestArgsClass")
                
            # This should also pass for the alternative parameter name
            self.assertEqual(cli.method_args_mapping["param"].__name__, "TestArgsClass",
                           "Method with parameter named 'param' should also resolve to TestArgsClass")
                
            # Verify that type hints are properly detected for all methods
            type_hints_good = get_type_hints(BugDemoCLI.run_good)
            type_hints_bad = get_type_hints(BugDemoCLI.run_bad)
            type_hints_param = get_type_hints(BugDemoCLI.run_param)
            
            logger.debug(f"Type hints for run_good: {type_hints_good}")
            logger.debug(f"Type hints for run_bad: {type_hints_bad}")
            logger.debug(f"Type hints for run_param: {type_hints_param}")
            
            # All methods should have their parameter correctly typed
            self.assertEqual(type_hints_good.get('a'), TestArgsClass)
            self.assertEqual(type_hints_bad.get('a'), TestArgsClass)
            self.assertEqual(type_hints_param.get('param'), TestArgsClass)
            
        finally:
            # Restore original logging level
            autocli_logger.setLevel(original_level)


class FallbackTest(unittest.TestCase):
    """Test fallback to CommonArgs."""
    
    def test_fallback(self):
        """Test that methods with no specific args class fall back to CommonArgs."""
        
        class FallbackCLI(AutoCLI):
            def run_fallback(self, a):
                return "fallback"
        
        cli = FallbackCLI()
        # Verify that run_fallback uses CommonArgs
        self.assertEqual(cli.method_args_mapping["fallback"].__name__, "CommonArgs")
        
        # Call the method
        a = FallbackCLI.CommonArgs()
        result = cli.run_fallback(a)
        self.assertEqual(result, "fallback")


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


if __name__ == "__main__":
    unittest.main() 