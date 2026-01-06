#!/usr/bin/env python3
"""
Test script for IDE debugger detection
"""

import sys
import os

# Add IDE app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from debugger_utils import (
    detect_debugger_support,
    get_ez_version,
    test_debugserver_available,
    get_debugger_display_name,
    get_debugger_icon
)

def main():
    print("Testing IDE Debugger Detection")
    print("=" * 50)
    print()
    
    # Test 1: Find EZ interpreter
    print("Test 1: Finding EZ interpreter...")
    ez_path = '../EZ/ez'
    if os.path.exists(ez_path):
        print(f"✓ Found EZ at: {ez_path}")
    else:
        print(f"✗ EZ not found at: {ez_path}")
        return
    
    print()
    
    # Test 2: Get version
    print("Test 2: Getting EZ version...")
    version = get_ez_version(ez_path)
    if version:
        print(f"✓ Version: {version}")
    else:
        print("✗ Could not get version")
    
    print()
    
    # Test 3: Test debugserver availability
    print("Test 3: Testing debugserver availability...")
    has_debugserver = test_debugserver_available(ez_path)
    if has_debugserver:
        print("✓ Debugserver is available")
    else:
        print("✗ Debugserver not available")
    
    print()
    
    # Test 4: Detect debugger capabilities
    print("Test 4: Detecting debugger capabilities...")
    caps = detect_debugger_support(ez_path)
    
    print(f"  Type: {caps.type}")
    print(f"  Icon: {get_debugger_icon(caps.type)}")
    print(f"  Name: {get_debugger_display_name(caps.type)}")
    print(f"  Version: {caps.version}")
    print(f"  Description: {caps.description}")
    print()
    print("  Capabilities:")
    print(f"    Step: {caps.supports_step}")
    print(f"    Breakpoints: {caps.supports_breakpoints}")
    print(f"    Call Stack: {caps.supports_call_stack}")
    print(f"    Variables: {caps.supports_variable_inspection}")
    
    print()
    print("=" * 50)
    
    if caps.type == 'native':
        print("✓ Native debugger detected - Full features available!")
    elif caps.type == 'repl':
        print("⚠ REPL debugger only - Limited features")
    else:
        print("✗ No debugger available")
    
    print()

if __name__ == '__main__':
    main()
