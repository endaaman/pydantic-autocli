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

from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger("pydantic_autocli")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# デフォルトではログを出さないようにする（WARNING以上のみ表示）
logger.setLevel(logging.WARNING)

def snake_to_pascal(s):
    """Convert snake_case string to PascalCase."""
    r = capwords(s.replace('_', ' '))
    r = r.replace(' ', '')
    return r


def snake_to_kebab(s):
    """Convert snake_case string to kebab-case."""
    return s.replace('_', '-')


# Mapping of JSON Schema primitive types to Python types
primitive2type = {
    'string': str,
    'number': float,
    'integer': int,
}


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
        snake_key = '--' + key.replace('_', '-')
        
        # Check for custom CLI args in json_schema_extra or directly in prop
        json_schema_extra = prop.get('json_schema_extra', {})
        
        # First check direct properties (for backward compatibility)
        if 'l' in prop:
            snake_key = prop['l']
            replacer[snake_key[2:].replace('-', '_')] = key
        # Then check json_schema_extra (preferred for v2)
        elif 'l' in json_schema_extra:
            snake_key = json_schema_extra['l']
            replacer[snake_key[2:].replace('-', '_')] = key

        args = [snake_key]
        
        # Check for short form in either location
        if 's' in prop:
            args.append(prop['s'])
        elif 's' in json_schema_extra:
            args.append(json_schema_extra['s'])

        kwargs = {}
        if 'description' in prop:
            kwargs['help'] = prop['description']

        if prop['type'] in primitive2type:
            kwargs['type'] = primitive2type[prop['type']]
            if 'default' in prop:
                kwargs['default'] = prop['default']
                kwargs['metavar'] = str(prop['default'])
            else:
                kwargs['required'] = True
                kwargs['metavar'] = f'<{prop["type"]}>'
        elif prop['type'] == 'boolean':
            # if 'default' in prop:
            #     print('default value of bool is ignored.')
            kwargs['action'] = 'store_true'
        elif prop['type'] == 'array':
            if 'default' in prop:
                kwargs['default'] = prop['default']
                kwargs['metavar'] = str(prop['default'])
                kwargs['nargs'] = '+'
            else:
                kwargs['required'] = True
                kwargs['metavar'] = None
                kwargs['nargs'] = '*'
            kwargs['type'] = primitive2type[prop['items']['type']]

        # Check for choices in either location
        if 'choices' in prop:
            kwargs['choices'] = prop['choices']
        elif 'choices' in json_schema_extra:
            kwargs['choices'] = json_schema_extra['choices']

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

    def with_suffix(self, base, suffix):
        """Add a suffix to a base string if suffix is provided."""
        if suffix:
            return f'{base}_{suffix}'
        return base

    def with_wrote(self, s):
        """Print a message when a file is written."""
        print('wrote', s)
        return s

    class CommonArgs(BaseModel):
        """Base class for common arguments shared across all commands."""
        pass

    def _pre_common(self, a):
        """Execute pre-common hook if defined."""
        pre_common = getattr(self, 'pre_common', None)
        if pre_common:
            pre_common(a)

    def wrap_runner(self, key):
        """Wrap a runner method with common functionality.
        
        This includes:
        - Setting instance variables
        - Executing pre-common hook
        - Printing start/end messages
        - Handling async methods
        """
        runner = getattr(self, key)
        def alt_runner(a):
            self.a = a
            self.function = key
            self._pre_common(a)
            print(f'Starting <{key}>')
            d = a.dict()
            if len(d) > 0:
                print('Args')
                maxlen = max(len(k) for k in d) if len(d) > 0 else -1
                for k, v in d.items():
                    print(f'\t{k:<{maxlen+1}}: {v}')
            else:
                print('No args')

            if inspect.iscoroutinefunction(runner):
                r = asyncio.run(runner(a))
            else:
                r = runner(a)
            print(f'Done <{key}>')
            return r
        return alt_runner

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
                if '__main__' in sys.modules:
                    main_globals = sys.modules['__main__'].__dict__
                    locals_dict.update(main_globals)
                
                type_hints = get_type_hints(method, globalns=globals(), localns=locals_dict)
                logger.debug(f"Type hints for {method_key}: {type_hints}")
                
                # Check all parameters (except 'self' and 'return') for BaseModel types
                for param_name, param_type in type_hints.items():
                    if param_name != 'return' and param_name != 'self':
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
            
        # First, check for type annotation in the method
        annotation_cls = self._get_type_annotation_for_method(method_name)
        if annotation_cls is not None:
            logger.debug(f"Found annotation class for {method_name}: {annotation_cls.__name__}")
            return annotation_cls
        
        # If no type annotation, look for class named according to convention
        command_name = re.match(r'^run_(.*)$', method_name)[1]
        
        # Try multiple naming conventions:
        # 1. PascalCase + Args (e.g., FileArgs for run_file)
        # 2. Command-specific custom class (e.g., CustomArgs for a specific command)
        args_class_names = [
            snake_to_pascal(command_name) + 'Args',  # Standard convention
            command_name.capitalize() + 'Args',      # Simple capitalization
            'CustomArgs'                             # Common custom name
        ]
        
        logger.debug(f"Looking for convention-based classes: {args_class_names}")
        
        # Search for any of the possible class names
        for args_class_name in args_class_names:
            if hasattr(self.__class__, args_class_name):
                attr = getattr(self.__class__, args_class_name)
                if inspect.isclass(attr) and issubclass(attr, BaseModel):
                    logger.debug(f"Found convention-based class {args_class_name}")
                    return attr
                else:
                    logger.debug(f"Found attribute {args_class_name} but it's not a BaseModel subclass")
            else:
                logger.debug(f"No attribute named {args_class_name} found in {self.__class__.__name__}")
        
        # Fall back to CommonArgs
        logger.debug(f"Falling back to default_args_class for {method_name}")
        return self.default_args_class

    def __init__(self):
        """Initialize the CLI application.
        
        This sets up:
        - Argument parser
        - Subparsers for each command
        - Method to args class mapping
        """
        logger.debug(f"Initializing AutoCLI for class {self.__class__.__name__}")
            
        self.a = None
        self.runners = {}
        self.function = None
        self.default_args_class = getattr(self.__class__, 'CommonArgs', self.CommonArgs)
        
        logger.debug(f"Default args class: {self.default_args_class.__name__}")

        self.main_parser = argparse.ArgumentParser(add_help=False)
        sub_parsers = self.main_parser.add_subparsers()
        
        # Dictionary to store method name -> args class mapping
        self.method_args_mapping = {}
        
        # List all methods that start with run_
        run_methods = [key for key in dir(self) if key.startswith('run_')]
        logger.debug(f"Found {len(run_methods)} run methods: {run_methods}")
        
        for key in run_methods:
            m = re.match(r'^run_(.*)$', key)
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

    def run(self):
        """Run the CLI application.
        
        This method:
        1. Parses command line arguments
        2. Finds the appropriate command and args class
        3. Executes the command with parsed arguments
        4. Handles async commands
        """
        logger.debug("Starting AutoCLI.run()")
        logger.debug(f"Available commands: {[k for k in dir(self) if k.startswith('run_')]}")
            
        self.raw_args = self.main_parser.parse_args()
        logger.debug(f"Parsed args: {self.raw_args}")
            
        if not hasattr(self.raw_args, '__function'):
            logger.debug("No function specified, showing help")
            self.main_parser.print_help()
            exit(0)

        args_dict = self.raw_args.__dict__
        name = args_dict['__function']
        replacer = args_dict['__replacer']
        args_cls = args_dict['__cls']
        
        logger.debug(f"Running command '{name}' with class {args_cls.__name__}")
        logger.debug(f"Replacer mapping: {replacer}")

        args_params = {}
        for k, v in args_dict.items():
            if k.startswith('__'):
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

        function = getattr(self, 'run_' + name)
        logger.debug(f"Function to call: {function.__name__}")
        logger.debug(f"Function signature: {inspect.signature(function)}")

        self.a = args

        self._pre_common(args)
        print(f'Starting <{name}>')
        
        # Use model_dump for Pydantic v2 compatibility or dict() for v1
        dict_method = getattr(args, "model_dump", None) or args.dict
        args_dict = dict_method()
        
        if len(args_dict) > 0:
            print('Args')
            maxlen = max(len(k) for k in args_dict) if len(args_dict) > 0 else -1
            for k, v in args_dict.items():
                print(f'\t{k:<{maxlen+1}}: {v}')
        else:
            print('No args')

        try:
            if inspect.iscoroutinefunction(function):
                r = asyncio.run(function(args))
            else:
                r = function(args)
            print(f'Done <{name}>')
        except Exception as e:
            logger.error(f"ERROR in command execution: {e}")
            logger.debug("", exc_info=True)


if __name__ == '__main__':
    class CLI(AutoCLI):
        class CustomArgs(BaseModel):
            diff_name: int = Field(..., s='-D', l='--diff')
        
        def run_foo(self, a: CustomArgs):
            print(a)

        async def run_async(self, a):
            await asyncio.sleep(1)
            print('hi')
            await asyncio.sleep(1)
            print('hi')
            await asyncio.sleep(1)
            print('hi')
            print('async')

    cli = CLI()
    cli.run()
