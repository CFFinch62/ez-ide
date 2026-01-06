"""
Debugger Utility Functions for EZ IDE
Detects debugger capabilities and manages debugger selection
"""

import os
import subprocess
import shutil
from typing import Optional, Literal
from dataclasses import dataclass


DebuggerType = Literal['native', 'repl', 'none']


@dataclass
class DebuggerCapabilities:
    """Information about available debugger features"""
    type: DebuggerType
    supports_step: bool
    supports_breakpoints: bool
    supports_call_stack: bool
    supports_variable_inspection: bool
    version: Optional[str] = None
    description: str = ""


def get_ez_version(ez_path: str) -> Optional[str]:
    """
    Get the EZ interpreter version string
    
    Args:
        ez_path: Path to the EZ interpreter executable
        
    Returns:
        Version string (e.g., "0.39.1") or None if unable to determine
    """
    try:
        result = subprocess.run(
            [ez_path, 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Parse version from output (e.g., "EZ v0.39.1")
            output = result.stdout.strip()
            
            # Try to extract version number with regex
            import re
            # Match patterns like "v0.39.1", "0.39.1", "dev", etc.
            match = re.search(r'v?([\d.]+(?:-\w+)?|dev)', output, re.IGNORECASE)
            if match:
                return match.group(1)
            
            # Fallback: if 'v' in output, try simple split
            if 'v' in output.lower():
                parts = output.lower().split('v')
                if len(parts) > 1:
                    # Get first word after 'v'
                    version = parts[1].split()[0]
                    return version
            
            return output
            
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    return None


def test_debugserver_available(ez_path: str) -> bool:
    """
    Test if the debugserver command is available
    
    Args:
        ez_path: Path to the EZ interpreter executable
        
    Returns:
        True if debugserver command exists and can be invoked
    """
    try:
        # Try to run debugserver with a non-existent file
        # This should fail quickly but confirm the command exists
        result = subprocess.run(
            [ez_path, 'debugserver', '/tmp/__nonexistent_test__.ez'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        # If the command exists, it will fail with "Error reading file"
        # If the command doesn't exist, it will fail with unknown command
        stderr = result.stderr.lower()
        stdout = result.stdout.lower()
        
        # Command exists if we get a file error, not a command error
        if 'error reading file' in stderr or 'error reading file' in stdout:
            return True
        if 'unknown command' in stderr or 'unknown command' in stdout:
            return False
            
        # If we get here, assume it exists (better to try and fail later)
        return True
        
    except subprocess.TimeoutExpired:
        # Timeout suggests the command started (good sign)
        return True
    except (FileNotFoundError, Exception):
        return False


def detect_debugger_support(ez_path: str) -> DebuggerCapabilities:
    """
    Detect what type of debugger support is available
    
    Args:
        ez_path: Path to the EZ interpreter executable
        
    Returns:
        DebuggerCapabilities object describing available features
    """
    if not ez_path or not os.path.isfile(ez_path):
        return DebuggerCapabilities(
            type='none',
            supports_step=False,
            supports_breakpoints=False,
            supports_call_stack=False,
            supports_variable_inspection=False,
            description="EZ interpreter not found"
        )
    
    # Check if executable
    if not os.access(ez_path, os.X_OK):
        return DebuggerCapabilities(
            type='none',
            supports_step=False,
            supports_breakpoints=False,
            supports_call_stack=False,
            supports_variable_inspection=False,
            description="EZ interpreter not executable"
        )
    
    version = get_ez_version(ez_path)
    
    # Test for native debugger support
    if test_debugserver_available(ez_path):
        return DebuggerCapabilities(
            type='native',
            supports_step=True,
            supports_breakpoints=True,
            supports_call_stack=True,
            supports_variable_inspection=True,
            version=version,
            description="Native Go debugger with full features"
        )
    
    # Fall back to REPL-based debugger
    # REPL is always available if EZ is available
    return DebuggerCapabilities(
        type='repl',
        supports_step=True,
        supports_breakpoints=False,  # REPL debugger doesn't support breakpoints
        supports_call_stack=False,   # Limited call stack info
        supports_variable_inspection=True,
        version=version,
        description="REPL-based debugger with limited features"
    )


def get_debugger_display_name(debugger_type: DebuggerType) -> str:
    """
    Get a human-readable name for the debugger type
    
    Args:
        debugger_type: Type of debugger
        
    Returns:
        Display name string
    """
    names = {
        'native': 'Native Debugger',
        'repl': 'REPL Debugger',
        'none': 'No Debugger'
    }
    return names.get(debugger_type, 'Unknown')


def get_debugger_icon(debugger_type: DebuggerType) -> str:
    """
    Get an icon/emoji for the debugger type
    
    Args:
        debugger_type: Type of debugger
        
    Returns:
        Icon string (emoji)
    """
    icons = {
        'native': '🟢',  # Green circle - full features
        'repl': '🟡',    # Yellow circle - limited features
        'none': '🔴'     # Red circle - no debugger
    }
    return icons.get(debugger_type, '⚪')


def find_ez_interpreter() -> Optional[str]:
    """
    Find the EZ interpreter in the system PATH
    
    Returns:
        Path to EZ interpreter or None if not found
    """
    return shutil.which('ez')
