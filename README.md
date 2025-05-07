# pydantic-autocli

Automatically generate CLI applications from Pydantic models.

## Installation

```bash
pip install pydantic-autocli
```

## Features

- Automatically generate CLI commands from class methods
- Map Pydantic model fields to CLI arguments
- Customize CLI arguments with short/long forms and other options
- Automatically handle help text generation
- Support for common arguments across all commands
- Support for async commands
- Support for array arguments (list[str], list[int], list[float], etc.)

## Basic Usage

pydantic-autocli provides multiple ways to define CLI arguments and commands.

```python
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
    # Standard Pydantic notation
    class SimpleArgs(BaseModel):
        # Required parameter (no default value)
        required_value: int
        
        # Optional parameter (with default value)
        optional_value: int = 123
        
        # Array parameter
        names: list[str] = []
    
    # This method will automatically use SimpleArgs
    # Args class selection rule: run_simple -> SimpleArgs (by naming convention)
    def run_simple(self, args):
        """Execute simple command"""
        print(f"Required: {args.required_value}")
        print(f"Optional: {args.optional_value}")
        print(f"Names: {args.names}")
        return True  # Indicates success (exit code 0)
    
    # Notation using the param function
    class CommonArgs(AutoCLI.CommonArgs):
        # Common arguments for all commands
        verbose: bool = param(False, l="--verbose", s="-v", description="Enable detailed output")
    
    class AdvancedArgs(CommonArgs):
        # Specify short and long forms
        name: str = param(..., l="--name", s="-n")
        
        # Restrict choices
        mode: str = param("read", l="--mode", choices=["read", "write", "append"])
        
        # Array parameters (with type specification)
        input_paths: list[str] = param(..., l="--in", s="-i")
        numbers: list[int] = param([1, 2, 3], l="--nums")

    # This method will automatically use AdvancedArgs 
    # Args class selection rule: run_advanced -> AdvancedArgs (by naming convention)
    def run_advanced(self, args):
        """Execute advanced command"""
        print(f"Name: {args.name}, Mode: {args.mode}")
        print(f"Input paths: {args.input_paths}")
        print(f"Numbers: {args.numbers}")
        if args.verbose:
            print("Verbose mode enabled")
        return True  # Indicates success (exit code 0)
    
    # Example with multi-word command and parameters
    class ShowFileInfoArgs(CommonArgs):
        # Parameter names with underscores become kebab-case in CLI
        # file_path becomes --file-path in command line
        file_path: str = param(..., l="--file-path", s="-f")
        
        # show_lines becomes --show-lines in command line
        show_lines: bool = param(False, l="--show-lines")
        
        # line_count becomes --line-count in command line 
        line_count: int = param(10, l="--line-count")
    
    # Multi-word command: run_show_file_info becomes "show-file-info" command
    # Args selection rule: run_show_file_info -> ShowFileInfoArgs
    def run_show_file_info(self, args):
        """Show information about a file"""
        print(f"File: {args.file_path}")
        if args.show_lines:
            print(f"Showing {args.line_count} lines")
        return True  # Indicates success (exit code 0)
    
    # Example that returns failure
    class ErrorArgs(CommonArgs):
        code: int = param(1, l="--code", s="-c")
    
    # This method will automatically use ErrorArgs
    # Args class selection rule: run_error -> ErrorArgs (by naming convention)
    def run_error(self, args):
        """Example command that returns an error"""
        print(f"Simulating error with code {args.code}")
        return False  # Indicates failure (exit code 1)
        # Or return a specific exit code: return args.code

if __name__ == "__main__":
    cli = MyCLI()
    cli.run()
```

### Command-line execution examples

```bash
# Execute simple command
$ python mycli.py simple --required-value 42 --names Alice Bob Charlie
Required: 42
Optional: 123
Names: ['Alice', 'Bob', 'Charlie']

# Execute advanced command
$ python mycli.py advanced --name test --mode write --in file1.txt file2.txt --nums 5 10 15 -v
Name: test, Mode: write
Input paths: ['file1.txt', 'file2.txt']
Numbers: [5, 10, 15]
Verbose mode enabled

# Execute multi-word command (note the kebab-case)
# run_show_file_info method becomes show-file-info command
# Parameter names also use kebab-case (--file-path, --show-lines, --line-count)
$ python mycli.py show-file-info --file-path example.txt --show-lines --line-count 5
File: example.txt
Showing 5 lines

# Execute error command
$ python mycli.py error --code 42
Simulating error with code 42
# Exits with code 42
```

## Argument Resolution

### Using Naming Convention

You can specify argument classes for CLI commands using naming conventions:

```python
class MyCLI(AutoCLI):
    # Naming convention:
    # run_command → CommandArgs
    # run_foo_bar → FooBarArgs
    
    # Single-word command example
    class CommandArgs(AutoCLI.CommonArgs):
        name: str = param("default", l="--name", s="-n")
    
    def run_command(self, args):
        print(f"Name: {args.name}")
        return True  # Indicates success (exit code 0)
        
    # Two-word command example
    class FooBarArgs(AutoCLI.CommonArgs):
        option: str = param("default", l="--option")
    
    def run_foo_bar(self, args):
        print(f"Option: {args.option}")
        return True  # Indicates success (exit code 0)
```

Command-line execution examples:

```bash
$ python mycli.py command --name test
Name: test

$ python mycli.py foo-bar --option custom
Option: custom
```

### Using Type Annotations

You can directly specify the argument class using type annotations:

```python
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
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

### Resolution Priority

pydantic-autocli uses the following priority order to determine which argument class to use:

1. Type annotation on the method parameter
2. Naming convention (CommandArgs class for run_command method)
3. Fall back to CommonArgs

When both naming convention and type annotation could apply to a method, the type annotation takes precedence (as per the priority above). In such cases, a warning is displayed about the conflict:

```python
class MyCLI(AutoCLI):
    # Args class that follows naming convention
    class CommandArgs(BaseModel):
        name: str = param("default", l="--name")
    
    # Different args class specified by type annotation
    class CustomArgs(BaseModel):
        value: int = param(42, l="--value")
    
    # Type annotation takes precedence over naming convention
    # A warning will be displayed about the conflict
    def run_command(self, args: CustomArgs):
        # Uses CustomArgs even though CommandArgs exists
        print(f"Value: {args.value}")
        return True
```

This command will use `CustomArgs` (from type annotation) instead of `CommandArgs` (from naming convention), with a warning about the detected conflict. It's generally recommended to avoid such conflicts for code clarity.

## Common Arguments Base Class

`AutoCLI.CommonArgs` is a class that inherits from Pydantic's `BaseModel`. This means you can use it interchangeably with `BaseModel` while getting the benefits of common arguments across commands.

## Development and Testing

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Or using taskipy
uv run task test
```

## Examples

To run the example CLI:

```bash
python examples/example.py greet --verbose

# Or using taskipy
uv run task example file --file README.md
```

## License

See LICENSE file.
