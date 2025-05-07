#!/usr/bin/env python3

from pydantic import BaseModel, Field
from pydantic_autocli import BaseCLI

class MinimalCLI(BaseCLI):
    class HelloArgs(BaseCLI.CommonArgs):
        name: str = Field("World", l="--name", s="-n")

    def run_hello(self, args):
        print(f"Hello, {args.name}!")
        return True

if __name__ == "__main__":
    cli = MinimalCLI()
    cli.run() 