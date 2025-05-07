#!/usr/bin/env python3
"""
Comprehensive test suite for pydantic-autocli.
"""

import unittest
from pydantic import BaseModel, Field
from pydantic_autocli import BaseCLI


class BasicFunctionalityTest(unittest.TestCase):
    """Test basic functionality of BaseCLI."""
    
    def test_basic_cli(self):
        """Test basic CLI functionality with a simple command."""
        
        class TestCLI(BaseCLI):
            class GreetArgs(BaseCLI.CommonArgs):
                name: str = Field("World", l="--name", s="-n")
                count: int = Field(1, l="--count", s="-c")
            
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
        
        class AnnotationCLI(BaseCLI):
            # Define a model to use with annotations
            class CustomArgs(BaseModel):
                value: int = Field(42, l="--value", s="-v")
                flag: bool = Field(False, l="--flag", s="-f")
            
            # Method using type annotation directly
            def run_annotated(self, args: CustomArgs):
                if args.flag:
                    return args.value * 2
                return args.value
            
            # Traditional method using naming convention
            class TraditionalArgs(BaseCLI.CommonArgs):
                name: str = Field("default", l="--name", s="-n")
            
            def run_traditional(self, args):
                return args.name
        
        cli = AnnotationCLI()
        
        # Verify class mapping
        self.assertEqual(cli.method_args_mapping["annotated"].__name__, "CustomArgs")
        self.assertEqual(cli.method_args_mapping["traditional"].__name__, "TraditionalArgs")
        
        # Test annotated method
        args = AnnotationCLI.CustomArgs(value=100, flag=True)
        result = cli.run_annotated(args)
        self.assertEqual(result, 200)  # 100 * 2
        
        # Test traditional method
        args = AnnotationCLI.TraditionalArgs(name="Test Name")
        result = cli.run_traditional(args)
        self.assertEqual(result, "Test Name")


class UserPatternTest(unittest.TestCase):
    """Test the specific pattern requested by the user."""
    
    def test_user_pattern(self):
        """Test CLI using the pattern specified by the user."""
        
        class UserCLI(BaseCLI):
            class BarArgs(BaseModel):
                a: int = Field(123, l="--a", s="-a")
            
            def run_foo(self, a: BarArgs):
                return a.a
        
        cli = UserCLI()
        # Verify that run_foo uses BarArgs
        self.assertEqual(cli.method_args_mapping["foo"].__name__, "BarArgs")
        
        # Call with default value
        args = UserCLI.BarArgs()
        result = cli.run_foo(args)
        self.assertEqual(result, 123)  # Default value
        
        # Call with custom value
        args = UserCLI.BarArgs(a=456)
        result = cli.run_foo(args)
        self.assertEqual(result, 456)


class FallbackTest(unittest.TestCase):
    """Test fallback to CommonArgs."""
    
    def test_fallback(self):
        """Test that methods with no specific args class fall back to CommonArgs."""
        
        class FallbackCLI(BaseCLI):
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