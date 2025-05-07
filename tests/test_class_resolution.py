#!/usr/bin/env python3
"""
Tests focused on class resolution logic for pydantic-autocli.
Testing how argument classes are selected based on type annotations and naming conventions.
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
logger = logging.getLogger("test_class_resolution")


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


class NamingConventionTest(unittest.TestCase):
    """Test naming convention based class resolution."""
    
    def test_naming_convention(self):
        """Test that naming convention correctly resolves argument classes."""
        
        class NamingCLI(AutoCLI):
            # Single-word command
            class CommandArgs(AutoCLI.CommonArgs):
                name: str = param("default", l="--name", s="-n")
            
            def run_command(self, a):
                return f"Command: {a.name}"
            
            # Two-word command
            class FooBarArgs(AutoCLI.CommonArgs):
                option: str = param("default", l="--option")
            
            def run_foo_bar(self, a):
                return f"FooBar: {a.option}"
        
        cli = NamingCLI()
        
        # Check class resolution by naming convention
        self.assertEqual(cli.method_args_mapping["command"].__name__, "CommandArgs")
        self.assertEqual(cli.method_args_mapping["foo_bar"].__name__, "FooBarArgs")


class ConflictResolutionTest(unittest.TestCase):
    """Test resolution when both naming convention and type annotation could apply."""
    
    def test_conflict_resolution(self):
        """Test that type annotation takes precedence over naming convention."""
        
        autocli_logger = logging.getLogger("pydantic_autocli")
        original_level = autocli_logger.level
        autocli_logger.setLevel(logging.DEBUG)
        
        try:
            class ConflictCLI(AutoCLI):
                # Args class that follows naming convention
                class CommandArgs(BaseModel):
                    name: str = param("default", l="--name")
                
                # Different args class specified by type annotation
                class CustomArgs(BaseModel):
                    value: int = param(42, l="--value")
                
                # Type annotation should take precedence over naming convention
                def run_command(self, a: CustomArgs):
                    return f"Value: {a.value}"
            
            cli = ConflictCLI()
            
            # Type annotation should win over naming convention
            self.assertEqual(cli.method_args_mapping["command"].__name__, "CustomArgs")
        finally:
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


if __name__ == "__main__":
    unittest.main() 