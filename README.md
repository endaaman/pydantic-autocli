# pydantic-autocli

[![CI](https://github.com/endaaman/pydantic-autocli/workflows/CI/badge.svg)](https://github.com/endaaman/pydantic-autocli/actions)
[![codecov](https://codecov.io/gh/endaaman/pydantic-autocli/branch/master/graph/badge.svg)](https://codecov.io/gh/endaaman/pydantic-autocli)

Automatically generate sub-command based CLI applications from Pydantic models.

## Installation

```bash
pip install pydantic-autocli
```

## Features

- Automatic CLI generation from Pydantic models
- Type-safe argument parsing with validation
- Async command support
- Default command (`run_default`) and subcommands
- Positional and remainder arguments (`--`) via `ExtraArgsMixin`

Requires Python 3.10+ and Pydantic v2.

## Basic Usage

```python
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
    # Default command: runs when no subcommand is provided
    class DefaultArgs(BaseModel):
        message: str = param("Hello", l="--message", s="-m")

    def run_default(self, args: DefaultArgs):
        print(args.message)

    # Subcommand: `python script.py greet`
    class GreetArgs(BaseModel):
        name: str = param("World", l="--name", s="-n")
        count: int = param(1, l="--count", s="-c")

    def run_greet(self, args: GreetArgs):
        for _ in range(args.count):
            print(f"Hello, {args.name}!")

if __name__ == "__main__":
    MyCLI().run()
```

```bash
# Default command
python script.py                       # prints "Hello"
python script.py --message "Hi"        # prints "Hi"

# Subcommand
python script.py greet --name Alice    # prints "Hello, Alice!"
python script.py greet -n Bob -c 3     # prints "Hello, Bob!" 3 times

# Help
python script.py --help                # shows default command help
python script.py greet --help          # shows greet command help
```

Note: `--help` is reserved and cannot be used as a field name.

## Advanced Usage

### Common Arguments and Initialization

```python
from pydantic_autocli import AutoCLI, param

class MyCLI(AutoCLI):
    # Shared arguments across all commands
    class CommonArgs(AutoCLI.CommonArgs):
        verbose: bool = param(False, l="--verbose", s="-v")

    # Runs before every command
    def prepare(self, args: CommonArgs):
        if args.verbose:
            print("Verbose mode enabled")

    def run_task(self, args: CommonArgs):
        print("Running task...")
```

### Parameter Options

```python
class TaskArgs(AutoCLI.CommonArgs):
    # Required argument (no default)
    name: str = param(..., l="--name", s="-n")
    # Choices
    mode: str = param("read", l="--mode", choices=["read", "write"])
    # Validation
    count: int = param(1, l="--count", ge=1, le=100)
    pattern: str = param(".*", l="--pattern", pattern=r"^[a-z]+$")
```

### Async Commands and Return Values

```python
async def run_fetch(self, args):
    await asyncio.sleep(1)
    if error:
        return False  # exit code 1
    return True       # exit code 0
    # return 42       # custom exit code
```

### Positional and Remainder Arguments (ExtraArgsMixin)

Use `ExtraArgsMixin` to capture positional arguments and arguments after `--`:

```python
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param, ExtraArgsMixin

class MyCLI(AutoCLI):
    class RunArgs(ExtraArgsMixin, BaseModel):
        verbose: bool = param(False, l="--verbose", s="-v")

    def run_exec(self, args: RunArgs):
        # Positional arguments (before --)
        files = args.get_positional()  # ['file1.py', 'file2.py']

        # Remainder arguments (after --)
        cmd = args.get_remainder()       # 'python -m pytest --tb=short'
        cmd_list = args.get_remainder_list()  # ['python', '-m', 'pytest', '--tb=short']

        print(f"Files: {files}")
        print(f"Command: {cmd}")

if __name__ == "__main__":
    MyCLI().run()
```

```bash
# Positional args and remainder after --
python script.py exec file1.py file2.py -- python -m pytest --tb=short

# Only remainder
python script.py exec -- nested-command --option value
```

Note: For the default command (`run_default`), `get_positional()` always returns an empty list to avoid ambiguity with subcommand names. Use `get_remainder()` instead.

## Argument Resolution

Args class is resolved in this order:

1. **Type annotation**: `def run_cmd(self, args: MyArgs)` → uses `MyArgs`
2. **Naming convention**: `run_foo_bar` → looks for `FooBarArgs`
3. **Fallback**: uses `CommonArgs`

```python
class MyCLI(AutoCLI):
    class FooBarArgs(BaseModel):
        option: str = param("x", l="--option")

    # Uses FooBarArgs by naming convention
    def run_foo_bar(self, args):
        print(args.option)
```


## Development

```bash
uv sync                  # Install dependencies
uv run task test         # Run tests
uv run task coverage     # Run tests with coverage
uv run task lint         # Lint code
uv run task example      # Run example CLI
```

## Claude Code Integration

Add to your project's `CLAUDE.md`:

```markdown
## AutoCLI Usage

- `def run_foo_bar(self, a: FooBarArgs)` → `script.py foo-bar`
- `def run_default(self, a: DefaultArgs)` → `script.py` (no subcommand)
- `class CommonArgs` → shared arguments across all commands
- `def prepare(self, a: CommonArgs)` → runs before every command
- Return `True`/`None` (exit 0), `False` (exit 1), `int` (custom exit code)

For details: `script.py --help` or `script.py <command> --help`
```

## License

See LICENSE file.
