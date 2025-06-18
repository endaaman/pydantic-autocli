"""Tests for prepare() functionality and pre_common deprecation."""

import warnings
import pytest
from pydantic import BaseModel
from pydantic_autocli import AutoCLI, param


class TestPrepareFunctionality:
    
    def test_prepare_method_called(self, capsys):
        """Test that prepare() method is called before command execution."""
        
        class TestCLI(AutoCLI):
            class CommonArgs(AutoCLI.CommonArgs):
                verbose: bool = param(False)
            
            def prepare(self, args):
                print("PREPARE_CALLED")
            
            def run_test(self, args: CommonArgs):
                print("COMMAND_EXECUTED")
                return True
        
        cli = TestCLI()
        with pytest.raises(SystemExit) as excinfo:
            cli.run(["test", "test"])
        assert excinfo.value.code == 0
        
        captured = capsys.readouterr()
        assert "PREPARE_CALLED" in captured.out
        assert "COMMAND_EXECUTED" in captured.out
    
    def test_pre_common_deprecation_warning(self):
        """Test that pre_common usage shows deprecation warning."""
        
        class TestCLI(AutoCLI):
            class CommonArgs(AutoCLI.CommonArgs):
                pass
            
            def pre_common(self, args):
                pass
            
            def run_test(self, args: CommonArgs):
                return True
        
        cli = TestCLI()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with pytest.raises(SystemExit):
                cli.run(["test", "test"])
            
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "pre_common() is deprecated" in str(w[0].message)
            assert "Use prepare() instead" in str(w[0].message)
    
    def test_prepare_takes_precedence_over_pre_common(self, capsys):
        """Test that prepare() is called instead of pre_common when both exist."""
        
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
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with pytest.raises(SystemExit):
                cli.run(["test", "test"])
            
            captured = capsys.readouterr()
            assert "PREPARE_CALLED" in captured.out
            assert "PRE_COMMON_CALLED" not in captured.out
            # No deprecation warning should be shown when prepare() exists
            assert len(w) == 0
    
    def test_no_prepare_or_pre_common(self):
        """Test that no errors occur when neither prepare() nor pre_common() exist."""
        
        class TestCLI(AutoCLI):
            class CommonArgs(AutoCLI.CommonArgs):
                pass
            
            def run_test(self, args: CommonArgs):
                return True
        
        cli = TestCLI()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with pytest.raises(SystemExit):
                cli.run(["test", "test"])
            
            # No warnings should be generated
            assert len(w) == 0
    
    def test_prepare_receives_correct_args(self):
        """Test that prepare() receives the parsed arguments correctly."""
        
        class TestCLI(AutoCLI):
            class TestArgs(AutoCLI.CommonArgs):
                name: str = param("default", l="--name")
                count: int = param(1, l="--count")
            
            def prepare(self, args):
                self.prepared_args = args
            
            def run_test(self, args: TestArgs):
                return True
        
        cli = TestCLI()
        with pytest.raises(SystemExit):
            cli.run(["test", "test", "--name", "Alice", "--count", "5"])
        
        assert hasattr(cli, 'prepared_args')
        assert cli.prepared_args.name == "Alice"
        assert cli.prepared_args.count == 5
    
    def test_prepare_can_modify_shared_state(self, capsys):
        """Test that prepare() can set up shared state for commands."""
        
        class TestCLI(AutoCLI):
            class CommonArgs(AutoCLI.CommonArgs):
                debug: bool = param(False, l="--debug")
            
            def prepare(self, args):
                self.debug_mode = args.debug
                if self.debug_mode:
                    print("DEBUG MODE ENABLED")
            
            def run_test(self, args: CommonArgs):
                if self.debug_mode:
                    print("Running in debug mode")
                return True
        
        cli = TestCLI()
        with pytest.raises(SystemExit):
            cli.run(["test", "test", "--debug"])
        
        captured = capsys.readouterr()
        assert "DEBUG MODE ENABLED" in captured.out
        assert "Running in debug mode" in captured.out
        assert cli.debug_mode is True