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
            
            def run_greet(self, args):
                return f"Hello, {args.name}!"
        
        cli = TestCLI()
        # Directly call the method with args
        args = TestCLI.GreetArgs(name="Test User")
        result = cli.run_greet(args)
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
            def run_annotated(self, args: CustomArgs):
                if args.flag:
                    return args.value * 2
                return args.value
            
            # Traditional method using naming convention
            class TraditionalArgs(AutoCLI.CommonArgs):
                name: str = param("default", l="--name", s="-n")
            
            def run_traditional(self, args):
                return args.name
        
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
                def run_good(self, args: TestArgsClass):
                    """Method with standard parameter name"""
                    return args.value
                
                # Method with parameter named 'a' - this will not resolve correctly
                def run_bad(self, a: TestArgsClass):
                    """Method with non-standard parameter name"""
                    return a.value
            
            # Create CLI instance
            cli = BugDemoCLI()
            
            # Print debug info
            logger.debug("Method args mapping after initialization:")
            for name, cls in cli.method_args_mapping.items():
                logger.debug(f"  {name}: {cls.__name__}")
            
            # Manually check what the type annotation method returns
            annotation_good = cli._get_type_annotation_for_method("run_good")
            annotation_bad = cli._get_type_annotation_for_method("run_bad")
            
            logger.debug(f"Type annotation for run_good: {annotation_good}")
            logger.debug(f"Type annotation for run_bad: {annotation_bad}")
            
            # Look at the signature of methods
            good_params = inspect.signature(BugDemoCLI.run_good).parameters
            bad_params = inspect.signature(BugDemoCLI.run_bad).parameters
            
            logger.debug("Parameters of run_good:")
            for name, param in good_params.items():
                logger.debug(f"  {name}: {param.annotation}")
            
            logger.debug("Parameters of run_bad:")
            for name, param in bad_params.items():
                logger.debug(f"  {name}: {param.annotation}")
            
            # This should pass - parameter named 'args' should be correctly resolved
            if annotation_good == TestArgsClass:
                self.assertEqual(cli.method_args_mapping["good"].__name__, "TestArgsClass", 
                                "Method with parameter named 'args' should resolve to TestArgsClass")
            
            # This should fail due to the bug - parameter named 'a' doesn't get resolved
            if annotation_bad == TestArgsClass:
                self.assertEqual(cli.method_args_mapping["bad"].__name__, "TestArgsClass",
                                "Method with parameter named 'a' should also resolve to TestArgsClass")
            else:
                # If the annotation isn't being detected at all, validate our assumption
                self.assertEqual(cli.method_args_mapping["bad"].__name__, "CommonArgs",
                               "Method with parameter named 'a' is incorrectly resolving to CommonArgs")
                
                # Now manually verify that the annotation exists but isn't being detected
                type_hints = get_type_hints(BugDemoCLI.run_bad)
                logger.debug(f"Type hints for run_bad: {type_hints}")
                
                if 'a' in type_hints and type_hints['a'] == TestArgsClass:
                    # Confirm that this is a bug - the type hint exists but isn't being used
                    logger.debug("BUG CONFIRMED: Type hint for 'a' parameter exists but isn't being used")
            
            # Examine the _get_type_annotation_for_method implementation
            source = inspect.getsource(AutoCLI._get_type_annotation_for_method)
            logger.debug(f"Source of _get_type_annotation_for_method: {source}")
            
        finally:
            # Restore original logging level
            autocli_logger.setLevel(original_level)


class FallbackTest(unittest.TestCase):
    """Test fallback to CommonArgs."""
    
    def test_fallback(self):
        """Test that methods with no specific args class fall back to CommonArgs."""
        
        class FallbackCLI(AutoCLI):
            def run_fallback(self, args):
                return "fallback"
        
        cli = FallbackCLI()
        # Verify that run_fallback uses CommonArgs
        self.assertEqual(cli.method_args_mapping["fallback"].__name__, "CommonArgs")
        
        # Call the method
        args = FallbackCLI.CommonArgs()
        result = cli.run_fallback(args)
        self.assertEqual(result, "fallback")


if __name__ == "__main__":
    unittest.main() 