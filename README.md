# pydantic-autocli

[![CI](https://github.com/endaaman/pydantic-autocli/workflows/CI/badge.svg)](https://github.com/endaaman/pydantic-autocli/actions)
[![codecov](https://codecov.io/gh/endaaman/pydantic-autocli/branch/master/graph/badge.svg)](https://codecov.io/gh/endaaman/pydantic-autocli)

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

```python:cli.py
from pydantic import BaseModel
from pydantic_autocli import AutoCLI

class MyCLI(AutoCLI):
    # Standard Pydantic notation
    class CustomArgs(BaseModel):
        # Required parameter (no default value)
        required_value: int
        # Optional parameter (with default value)
        optional_value: int = 123
        # Array parameter
        names: list[str] = []
        
    # This will be triggered by `python xxx.py simple` command
    # Args class is explicitly specified (by type annotation)
    def run_simple(self, args:CustomArgs):
        print(f"Required: {args.required_value}")
        print(f"Optional: {args.optional_value}")
        print(f"Names: {args.names}")

if __name__ == "__main__":
    cli = MyCLI()
    cli.run()
```

pydantic-autocli uses standard `argparse` under the hood, so command-line arguments follow familiar patterns:

```bash
# Run simple command with required parameter
python your_script.py simple --required-value 42 --optional-value 100 

# Run simple command with all parameters (multiple ways to specify arrays)
python your_script.py simple --required-value 42 --names John --names Jane

# Array values can also be provided as space-delimited in a single argument
python your_script.py simple --required-value 42 --names John Jane Bob
```


## advanced Usage


```python
from pydantic import Field
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
    # Common arguments for all commands and act as a fallback
    class CommonArgs(AutoCLI.CommonArgs):
        # `param` `param()` is syntax sugar for `Field()`
        verbose: bool = param(False, l="--verbose", s="-v", description="Enable detailed output")
        # Field can also be used
        seed: int = Field(42, json_schema_extra={"l": "--seed"})

    # Executed commonly for all subcommands
    def prepare(self, args:CommonArgs):
        print(f'Using seed: {args.seed}')

    class VeryAdvancedArgs(CommonArgs):
        # file_name becomes --file-name in command line 
        file_name: str = param(..., l="--name", pattern=r"^[a-zA-Z]+\.(txt|json|yaml)$")
        # Restrict choices
        mode: str = param("read", l="--mode", choices=["read", "write", "append"])
        # You can use float, too
        wait: float = Field(0.5, json_schema_extra={"l": "--wait", "s": "-w"})


    # This will be triggered by `python xxx.py very-advanced` command
    # Args class selection rule: run_very_advanced -> VeryAdvancedArgs (by naming convention)
    # This is an async method that can be awaited
    async def run_very_advanced(self, args):
        print(f"File name: {args.file_name}")
        print(f"Mode: {args.mode}")
        
        print(f"Waiting for {args.wait}s..")
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
    # Uses sys.argv by default    
    cli.run()  
    # Explicitly pass sys.argv
    cli.run(sys.argv)  
    # Pass custom arguments
    cli.run(["program_name", "command", "--value", "value1", "--flag"])    
```


 `param` passes all CLI-specific options (like `s` for short form, `l` for long form) to Field's json_schema_extra.


```bash
# Run very-advanced command
python your_script.py very-advanced --file-name data.txt --mode write --wait 1.5 --verbose
```

## Argument Resolution

### Using Type Annotations

You can directly specify the argument class using type annotations:

```python
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
    class CustomArgs(AutoCLI.CommonArgs):
        value: int = param(42, l="--value", s="-v")
    
    # Use type annotation to specify args class
    def run_command(self, args: CustomArgs):
        print(f"Value: {args.value}")
```


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
        
    # Two-word command example
    class FooBarArgs(AutoCLI.CommonArgs):
        option: str = param("default", l="--option")
    
    def run_foo_bar(self, args):
        print(f"Option: {args.option}")
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
# Install all dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run task coverage
```

## Examples

To run the example CLI:

```bash
python examples/example.py greet --verbose

# Or using taskipy
uv run task example file --file README.md
```

## Claude Code Integration

If you're using Claude Code with your pydantic-autocli application, add this section to your project's `CLAUDE.md`:

```markdown
## AutoCLI Usage

Key patterns:
- `def run_foo_bar(self, args):` → `python script.py foo-bar`
- `def prepare(self, args):` → shared initialization  
- `class FooBarArgs(AutoCLI.CommonArgs):` → command arguments
- Return `True`/`None` (success), `False` (fail), `int` (exit code)

For details: `python your_script.py --help`
```

## License

See LICENSE file.
