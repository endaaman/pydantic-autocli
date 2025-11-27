import os
import sys
import re
from string import capwords
import inspect
import asyncio
import typing
from typing import Callable, Type, get_type_hints, Optional, Dict, Any, List, Union
import argparse
import logging
import traceback

from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger("pydantic_autocli")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
# デフォルトではログを出さないようにする（WARNING以上のみ表示）
logger.setLevel(logging.WARNING)


class Colors:
    """ANSI color codes for terminal output."""
    # Check if colors should be disabled
    _enabled = (
        os.environ.get('NO_COLOR') is None
        and hasattr(sys.stdout, 'isatty')
        and sys.stdout.isatty()
    )

    if _enabled:
        GREEN = '\033[92m'
        CYAN = '\033[96m'
        YELLOW = '\033[93m'
        MAGENTA = '\033[95m'
        RED = '\033[91m'
        RESET = '\033[0m'
    else:
        GREEN = ''
        CYAN = ''
        YELLOW = ''
        MAGENTA = ''
        RED = ''
        RESET = ''

    @staticmethod
    def colorize_value(v):
        """Colorize a value based on its type."""
        if isinstance(v, bool):
            return f"{Colors.MAGENTA}{v}{Colors.RESET}"
        elif isinstance(v, str):
            return f"{Colors.GREEN}{v}{Colors.RESET}"
        elif isinstance(v, (int, float)):
            return f"{Colors.CYAN}{v}{Colors.RESET}"
        else:
            return str(v)

def snake_to_pascal(s):
    """Convert snake_case string to PascalCase."""
    r = capwords(s.replace("_", " "))
    r = r.replace(" ", "")
    return r


def snake_to_kebab(s):
    """Convert snake_case string to kebab-case."""
    return s.replace("_", "-")


# Mapping of JSON Schema primitive types to Python types
primitive2type = {
    "string": str,
    "number": float,
    "integer": int,
}


def get_model_fields(cls):
    """Get model fields from a Pydantic model class."""
    return cls.model_fields


def param(default_value, *, s=None, l=None, choices=None, **kwargs):
    """Create a Field object with CLI-specific parameters.

    Args:
        default_value: The default value for the field
        s: Short form argument (e.g., "-n")
        l: Long form argument (e.g., "--name")
        choices: List of allowed values
        **kwargs: Additional arguments passed to Field
    """
    json_schema_extra = {}
    if l:
        json_schema_extra["l"] = l
    if s:
        json_schema_extra["s"] = s
    if choices:
        json_schema_extra["choices"] = choices

    if json_schema_extra:
        kwargs["json_schema_extra"] = json_schema_extra

    return Field(default_value, **kwargs)


def register_cls_to_parser(cls, parser):
    """Register a Pydantic model class to an argparse parser.

    This function converts Pydantic model fields to argparse arguments.
    It handles various field types and their CLI-specific configurations.

    Args:
        cls: A Pydantic model class
        parser: An argparse parser to add arguments to

    Returns:
        dict: A mapping of CLI argument names to model field names
    """
    logger.debug(f"Registering class {cls.__name__} to parser")
    replacer = {}

    schema = cls.model_json_schema()
    properties = schema.get("properties", {})

    for key, prop in properties.items():
        logger.debug(f"Processing property: {key}")
        logger.debug(f"Property details: {prop}")

        # Default snake-case conversion for command line args
        snake_key = "--" + key.replace("_", "-")

        # json_schema_extra fields are expanded directly into prop in Pydantic v2
        if "l" in prop:
            snake_key = prop["l"]
            replacer[snake_key[2:].replace("-", "_")] = key

        args = [snake_key]

        if "s" in prop:
            args.append(prop["s"])

        # Check for reserved --help option
        if "--help" in args:
            raise ValueError(
                f"'--help' is reserved for AutoCLI. "
                f"Please use a different option name in {cls.__name__}.{key}."
            )

        kwargs = {}
        if "description" in prop:
            kwargs["help"] = prop["description"]

        if prop["type"] in primitive2type:
            kwargs["type"] = primitive2type[prop["type"]]
            if "default" in prop:
                kwargs["default"] = prop["default"]
                kwargs["metavar"] = str(prop["default"])
            else:
                kwargs["required"] = True
                kwargs["metavar"] = f"<{prop['type']}>"
        elif prop["type"] == "boolean":
            if "default" in prop:
                logger.debug(f"default value of bool is ignored.")
            kwargs["action"] = "store_true"
        elif prop["type"] == "array":
            if "default" in prop:
                kwargs["default"] = prop["default"]
                kwargs["metavar"] = str(prop["default"])
                kwargs["nargs"] = "+"
            else:
                kwargs["required"] = True
                kwargs["metavar"] = None
                kwargs["nargs"] = "*"
            kwargs["type"] = primitive2type[prop["items"]["type"]]

        if "choices" in prop:
            kwargs["choices"] = prop["choices"]

        logger.debug(f"Parser arguments: {args}")
        logger.debug(f"Parser kwargs: {kwargs}")

        parser.add_argument(*args, **kwargs)
    return replacer


