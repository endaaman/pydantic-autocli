# pydantic-autocli

Automatically generate CLI applications from Pydantic models.

## Installation

```bash
# Using pip
pip install pydantic-autocli

# Using uv
uv pip install pydantic-autocli
```

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Or using taskipy
uv run task test
```

## Usage

```python
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
    class CommonArgs(AutoCLI.CommonArgs):
        # Common arguments for all commands
        verbose: bool = param(False, description="Enable verbose output")

    class FooArgs(CommonArgs):
        # Arguments specific to 'foo' command
        name: str = param(..., l="--name", s="-n")
        count: int = param(1, l="--count", s="-c")

    def run_foo(self, args):
        """Run the foo command"""
        print(f"Running foo with name={args.name}, count={args.count}")
        if args.verbose:
            print("Verbose mode enabled")

    class BarArgs(CommonArgs):
        # Arguments specific to 'bar' command
        file: str = param(..., l="--file", s="-f")
        mode: str = param("read", l="--mode", s="-m", choices=["read", "write", "append"])

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
- Customize CLI arguments with the `param` function:
  - `l`: Long form argument (e.g., `l="--name"`)
  - `s`: Short form argument (e.g., `s="-n"`)
  - `choices`: List of allowed values (e.g., `choices=["read", "write", "append"]`)
- Automatically handle help text generation
- Support for common arguments across all commands
- Support for async commands

## The `param` Function

The library provides a `param` function to create CLI arguments in a more concise way:

```python
from pydantic_autocli import param

# Basic usage
name: str = param(..., l="--name", s="-n")

# With default value
count: int = param(1, l="--count", s="-c")

# With choices
mode: str = param("read", l="--mode", s="-m", choices=["read", "write", "append"])

# With additional Field parameters
verbose: bool = param(False, description="Enable verbose output")
```

Note that `param` is just a convenience function that internally uses Pydantic's `Field`. You can also use `Field` directly if you prefer:

```python
from pydantic import BaseModel, Field

class MyArgs(BaseModel):
    # Using param (recommended)
    name1: str = param("default", l="--name1", s="-n1")
    
    # Using Field directly
    name2: str = Field("default", json_schema_extra={"l": "--name2", "s": "-n2"})
```

Both approaches are valid and will work the same way. The `param` function is provided to make the code more readable and maintainable.

## Type Annotation Support

pydantic-autocli now supports two ways to define CLI argument classes:

### 1. Using Type Annotations

You can directly specify the argument class using type annotations:

```python
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
    # Define a model to use with annotations
    class CustomArgs(BaseModel):
        value: int = param(42, l="--value", s="-v")
        flag: bool = param(False, l="--flag", s="-f")
    
    # Use type annotation to specify args class
    def run_command(self, args: CustomArgs):
        print(f"Value: {args.value}")
        if args.flag:
            print("Flag is set")
        return True
```

### 2. Using Naming Convention (Traditional)

The traditional naming convention continues to work:

```python
class MyCLI(AutoCLI):
    # Args class named after command (CommandArgs)
    class CommandArgs(AutoCLI.CommonArgs):
        name: str = param("default", l="--name", s="-n")
    
    def run_command(self, args):
        print(f"Name: {args.name}")
        return True
```

### Resolution Priority

pydantic-autocli uses the following priority order to determine which argument class to use:

1. Type annotation on the method parameter
2. Naming convention (CommandArgs class for run_command method)
3. Fall back to CommonArgs

## Testing

To run the tests:

```bash
# Install development dependencies and run tests
uv sync
uv run pytest

# Or using taskipy
uv run task test
```

## Examples

To run the example CLI:

```bash
# Run the example directly
python examples/simple.py

# Or using taskipy
uv run task example
```

## License

See LICENSE file.
