#!/usr/bin/env python3
"""
Direct test script for type annotations without unittest.
"""

from pydantic import BaseModel, Field
from pydantic_autocli import AutoCLI

def test_type_annotations():
    print("\n=== Testing Type Annotations ===")
    
    class TestCLI(AutoCLI):
        class CustomArgs(BaseModel):
            value: int = Field(42, json_schema_extra={"l": "--value", "s": "-v"})
        
        def run_test(self, args: CustomArgs):
            print(f"Value: {args.value}")
            return args.value
    
    # Create an instance
    cli = TestCLI()
    
    # Check if the type annotation was detected correctly
    if "test" in cli.method_args_mapping:
        cls = cli.method_args_mapping["test"]
        print(f"Method 'run_test' mapped to: {cls.__name__}")
        if cls.__name__ == "CustomArgs":
            print("✅ Correct type annotation detected!")
        else:
            print(f"❌ Wrong class detected. Expected: CustomArgs, Got: {cls.__name__}")
    else:
        print("❌ Method 'run_test' not found in mapping")

def test_user_pattern():
    print("\n=== Testing User Pattern ===")
    
    class UserCLI(AutoCLI):
        class BarArgs(BaseModel):
            a: int = Field(123, json_schema_extra={"l": "--a", "s": "-a"})
        
        def run_foo(self, a: BarArgs):
            print(f"a = {a.a}")
            return a.a
    
    # Create an instance
    cli = UserCLI()
    
    # Check if the type annotation was detected correctly
    if "foo" in cli.method_args_mapping:
        cls = cli.method_args_mapping["foo"]
        print(f"Method 'run_foo' mapped to: {cls.__name__}")
        if cls.__name__ == "BarArgs":
            print("✅ Correct type annotation detected!")
        else:
            print(f"❌ Wrong class detected. Expected: BarArgs, Got: {cls.__name__}")
    else:
        print("❌ Method 'run_foo' not found in mapping")

if __name__ == "__main__":
    test_type_annotations()
    test_user_pattern() 