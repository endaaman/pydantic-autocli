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

    # Use model_json_schema for pydantic v2 compatibility
    schema_func = getattr(cls, "model_json_schema", None) or cls.schema
    schema = schema_func()
    properties = schema.get("properties", {})

    for key, prop in properties.items():
        logger.debug(f"Processing property: {key}")
        logger.debug(f"Property details: {prop}")

        # Default snake-case conversion for command line args
        snake_key = "--" + key.replace("_", "-")

        # Check for custom CLI args in json_schema_extra or directly in prop
        json_schema_extra = prop.get("json_schema_extra", {})

        # First check direct properties (for backward compatibility)
        if "l" in prop:
            snake_key = prop["l"]
            replacer[snake_key[2:].replace("-", "_")] = key
        # Then check json_schema_extra (preferred for v2)
        elif "l" in json_schema_extra:
            snake_key = json_schema_extra["l"]
            replacer[snake_key[2:].replace("-", "_")] = key

        args = [snake_key]

        # Check for short form in either location
        if "s" in prop:
            args.append(prop["s"])
        elif "s" in json_schema_extra:
            args.append(json_schema_extra["s"])

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

        # Check for choices in either location
        if "choices" in prop:
            kwargs["choices"] = prop["choices"]
        elif "choices" in json_schema_extra:
            kwargs["choices"] = json_schema_extra["choices"]

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

    def _pre_common(self, a):
        """Execute pre-common hook if defined."""
        pre_common = getattr(self, "pre_common", None)
        if pre_common:
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
        sub_parsers = self.main_parser.add_subparsers()

        # Dictionary to store method name -> args class mapping
        self.method_args_mapping = {}

        # List all methods that start with run_
        run_methods = [key for key in dir(self) if key.startswith("run_")]
        logger.debug(f"Found {len(run_methods)} run methods: {run_methods}")

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

            # Create subparser and register arguments
            sub_parser = sub_parsers.add_parser(subcommand_name, parents=[self.main_parser])
            replacer = register_cls_to_parser(args_class, sub_parser)
            sub_parser.set_defaults(__function=name, __cls=args_class, __replacer=replacer)

            logger.debug(f"Registered parser for command '{subcommand_name}' with replacer: {replacer}")

        logger.debug(f"Final method_args_mapping: {[(k, v.__name__) for k, v in self.method_args_mapping.items()]}")


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

        self.raw_args = self.main_parser.parse_args(argv[1:])
        logger.debug(f"Parsed args: {self.raw_args}")

        if not hasattr(self.raw_args, "__function"):
            logger.debug("No function specified, showing help")
            self.main_parser.print_help()
            exit(0)

        args_dict = self.raw_args.__dict__
        name = args_dict["__function"]
        replacer = args_dict["__replacer"]
        args_cls = args_dict["__cls"]

        logger.debug(f"Running command '{name}' with class {args_cls.__name__}")
        logger.debug(f"Replacer mapping: {replacer}")

        args_params = {}
        for k, v in args_dict.items():
            if k.startswith("__"):
                continue
            if k in replacer:
                k = replacer[k]
            args_params[k] = v

        logger.debug(f"Args params for parsing: {args_params}")

        # Support both Pydantic v1 and v2
        parse_method = getattr(args_cls, "model_validate", None) or args_cls.parse_obj

        try:
            args = parse_method(args_params)
            logger.debug(f"Created args instance: {args}")
        except Exception as e:
            logger.error(f"Failed to create args instance: {e}")
            logger.debug(f"Args class: {args_cls}")
            logger.debug(f"Args params: {args_params}")
            exit(1)

        function = getattr(self, "run_" + name)
        logger.debug(f"Function to call: {function.__name__}")
        logger.debug(f"Function signature: {inspect.signature(function)}")

        self.args = args

        self._pre_common(args)
        print(f"Starting <{name}>")

        # Use model_dump for Pydantic v2 compatibility or dict() for v1
        dict_method = getattr(args, "model_dump", None) or args.dict
        args_dict = dict_method()

        if len(args_dict) > 0:
            print("Args")
            maxlen = max(len(k) for k in args_dict) if len(args_dict) > 0 else -1
            for k, v in args_dict.items():
                print(f"\t{k:<{maxlen+1}}: {v}")
        else:
            print("No args")

        result = False
        try:
            if inspect.iscoroutinefunction(function):
                result = asyncio.run(function(args))
            else:
                result = function(args)
            print(f"Done <{name}>")
        except Exception as e:
            logger.error(f"ERROR in command execution: {e}")
            logger.debug("", exc_info=True)
            traceback.print_exc()

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
                logger.warning(f"Unexpected return type: {type(result)}. Using 1.")
                code = 1
        sys.exit(code)
