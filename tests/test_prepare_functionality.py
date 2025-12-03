"""Tests for prepare() functionality."""

import pytest
from pydantic_autocli import AutoCLI, param


class TestPrepareFunctionality:
    
    def test_prepare_method_called(self, capsys):
        """Test that prepare() is called and receives correct arguments."""
        
        class TestCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                name: str = param("default", l="--name")
            
            def prepare(self, args):
                self.prepared_name = args.name
                print("PREPARE_CALLED")
            
            def run_test(self, args: TestArgs):
                return True
        
        cli = TestCLI()
        with pytest.raises(SystemExit):
            cli.run(["test", "test", "--name", "Alice"])
        
        captured = capsys.readouterr()
        assert "PREPARE_CALLED" in captured.out
        assert cli.prepared_name == "Alice"
    
    def test_prepare_takes_precedence_over_pre_common(self, capsys):
        """Test that prepare() is preferred over pre_common."""
        
        class TestCLI(AutoCLI):
            class CommonArgs(AutoCLI.CommonArgs):
                pass
            
            def prepare(self, args):
                print("PREPARE_CALLED")
            
            def pre_common(self, args):
                print("PRE_COMMON_CALLED")
            
            def run_test(self, args: CommonArgs):
                return True
        
        cli = TestCLI()
        with pytest.raises(SystemExit):
            cli.run(["test", "test"])
        
        captured = capsys.readouterr()
        assert "PREPARE_CALLED" in captured.out
        assert "PRE_COMMON_CALLED" not in captured.out