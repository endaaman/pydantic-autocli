# pydantic-autocli

Automatically generate CLI applications from Pydantic models.

## Installation

```bash
pip install pydantic-autocli
```

## Usage

```python
from pydantic import BaseModel, Field
from pydantic_autocli import BaseCLI

class MyCLI(BaseCLI):
    class CommonArgs(BaseCLI.CommonArgs):
        # Common arguments for all commands
        verbose: bool = Field(False, description="Enable verbose output")

    class FooArgs(CommonArgs):
        # Arguments specific to 'foo' command
        name: str = Field(..., l="--name", s="-n")
        count: int = Field(1, l="--count", s="-c")

    def run_foo(self, args):
        """Run the foo command"""
        print(f"Running foo with name={args.name}, count={args.count}")
        if args.verbose:
            print("Verbose mode enabled")

    class BarArgs(CommonArgs):
        # Arguments specific to 'bar' command
        file: str = Field(..., l="--file", s="-f")
        mode: str = Field("read", l="--mode", s="-m", choices=["read", "write", "append"])

    def run_bar(self, args):
        """Run the bar command"""
        print(f"Running bar with file={args.file}, mode={args.mode}")
        if args.verbose:
            print("Verbose mode enabled")

if __name__ == "__main__":
    cli = MyCLI()
    cli.run()
```

## Features

- Automatically generate CLI commands from class methods
- Map Pydantic model fields to CLI arguments
- Customize CLI arguments with extended Field options:
  - `l`: Long form argument (e.g., `l="--name"`)
  - `s`: Short form argument (e.g., `s="-n"`)
  - `choices`: List of allowed values (e.g., `choices=["read", "write", "append"]`)
- Automatically handle help text generation
- Support for common arguments across all commands
- Support for async commands

## Extended Field Parameters

The library extends Pydantic's Field with the following CLI-specific parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Long form CLI argument | `Field(..., l="--output-dir")` |
| `s` | Short form CLI argument | `Field(..., s="-o")` |
| `choices` | Allowed values for the argument | `Field("read", choices=["read", "write"])` |

## License

See LICENSE file.
