#!/usr/bin/env python3
"""
Simple test script to verify pydantic-autocli works.
Run using: python test_cli.py greet -n "Test User" -c 2 --verbose
"""

from pydantic import BaseModel, Field
from pydantic_autocli import BaseCLI

class TestCLI(BaseCLI):
    class GreetArgs(BaseCLI.CommonArgs):
        name: str = Field("World", l="--name", s="-n")
        count: int = Field(1, l="--count", s="-c")
        verbose: bool = Field(False, l="--verbose")

    def run_greet(self, args):
        for _ in range(args.count):
            print(f"Hello, {args.name}!")
        
        if args.verbose:
            print(f"Verbose: Greeted {args.name} {args.count} times")
        
        return True

if __name__ == "__main__":
    cli = TestCLI()
    cli.run()