#!/usr/bin/env python3
"""
A simple CLI example using pydantic-autocli.
"""

from pydantic import BaseModel, Field
from pydantic_autocli import BaseCLI, field

class SimpleCLI(BaseCLI):
    class CommonArgs(BaseCLI.CommonArgs):
        # Common arguments for all commands
        verbose: bool = Field(False, description="Enable verbose output")

    class GreetArgs(CommonArgs):
        # Arguments specific to 'greet' command
        name: str = field("World", "--name", "-n")
        count: int = field(1, "--count", "-c")

    def run_greet(self, args):
        """Run the greet command"""
        for _ in range(args.count):
            print(f"Hello, {args.name}!")
        
        if args.verbose:
            print(f"Greeted {args.name} {args.count} times")

    class FileArgs(CommonArgs):
        # Arguments specific to 'file' command
        filename: str = field(..., "--file", "-f")
        write_mode: bool = field(False, "--write", "-w")

    def run_file(self, args):
        """Run the file command"""
        if args.write_mode:
            with open(args.filename, 'w') as f:
                f.write("Hello from pydantic-autocli!\n")
            print(f"Wrote to file: {args.filename}")
        else:
            try:
                with open(args.filename, 'r') as f:
                    content = f.read()
                print(f"File content: {content.strip()}")
            except FileNotFoundError:
                print(f"File not found: {args.filename}")
        
        if args.verbose:
            print(f"File operation complete on {args.filename}")

if __name__ == "__main__":
    cli = SimpleCLI()
    cli.run() 