# pydantic-autocli

Automatically generate sub-command based CLI applications from Pydantic models.

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
    class CommonArgs(AutoCLI.CommonArgs):
        # Common arguments for all commands and act as a fallback
        verbose: bool = param(False, l="--verbose", s="-v", description="Enable detailed output")
        seed: int = 42

    # Executed commonly for all subcommands
    def pre_common(self, args:CommonArgs):
        print('Using seed: {args.seed}')
        
    # Standard Pydantic notation
    class SimpleArgs(CommonArgs):
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

    class CustomAdvancedArgs(CommonArgs):
        # file_name becomes --file-name in command line 
        file_name: str
        # Restrict choices
        mode: str = param("read", l="--mode", choices=["read", "write", "append"])
        wait: float = 0.5

    # This method will use CustomAdvancedArgs
    # Args class is explicitly specified (by type annotation)
    # This is an async method that can be awaited
    async def run_advanced(self, args:CustomAdvancedArgs):
        """Execute advanced command"""
        print(f"Mode: {args.mode}")
        print(f"Filenames: {args.file_names}")
        print(f"Numbers: {args.numbers}")

        import asyncio
        print(f"Awaiting for {args.wait}s..")
        await asyncio.sleep(args.wait)

        if args.verbose:
            print("Verbose mode enabled")
        if not os.path.exists(args.file_name):
            return False # Indicates error (exit code 1)
        return True  # Indicates success (exit code 0)

        # Also supports custom exit codes
        # return 423

if __name__ == "__main__":
    cli = MyCLI()
    cli.run()  # Uses sys.argv by default    
    # cli.run(sys.argv)  # Explicitly pass sys.argv

    # Pass custom arguments
    # cli.run(["program_name", "command", "--value", "value1", "--flag"])    
```


### Command-line execution examples

```bash
# Run simple command with required parameter
python your_script.py run-simple --required-value 42

# Run simple command with all parameters
python your_script.py run-simple --required-value 42 --optional-value 100 --names "John Jane"

# Run advanced command
python your_script.py run-advanced --file-name data.txt --mode write --wait 1.5 --verbose
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

This command will use `CustomArgs` (from type annotation) instead of `CommandArgs` (from naming convention), with a warning about the detected conflict.


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