class AutoCLI:
    """Base class for automatically generating CLI applications from Pydantic models.

    This class provides functionality to:
    1. Automatically generate CLI commands from class methods
    2. Map Pydantic model fields to CLI arguments
    3. Handle type annotations and naming conventions for argument classes
    4. Support async commands
    """

    class CommonArgs(BaseModel):
        """Base class for common arguments shared across all commands."""
        pass

    quiet: bool = False

    def _pre_common(self, a):
        """Execute pre-common hook if defined."""
        import warnings

        # Check for new prepare() method first
        prepare = getattr(self, "prepare", None)
        pre_common = getattr(self, "pre_common", None)

        if prepare:
            prepare(a)
        elif pre_common:
            warnings.warn(
                "pre_common() is deprecated. Use prepare() instead for shared initialization.",
                DeprecationWarning,
                stacklevel=2
            )
            pre_common(a)

    def __init__(self):
        """Initialize the CLI application.

        This sets up:
        - Argument parser
        - Subparsers for each command
        - Method to args class mapping
        """
        logger.debug(f"Initializing AutoCLI for class {self.__class__.__name__}")

        self.args = None
        self.runners = {}
        self.function = None
        self.default_args_class = getattr(self.__class__, "CommonArgs", self.CommonArgs)

        logger.debug(f"Default args class: {self.default_args_class.__name__}")

        self.main_parser = argparse.ArgumentParser(add_help=False)
        # Add custom help argument to main parser only (without -h to allow user-defined -h args)
        self.main_parser.add_argument('--help', action='store_true', help='show this help message and exit')
        sub_parsers = self.main_parser.add_subparsers()

        # Dictionary to store method name -> args class mapping
        self.method_args_mapping = {}
        # Store subparsers for detailed help generation
        self.subparsers_info = {}
        # Track if run_default exists
        self.has_default = hasattr(self, "run_default")

        # List all methods that start with run_
        run_methods = [key for key in dir(self) if key.startswith("run_")]
        logger.debug(f"Found {len(run_methods)} run methods: {run_methods}")
        logger.debug(f"Has run_default: {self.has_default}")

        for key in run_methods:
            m = re.match(r"^run_(.*)$", key)
            if not m:
                continue
            name = m[1]

            logger.debug(f"Processing command '{name}' from method {key}")

            subcommand_name = snake_to_kebab(name)

            # Get the appropriate args class for this method
            args_class = self._get_args_class_for_method(key)

            logger.debug(f"For command '{name}', using args class: {args_class.__name__}")

            # Store the mapping for later use
            self.method_args_mapping[name] = args_class

            # Create subparser without -h to allow user-defined -h args
            sub_parser = sub_parsers.add_parser(subcommand_name, add_help=False)
            # Add --help manually (without -h to allow user-defined -h args)
            sub_parser.add_argument('--help', action='store_true', help='show command help and exit')
            replacer = register_cls_to_parser(args_class, sub_parser)
            sub_parser.set_defaults(__function=name, __cls=args_class, __replacer=replacer)

            # Store subparser info for detailed help
            method_func = getattr(self, key)
            method_doc = method_func.__doc__.strip() if method_func.__doc__ else None
            self.subparsers_info[subcommand_name] = {
                'parser': sub_parser,
                'method_name': name,
                'description': method_doc
            }

            logger.debug(f"Registered parser for command '{subcommand_name}' with replacer: {replacer}")

        # If run_default exists, register its args to main_parser for `cli --arg` usage
        if self.has_default and "default" in self.method_args_mapping:
            default_args_class = self.method_args_mapping["default"]
            self.default_replacer = register_cls_to_parser(default_args_class, self.main_parser)
            logger.debug(f"Registered default args to main parser: {default_args_class.__name__}")
        else:
            self.default_replacer = {}

        logger.debug(f"Final method_args_mapping: {[(k, v.__name__) for k, v in self.method_args_mapping.items()]}")

    def print_help(self, command=None):
        """Print help message.

        Args:
            command: If None, print full help including all subcommands and AutoCLI patterns.
                    If specified, print help for that specific command only (no patterns).
        """
        if command is not None:
            # Print help for specific command
            subcommand_name = snake_to_kebab(command)
            if subcommand_name not in self.subparsers_info:
                print(f"Unknown command: {command}")
                return

            info = self.subparsers_info[subcommand_name]
            info['parser'].print_help()
            return

        # Print full help
        # Print main usage
        self.main_parser.print_help()
        print()

        # Print AutoCLI usage patterns
        print("AutoCLI patterns:")
        print("  • def run_foo_bar(self, args): → python script.py foo-bar")
        print("  • def prepare(self, args): → shared initialization")
        print("  • class FooBarArgs(AutoCLI.CommonArgs): → command arguments")
        print("  • param(..., l='--long', s='-s') → custom argument options")
        print("  • return True/None (success), False (fail), int (exit code)")
        print()

        if not self.subparsers_info:
            return

        print("Available commands:")
        for subcommand_name, info in self.subparsers_info.items():
            desc = info['description'] or "No description available"
            # Limit description to first line for overview
            first_line = desc.split('\n')[0] if desc else "No description available"
            print(f"  {subcommand_name:<12} - {first_line}")

        print("\nCommand details:")
        for subcommand_name, info in self.subparsers_info.items():
            print(f"\n{'=' * 3} {subcommand_name} {'=' * 3}")
            info['parser'].print_help()

    def _get_type_annotation_for_method(self, method_key) -> Optional[Type[BaseModel]]:
        """Extract type annotation for the run_* method parameter (other than self).

        This method tries multiple approaches to get the type annotation:
        1. Direct type hints from the method (most reliable)
        2. Signature analysis for modern Python versions
        3. Source code analysis as fallback for string annotations
        """
        method = getattr(self, method_key)

        logger.debug(f"Trying to get type annotation for method {method_key}")

        try:
            # First try: Get type hints directly - most reliable across Python versions
            try:
                # Get type hints from the method using globals and locals
                locals_dict = {name: getattr(self.__class__, name) for name in dir(self.__class__)}
                # Add main module globals
                if "__main__" in sys.modules:
                    main_globals = sys.modules["__main__"].__dict__
                    locals_dict.update(main_globals)

                type_hints = get_type_hints(method, globalns=globals(), localns=locals_dict)
                logger.debug(f"Type hints for {method_key}: {type_hints}")

                # Check all parameters (except 'self' and 'return') for BaseModel types
                for param_name, param_type in type_hints.items():
                    if param_name != "return" and param_name != "self":
                        if inspect.isclass(param_type) and issubclass(param_type, BaseModel):
                            logger.debug(f"Found valid parameter {param_name} with type {param_type.__name__}")
                            return param_type

                if type_hints:
                    logger.debug(f"Found parameters but none are BaseModel subclasses: {type_hints}")
            except Exception as e:
                logger.debug(f"Error getting type hints directly: {e}")

            # Second try: Use signature analysis
            signature = inspect.signature(method)
            params = list(signature.parameters.values())

            if len(params) > 1:  # At least self + one parameter
                param = params[1]  # First param after self
                param_name = param.name
                annotation = param.annotation

                logger.debug(f"Parameter from signature: {param_name} with annotation {annotation}")

                # Check if the annotation is already a class
                if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
                    logger.debug(f"Found direct class annotation: {annotation.__name__}")
                    return annotation

                # Check if annotation is a string (common in older Python versions)
                if isinstance(annotation, str) and annotation != inspect.Parameter.empty:
                    class_name = annotation

                    # Try to find the class by name in various places
                    # First check class attributes
                    if hasattr(self.__class__, class_name):
                        attr = getattr(self.__class__, class_name)
                        if inspect.isclass(attr) and issubclass(attr, BaseModel):
                            logger.debug(f"Found class {class_name} in class attributes")
                            return attr

                    # Then search through all class attributes by name
                    for attr_name in dir(self.__class__):
                        attr = getattr(self.__class__, attr_name)
                        if inspect.isclass(attr) and attr.__name__ == class_name:
                            if issubclass(attr, BaseModel):
                                logger.debug(f"Found class {class_name} by name")
                                return attr

                    # Check globals
                    if class_name in globals() and inspect.isclass(globals()[class_name]):
                        cls = globals()[class_name]
                        if issubclass(cls, BaseModel):
                            logger.debug(f"Found class {class_name} in globals")
                            return cls
            else:
                logger.debug(f"Method {method_key} has insufficient parameters: {params}")

            # Third try: Source code analysis as last resort
            source = inspect.getsource(method)
            logger.debug(f"Method source: {source}")

            # Use regex to extract parameter info from source
            method_pattern = rf"def\s+{method_key}\s*\(\s*self\s*,\s*([a-zA-Z0-9_]+)\s*:\s*([A-Za-z0-9_\.]+)"
            match = re.search(method_pattern, source)

            if match:
                param_name = match.group(1).strip()
                class_name = match.group(2).strip()
                logger.debug(f"Extracted from source - Parameter: {param_name}, Type: {class_name}")

                # Look for the class by name
                # First check class attributes
                if hasattr(self.__class__, class_name):
                    attr = getattr(self.__class__, class_name)
                    if inspect.isclass(attr) and issubclass(attr, BaseModel):
                        logger.debug(f"Found class {class_name} from source analysis")
                        return attr

                # Search all attributes
                for attr_name in dir(self.__class__):
                    attr = getattr(self.__class__, attr_name)
                    if inspect.isclass(attr) and attr.__name__ == class_name:
                        if issubclass(attr, BaseModel):
                            logger.debug(f"Found class {class_name} from source by name matching")
                            return attr

                # Check globals
                if class_name in globals() and inspect.isclass(globals()[class_name]):
                    cls = globals()[class_name]
                    if issubclass(cls, BaseModel):
                        logger.debug(f"Found class {class_name} in globals from source analysis")
                        return cls
            else:
                logger.debug(f"Could not extract parameter info from source")

        except Exception as e:
            logger.exception(f"Error getting type annotation for {method_key}: {e}")

        logger.debug(f"No type annotation found for method {method_key}")
        return None

    def _get_args_class_for_method(self, method_name) -> Type[BaseModel]:
        """Get the appropriate args class for a method based on type annotation or naming convention.

        The resolution order is:
        1. Type annotation in the method signature
        2. Naming convention (CommandArgs class for run_command method)
        3. Fall back to CommonArgs
        """
        logger.debug(f"Getting args class for method {method_name}")

        # Get the command name to check for naming convention classes
        command_name = re.match(r"^run_(.*)$", method_name)[1]

        # Try multiple naming conventions:
        # 1. PascalCase + Args (e.g., FileArgs for run_file)
        # 2. Command-specific custom class (e.g., CustomArgs for a specific command)
        args_class_names = [
            snake_to_pascal(command_name) + "Args",  # Standard convention
            command_name.capitalize() + "Args",      # Simple capitalization
            "CustomArgs"                             # Common custom name
        ]

        logger.debug(f"Looking for convention-based classes: {args_class_names}")

        # Check if any naming convention classes exist
        convention_class = None
        for args_class_name in args_class_names:
            if hasattr(self.__class__, args_class_name):
                attr = getattr(self.__class__, args_class_name)
                if inspect.isclass(attr) and issubclass(attr, BaseModel):
                    logger.debug(f"Found convention-based class {args_class_name}")
                    convention_class = attr
                    break
                else:
                    logger.debug(f"Found attribute {args_class_name} but it's not a BaseModel subclass")
            else:
                logger.debug(f"No attribute named {args_class_name} found in {self.__class__.__name__}")

        # Check for type annotation in the method
        annotation_cls = self._get_type_annotation_for_method(method_name)

        # Check for conflicts between naming convention and type annotation
        if annotation_cls is not None:
            logger.debug(f"Found annotation class for {method_name}: {annotation_cls.__name__}")

            # If both convention class and annotation class exist and are different, show warning
            if convention_class is not None and annotation_cls != convention_class:
                warning_msg = (
                    f"Warning: Method '{method_name}' has both a type annotation ({annotation_cls.__name__}) "
                    f"and a naming convention class ({convention_class.__name__}). "
                    f"The type annotation takes precedence."
                )
                logger.warning(warning_msg)
                print(warning_msg)

            return annotation_cls

        # If no type annotation but convention class exists, use it
        if convention_class is not None:
            return convention_class

        # Fall back to CommonArgs
        logger.debug(f"Falling back to default_args_class for {method_name}")
        return self.default_args_class


    def run(self, argv=None):
        """Run the CLI application.

        This method:
        1. Parses command line arguments
        2. Finds the appropriate command and args class
        3. Executes the command with parsed arguments
        4. Handles async commands

        Args:
            argv: Optional list of command line arguments. Defaults to sys.argv.
        """
        logger.debug("Starting AutoCLI.run()")
        logger.debug(f"Available commands: {[k for k in dir(self) if k.startswith('run_')]}")

        # Use provided argv or default to sys.argv
        if argv is None:
            argv = sys.argv

        # --help takes priority over all other options
        if '--help' in argv[1:]:
            # Find subcommand in argv (first non-option arg that matches a subcommand)
            subcommand = None
            for arg in argv[1:]:
                if not arg.startswith('-') and arg in self.subparsers_info:
                    subcommand = arg
                    break
            if subcommand:
                self.print_help(subcommand.replace('-', '_'))
            elif self.has_default:
                self.print_help('default')
            else:
                self.print_help()
            sys.exit(0)

        self.raw_args = self.main_parser.parse_args(argv[1:])
        logger.debug(f"Parsed args: {self.raw_args}")

        args_dict = self.raw_args.__dict__

        if not hasattr(self.raw_args, "__function"):
            # No subcommand specified
            if self.has_default:
                # run_default exists, execute it
                logger.debug("No function specified, running default command")
                name = "default"
                args_cls = self.method_args_mapping["default"]
                replacer = self.default_replacer
            else:
                # No run_default, show help
                logger.debug("No function specified, showing help")
                self.print_help()
                sys.exit(0)
        else:
            name = args_dict["__function"]
            replacer = args_dict["__replacer"]
            args_cls = args_dict["__cls"]

        logger.debug(f"Running command '{name}' with class {args_cls.__name__}")
        logger.debug(f"Replacer mapping: {replacer}")

        args_params = {}
        for k, v in args_dict.items():
            if k.startswith("__"):
                continue
            if k == "help":
                continue
            if k in replacer:
                k = replacer[k]
            args_params[k] = v

        logger.debug(f"Args params for parsing: {args_params}")

        try:
            args = args_cls.model_validate(args_params)
            logger.debug(f"Created args instance: {args}")
        except Exception as e:
            logger.error(f"Failed to create args instance: {e}")
            logger.debug(f"Args class: {args_cls}")
            logger.debug(f"Args params: {args_params}")
            sys.exit(1)

        function = getattr(self, "run_" + name)
        logger.debug(f"Function to call: {function.__name__}")
        logger.debug(f"Function signature: {inspect.signature(function)}")

        self.args = args

        self._pre_common(args)

        if not self.quiet:
            print(f"{Colors.GREEN}▶{Colors.RESET} Starting {Colors.CYAN}{name}{Colors.RESET}")
            args_dict = args.model_dump()
            if len(args_dict) > 0:
                maxlen = max(len(k) for k in args_dict)
                for k, v in args_dict.items():
                    print(f"  {k:<{maxlen}} = {Colors.colorize_value(v)}")
                print()

        result = False
        try:
            if inspect.iscoroutinefunction(function):
                result = asyncio.run(function(args))
            else:
                result = function(args)
            if not self.quiet:
                print(f"{Colors.GREEN}✓{Colors.RESET} Done {Colors.CYAN}{name}{Colors.RESET}")
        except Exception as e:
            logger.error(f"ERROR in command execution: {e}")
            logger.debug("", exc_info=True)
            traceback.print_exc()
            if not self.quiet:
                print(f"{Colors.RED}✗{Colors.RESET} Failed {Colors.CYAN}{name}{Colors.RESET}")

        # Validate and handle the result type
        if result is None:
            code = 0
        elif isinstance(result, bool):
            code = 0 if result else 1
        elif isinstance(result, int):
            code = result
        else:
            # Try to convert to int for NumPy/PyTorch/other numeric types
            try:
                code = int(result)
            except (ValueError, TypeError):
                # For unconvertible types, treat as failure
                logger.warning(f"Unexpected return type: {type(result)}. Command methods should return None, bool, or int (status code). Using status code 1.")
                code = 1
        sys.exit(code)
