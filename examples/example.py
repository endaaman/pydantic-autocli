"""
A simple CLI example using pydantic-autocli.
"""

import os
from pydantic_autocli import AutoCLI, param

class SimpleCLI(AutoCLI):
    class CommonArgs(AutoCLI.CommonArgs):
        # Common arguments for all commands
        quiet: bool = param(False, s='-q', description="Set verbosity of output")

    def prepare(self, a:CommonArgs):
        """Common initialization for all commands"""
        if a.quiet:
            self.quiet = a.quiet
            print("[DEBUG] Verbose mode disabled")

    class GreetArgs(CommonArgs):
        # Arguments specific to 'greet' command
        name: str = param("World", l="--name", s="-n", pattern=r"^[a-zA-Z]+$")
        count: int = param(1, l="--count", s="-c")

    def run_greet(self, a:GreetArgs):
        """Greet someone with a customizable message"""
        print(type(a))
        for _ in range(a.count):
            print(f"Hello, {a.name}!")

        if not a.quiet:
            print(f"Greeted {a.name} {a.count} times")

    class CustomArgs(CommonArgs):
        # Arguments specific to 'file' command
        filename: str = param(..., l="--file", s="-f")
        write_mode: bool = param(False, l="--write", s="-w")
        mode: str = param("text", l="--mode", s="-m", choices=["text", "binary", "append"])
        hi: bool = param(False, s="-h")

    def run_file(self, a:CustomArgs):
        """Process a file with various modes and options"""
        print(type(a))
        print(f"File: {a.filename}, Mode: {a.mode}, Write: {a.write_mode}")
        if os.path.exists(a.filename):
            print('File found:', a.filename)
            # return 0
            return  # empty return returns code:0
        else:
            print('File not found:', a.filename)
            return 1

if __name__ == "__main__":
    cli = SimpleCLI()
    cli.run()
