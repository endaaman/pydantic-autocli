import os
import sys
import re
from string import capwords
import inspect
import asyncio
from typing import Callable, Type, get_type_hints
import argparse

from pydantic import BaseModel, Field


def snake_to_pascal(s):
    r = capwords(s.replace('_',' '))
    r = r.replace(' ','')
    return r

def snake_to_kebab(s):
    return s.replace('_','-')


primitive2type = {
    'string': str,
    'number': float,
    'integer': int,
}

VERBOSE = False

def register_cls_to_parser(cls, parser):
    if VERBOSE:
        print(cls)
    replacer = {}
    for key, prop in cls.schema()['properties'].items():
        if VERBOSE:
            print('Name: ', key)
            print('Prop:', prop)

        snake_key = '--' + key.replace('_', '-')
        if 'l' in prop:
            snake_key = prop['l']
            replacer[snake_key[2:].replace('-', '_')] = key

        args = [snake_key]
        if 's' in prop:
            args.append(prop['s'])

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

        if 'choices' in prop:
            kwargs['choices'] = prop['choices']

        if VERBOSE:
            print('args', args)
            print('kwargs', kwargs)
            print()

        parser.add_argument(*args, **kwargs)
    return replacer


class BaseCLI:
    def with_suffix(self, base, suffix):
        if suffix:
            return f'{base}_{suffix}'
        return base

    def with_wrote(self, s):
        print('wrote', s)
        return s

    class CommonArgs(BaseModel):
        pass

    def _pre_common(self, a):
        pre_common = getattr(self, 'pre_common', None)
        if pre_common:
            pre_common(a)

    def wrap_runner(self, key):
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

    def _get_args_class_for_method(self, method_name):
        """Get the appropriate args class for a method based on type annotation or naming convention"""
        method = getattr(self, method_name)
        
        # Priority 1: Check for type annotation
        type_hints = get_type_hints(method)
        
        # Check for type annotation on the second parameter (first is 'self')
        params = list(inspect.signature(method).parameters.values())
        if len(params) > 1 and params[1].name in type_hints:
            arg_type = type_hints[params[1].name]
            if inspect.isclass(arg_type) and issubclass(arg_type, BaseModel):
                return arg_type
        
        # Priority 2: Look for a class named according to convention
        command_name = re.match(r'^run_(.*)$', method_name)[1]
        args_class_name = snake_to_pascal(command_name) + 'Args'
        args_class = getattr(self.__class__, args_class_name, None)
        if args_class is not None:
            return args_class
        
        # Priority 3: Fall back to CommonArgs
        return self.default_args_class

    def __init__(self):
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
    class CLI(BaseCLI):
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
