#!/usr/bin/env python3
"""Entry point for running book_translator modules with uv run -m."""

import sys
from pathlib import Path

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run -m book_translator <module_number>")
        print("Available modules:")
        print("  05 - Quality evaluator")
        return
    
    module_num = sys.argv[1]
    
    if module_num == "05":
        from book_translator.quality_evaluator_05 import main
        main()
    else:
        print(f"Unknown module: {module_num}")

if __name__ == "__main__":
    main()