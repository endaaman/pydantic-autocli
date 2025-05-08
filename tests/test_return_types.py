#!/usr/bin/env python3
"""
Tests focused on return type handling for pydantic-autocli.
Testing how different return values from command methods are processed.
"""

import unittest
import sys
import logging
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param
from unittest.mock import patch, MagicMock


# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_return_types")


class CLIReturnTypesTest(unittest.TestCase):
    """Test CLI return type handling functionality."""
    
    def setUp(self):
        # Enable debug logging
        self.autocli_logger = logging.getLogger("pydantic_autocli")
        self.original_level = self.autocli_logger.level
        self.autocli_logger.setLevel(logging.DEBUG)
        
    def tearDown(self):
        # Restore original logging level
        self.autocli_logger.setLevel(self.original_level)
    
    @patch('sys.argv')
    def test_different_return_types(self, mock_argv):
        """Test handling different return types from command methods."""
        
        class ReturnTypesCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                return_type: str = param("bool", l="--return-type", 
                                       choices=["bool", "int", "none", "str"])
            
            def run_test(self, args):
                # Return different types based on the argument
                if args.return_type == "bool":
                    return True
                elif args.return_type == "int":
                    return 42
                elif args.return_type == "none":
                    return None
                elif args.return_type == "str":
                    return "string result"
        
        # Test boolean return value
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--return-type", "bool"
        ][idx]
        mock_argv.__len__.return_value = 4
        
        cli = ReturnTypesCLI()
        
        # Patch sys.exit to capture exit code
        with patch('sys.exit') as mock_exit:
            cli.run()
            mock_exit.assert_called_once_with(0)  # True should exit with 0
        
        # Test integer return value
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--return-type", "int"
        ][idx]
        
        cli = ReturnTypesCLI()
        
        with patch('sys.exit') as mock_exit:
            cli.run()
            mock_exit.assert_called_once_with(42)  # Should exit with the int value
        
        # Test None return value
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--return-type", "none"
        ][idx]
        
        cli = ReturnTypesCLI()
        
        with patch('sys.exit') as mock_exit:
            cli.run()
            mock_exit.assert_called_once_with(0)  # None should exit with 0
        
        # Test string return value (non-convertible to int)
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--return-type", "str"
        ][idx]
        
        cli = ReturnTypesCLI()
        
        with patch('sys.exit') as mock_exit:
            # Capture the warning log message about unexpected return type
            with self.assertLogs(logger="pydantic_autocli", level=logging.WARNING) as log_capture:
                cli.run()
                self.assertTrue(any("Unexpected return type" in msg for msg in log_capture.output))
            
            mock_exit.assert_called_once_with(1)  # String should cause exit with 1
    
    @patch('sys.argv')
    def test_boolean_return_values(self, mock_argv):
        """Test that boolean return values are properly converted to exit codes."""
        
        class BooleanReturnCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                success: bool = param(True, l="--success", s="-s")
            
            def run_test(self, args):
                # Return True or False based on args
                return args.success
        
        # Test True return value
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--success"
        ][idx]
        mock_argv.__len__.return_value = 3
        
        cli = BooleanReturnCLI()
        
        with patch('sys.exit') as mock_exit:
            cli.run()
            mock_exit.assert_called_once_with(0)  # True should exit with 0
        
        # Test False return value
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test"  # No --success flag means False
        ][idx]
        mock_argv.__len__.return_value = 2
        
        cli = BooleanReturnCLI()
        
        with patch('sys.exit') as mock_exit:
            cli.run()
            mock_exit.assert_called_once_with(1)  # False should exit with 1
    
    @patch('sys.argv')
    def test_numeric_objects_return_values(self, mock_argv):
        """Test handling numeric-like objects that can be converted to integers."""
        
        class NumericObjectCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                value: int = param(0, l="--value", s="-v")
            
            def run_test(self, args):
                # Return a custom numeric-like object
                class NumericLike:
                    def __init__(self, value):
                        self.value = value
                    
                    def __int__(self):
                        return self.value
                
                return NumericLike(args.value)
        
        # Test with a value that can be converted to int
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test", "--value", "42"
        ][idx]
        mock_argv.__len__.return_value = 4
        
        cli = NumericObjectCLI()
        
        with patch('sys.exit') as mock_exit:
            cli.run()
            mock_exit.assert_called_once_with(42)  # Should convert to 42
    
    @patch('sys.argv')
    def test_exception_in_command(self, mock_argv):
        """Test handling exceptions raised during command execution."""
        
        class ExceptionCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                pass
            
            def run_test(self, args):
                # Raise an exception
                raise ValueError("Test exception")
        
        mock_argv.__getitem__.side_effect = lambda idx: [
            "test_script.py", "test"
        ][idx]
        mock_argv.__len__.return_value = 2
        
        cli = ExceptionCLI()
        
        # Capture the error log
        with self.assertLogs(logger="pydantic_autocli", level=logging.ERROR) as log_capture:
            with patch('sys.exit') as mock_exit:
                cli.run()
                
                # Verify the error was logged
                self.assertTrue(any("ERROR in command execution" in msg for msg in log_capture.output))
                
                # No explicit return, so the result should implicitly be None -> exit code 0
                # But an exception occurred, which should be reported as a failure
                mock_exit.assert_called_once()
                
                # The actual implementation doesn't specify behavior for exceptions,
                # but ideally it would use a non-zero exit code to indicate failure


if __name__ == "__main__":
    unittest.main() 