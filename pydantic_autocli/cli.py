import os
import sys
import re
from string import capwords
import inspect
import asyncio
import typing
from typing import Callable, Type, get_type_hints, Optional, Dict, Any
import argparse

from pydantic import BaseModel, Field


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

VERBOSE = False


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
    if VERBOSE:
        print(cls)
    replacer = {}
    
    # Use model_json_schema for pydantic v2 compatibility
    schema_func = getattr(cls, "model_json_schema", None) or cls.schema
    schema = schema_func()
    properties = schema.get("properties", {})
    
    for key, prop in properties.items():
        if VERBOSE:
            print('Name: ', key)
            print('Prop:', prop)

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

        if VERBOSE:
            print('args', args)
            print('kwargs', kwargs)
            print()

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
        def alt_runner(args):
            self.a = args
            self.function = key
            self._pre_common(args)
            print(f'Starting <{key}>')
            d = args.dict()
            if len(d) > 0:
                print('Args')
                maxlen = max(len(k) for k in d) if len(d) > 0 else -1
                for k, v in d.items():
                    print(f'\t{k:<{maxlen+1}}: {v}')
            else:
                print('No args')

            if inspect.iscoroutinefunction(runner):
                r = asyncio.run(runner(args))
            else:
                r =  runner(args)
            print(f'Done <{key}>')
            return r
        return alt_runner

    def _get_type_annotation_for_method(self, method_key) -> Optional[Type[BaseModel]]:
        """Extract type annotation for the run_* method parameter (other than self).
        
        This method tries multiple approaches to get the type annotation:
        1. Direct type annotation in the method signature
        2. Type hints from the method
        3. Source code analysis for string annotations
        """
        method = getattr(self, method_key)
        
        try:
            # Get signature parameters
            params = list(inspect.signature(method).parameters.values())
            if len(params) <= 1:
                return None  # No parameters besides self
            
            param_name = params[1].name  # First param after self
            
            # Get type annotation from source
            source = inspect.getsource(method)
            
            # Look for annotations like "def run_xxx(self, arg: SomeClass):"
            annotation_pattern = rf"def\s+{method_key}\s*\(\s*self\s*,\s*{param_name}\s*:\s*([A-Za-z0-9_\.]+)"
            match = re.search(annotation_pattern, source)
            
            if match:
                # Extract the class name from annotation
                class_name = match.group(1).strip()
                
                # Get class from globals or instance attributes
                for attr_name in dir(self.__class__):
                    attr = getattr(self.__class__, attr_name)
                    if inspect.isclass(attr) and attr.__name__ == class_name:
                        if issubclass(attr, BaseModel):
                            return attr
            
            # Fallback to get_type_hints, but evaluate postponed annotations
            # to handle ForwardRefs or string annotations
            type_hints = get_type_hints(method, globalns=globals())
            
            if param_name in type_hints:
                param_type = type_hints[param_name]
                if inspect.isclass(param_type) and issubclass(param_type, BaseModel):
                    return param_type
                
        except Exception as e:
            if VERBOSE:
                print(f"Error getting type annotation: {e}")
        
        return None
    
    def _get_args_class_for_method(self, method_name) -> Type[BaseModel]:
        """Get the appropriate args class for a method based on type annotation or naming convention.
        
        The resolution order is:
        1. Type annotation in the method signature
        2. Naming convention (CommandArgs class for run_command method)
        3. Fall back to CommonArgs
        """
        # First, check for type annotation in the method
        annotation_cls = self._get_type_annotation_for_method(method_name)
        if annotation_cls is not None:
            return annotation_cls
        
        # If no type annotation, look for class named according to convention
        command_name = re.match(r'^run_(.*)$', method_name)[1]
        args_class_name = snake_to_pascal(command_name) + 'Args'
        
        # Search for the class as a direct attribute of the CLI class
        if hasattr(self.__class__, args_class_name):
            attr = getattr(self.__class__, args_class_name)
            if inspect.isclass(attr) and issubclass(attr, BaseModel):
                return attr
        
        # Fall back to CommonArgs
        return self.default_args_class

    def __init__(self):
        """Initialize the CLI application.
        
        This sets up:
        - Argument parser
        - Subparsers for each command
        - Method to args class mapping
        """
        self.a = None
        self.runners = {}
        self.function = None
        self.default_args_class = getattr(self.__class__, 'CommonArgs', self.CommonArgs)

        self.main_parser = argparse.ArgumentParser(add_help=False)
        sub_parsers = self.main_parser.add_subparsers()
        
        # Dictionary to store method name -> args class mapping
        self.method_args_mapping = {}
        
        for key in dir(self):
            m = re.match(r'^run_(.*)$', key)
            if not m:
                continue
            name = m[1]

            subcommand_name = snake_to_kebab(name)
            
            # Get the appropriate args class for this method
            args_class = self._get_args_class_for_method(key)
            
            # Store the mapping for later use
            self.method_args_mapping[name] = args_class
            
            # Create subparser and register arguments
            sub_parser = sub_parsers.add_parser(subcommand_name, parents=[self.main_parser])
            replacer = register_cls_to_parser(args_class, sub_parser)
            sub_parser.set_defaults(__function=name, __cls=args_class, __replacer=replacer)

    def run(self):
        """Run the CLI application.
        
        This method:
        1. Parses command line arguments
        2. Finds the appropriate command and args class
        3. Executes the command with parsed arguments
        4. Handles async commands
        """
        self.raw_args = self.main_parser.parse_args()
        if not hasattr(self.raw_args, '__function'):
            self.main_parser.print_help()
            exit(0)

        args_dict = self.raw_args.__dict__
        name = args_dict['__function']
        replacer = args_dict['__replacer']

        args_params = {}
        for k, v in args_dict.items():
            if k.startswith('__'):
                continue
            if k in replacer:
                k = replacer[k]
            args_params[k] = v

        args = args_dict['__cls'].parse_obj(args_params)

        function = getattr(self, 'run_' + name)

        self.a = args

        self._pre_common(args)
        print(f'Starting <{name}>')
        if len(args_params) > 0:
            print('Args')
            maxlen = max(len(k) for k in args_params) if len(args_params) > 0 else -1
            for k, v in args_params.items():
                print(f'\t{k:<{maxlen+1}}: {v}')
        else:
            print('No args')

        if inspect.iscoroutinefunction(function):
            r = asyncio.run(function(args))
        else:
            r =  function(args)
        print(f'Done <{name}>')

        # cls.parse_obj(parser.parse_args().__dict__)


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
