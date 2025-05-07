# pydantic-autocli

Automatically generate CLI applications from Pydantic models.

## Installation

```bash
pip install pydantic-autocli
```

## Usage

```python
from pydantic import BaseModel, Field
from pydantic_autocli import BaseCLI, field

class MyCLI(BaseCLI):
    class CommonArgs(BaseCLI.CommonArgs):
        # Common arguments for all commands
        verbose: bool = Field(False, description="Enable verbose output")

    class FooArgs(CommonArgs):
        # Arguments specific to 'foo' command
        name: str = field(..., "--name", "-n")
        count: int = field(1, "--count", "-c")

    def run_foo(self, args):
        """Run the foo command"""
        print(f"Running foo with name={args.name}, count={args.count}")
        if args.verbose:
            print("Verbose mode enabled")

    class BarArgs(CommonArgs):
        # Arguments specific to 'bar' command
        file: str = field(..., "--file", "-f")

    def run_bar(self, args):
        """Run the bar command"""
        print(f"Running bar with file={args.file}")
        if args.verbose:
            print("Verbose mode enabled")

if __name__ == "__main__":
    cli = MyCLI()
    cli.run()
```

## Features

- Automatically generate CLI commands from class methods
- Map Pydantic model fields to CLI arguments
- Support for short and long argument formats
- Automatically handle help text generation
- Support for common arguments across all commands
- Support for async commands

## License

See LICENSE file.
