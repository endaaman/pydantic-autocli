"""Tests for ExtraArgsMixin functionality."""

import pytest
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param, ExtraArgsMixin


class TestExtraArgsMixin:
    """Tests for positional and remainder argument handling."""

    def test_positional_args(self):
        """Test that positional arguments are captured."""

        class Args(ExtraArgsMixin, BaseModel):
            foo: str = param("default", l="--foo")

        class CLI(AutoCLI):
            quiet = True

            def run_test(self, args: Args):
                assert args.foo == "bar"
                assert args.get_positional() == ["PARAM1", "PARAM2"]
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "test", "--foo", "bar", "PARAM1", "PARAM2"])
        assert exc_info.value.code == 0

    def test_remainder_args(self):
        """Test that remainder arguments (after --) are captured."""

        class Args(ExtraArgsMixin, BaseModel):
            foo: str = param("default", l="--foo")

        class CLI(AutoCLI):
            quiet = True

            def run_test(self, args: Args):
                assert args.foo == "bar"
                assert args.get_remainder_list() == ["nested-cmd", "--param", "123"]
                assert args.get_remainder() == "nested-cmd --param 123"
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "test", "--foo", "bar", "--", "nested-cmd", "--param", "123"])
        assert exc_info.value.code == 0

    def test_positional_and_remainder(self):
        """Test both positional and remainder arguments together."""

        class Args(ExtraArgsMixin, BaseModel):
            foo: str = param("default", l="--foo")

        class CLI(AutoCLI):
            quiet = True

            def run_test(self, args: Args):
                assert args.foo == "bar"
                assert args.get_positional() == ["PARAM1", "PARAM2"]
                assert args.get_remainder_list() == ["THIS", "IS", "DOUBLE", "DASH"]
                assert args.get_remainder() == "THIS IS DOUBLE DASH"
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "test", "--foo", "bar", "PARAM1", "PARAM2", "--", "THIS", "IS", "DOUBLE", "DASH"])
        assert exc_info.value.code == 0

    def test_empty_positional_and_remainder(self):
        """Test with no positional or remainder arguments."""

        class Args(ExtraArgsMixin, BaseModel):
            foo: str = param("default", l="--foo")

        class CLI(AutoCLI):
            quiet = True

            def run_test(self, args: Args):
                assert args.get_positional() == []
                assert args.get_remainder_list() == []
                assert args.get_remainder() == ""
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "test", "--foo", "bar"])
        assert exc_info.value.code == 0

    def test_only_double_dash(self):
        """Test with only -- and no remainder."""

        class Args(ExtraArgsMixin, BaseModel):
            foo: str = param("default", l="--foo")

        class CLI(AutoCLI):
            quiet = True

            def run_test(self, args: Args):
                assert args.get_positional() == []
                assert args.get_remainder_list() == []
                assert args.get_remainder() == ""
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "test", "--foo", "bar", "--"])
        assert exc_info.value.code == 0

    def test_without_mixin_no_methods(self):
        """Test that args without ExtraArgsMixin don't have the methods."""

        class Args(BaseModel):
            foo: str = param("default", l="--foo")

        class CLI(AutoCLI):
            quiet = True

            def run_test(self, args: Args):
                assert not hasattr(args, "get_positional")
                assert not hasattr(args, "get_remainder")
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "test", "--foo", "bar", "PARAM1", "--", "extra"])
        assert exc_info.value.code == 0

    def test_remainder_preserves_dashes_in_args(self):
        """Test that dashes in remainder arguments are preserved."""

        class Args(ExtraArgsMixin, BaseModel):
            pass

        class CLI(AutoCLI):
            quiet = True

            def run_test(self, args: Args):
                assert args.get_remainder_list() == ["--verbose", "-v", "--config=test.json"]
                assert args.get_remainder() == "--verbose -v --config=test.json"
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "test", "--", "--verbose", "-v", "--config=test.json"])
        assert exc_info.value.code == 0

    def test_default_command_with_extra_args(self):
        """Test ExtraArgsMixin with default command (remainder only, no positional)."""

        class DefaultArgs(ExtraArgsMixin, BaseModel):
            foo: str = param("default", l="--foo")

        class CLI(AutoCLI):
            quiet = True

            def run_default(self, args: DefaultArgs):
                assert args.foo == "bar"
                assert args.get_remainder() == "extra args"
                return True

        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "--foo", "bar", "--", "extra", "args"])
        assert exc_info.value.code == 0

    def test_default_command_positional_always_empty(self):
        """Test that default command always has empty positional args (to avoid ambiguity with subcommands)."""

        class DefaultArgs(ExtraArgsMixin, BaseModel):
            pass

        class OtherArgs(ExtraArgsMixin, BaseModel):
            pass

        executed_command = []

        class CLI(AutoCLI):
            quiet = True

            def run_default(self, args: DefaultArgs):
                executed_command.append("default")
                # Positional should always be empty for default command
                assert args.get_positional() == []
                assert args.get_remainder() == "after double dash"
                return True

            def run_other(self, args: OtherArgs):
                executed_command.append("other")
                # Subcommand can have positional args
                assert args.get_positional() == ["POS1", "POS2"]
                assert args.get_remainder() == "remainder here"
                return True

        # Test default command
        cli = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli.run(["prog", "--", "after", "double", "dash"])
        assert exc_info.value.code == 0
        assert executed_command == ["default"]

        # Test other subcommand with positional args
        executed_command.clear()
        cli2 = CLI()
        with pytest.raises(SystemExit) as exc_info:
            cli2.run(["prog", "other", "POS1", "POS2", "--", "remainder", "here"])
        assert exc_info.value.code == 0
        assert executed_command == ["other"]
