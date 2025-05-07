#!/usr/bin/env python3
"""
A simple CLI example using pydantic-autocli.
"""

from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param

class SimpleCLI(AutoCLI):
    class CommonArgs(AutoCLI.CommonArgs):
        # Common arguments for all commands
        verbose: bool = param(False, description="Enable verbose output")

    class GreetArgs(CommonArgs):
        # Arguments specific to 'greet' command
        name: str = param("World", l="--name", s="-n")
        count: int = param(1, l="--count", s="-c")

    def run_greet(self, args:GreetArgs):
        """Run the greet command"""
        for _ in range(args.count):
            print(f"Hello, {args.name}!")
        
        if args.verbose:
            print(f"Greeted {args.name} {args.count} times")

    class CustomArgs(CommonArgs):
        # Arguments specific to 'file' command
        filename: str = param(..., l="--file", s="-f")
        write_mode: bool = param(False, l="--write", s="-w")
        mode: str = param("text", l="--mode", s="-m", choices=["text", "binary", "append"])

    def run_file(self, args:CustomArgs):
        """Run the file command"""
        assert args.mode == "text"
        print(f"File: {args.filename}, Mode: {args.mode}, Write: {args.write_mode}")

if __name__ == "__main__":
    cli = SimpleCLI()
    cli.run() 