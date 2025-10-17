#!/usr/bin/env python3
"""
Test runner script for LG-Urban test suite.
Provides convenient commands to run different test categories.
"""
import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False
    else:
        print(f"\n✅ {description} passed")
        return True


def main():
    parser = argparse.ArgumentParser(description="Run LG-Urban tests")
    parser.add_argument(
        "category",
        choices=["unit", "integration", "e2e", "all"],
        help="Test category to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true", 
        help="Run with coverage reporting"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend(["--cov=backend", "--cov-report=html", "--cov-report=term"])
    
    # Add test directory based on category
    if args.category == "unit":
        cmd.append("tests/unit/")
        description = "Unit Tests"
    elif args.category == "integration":
        cmd.append("tests/integration/")
        description = "Integration Tests"
    elif args.category == "e2e":
        cmd.append("tests/e2e/")
        description = "End-to-End Tests"
    elif args.category == "all":
        cmd.append("tests/")
        description = "All Tests"
    
    # Run the tests
    success = run_command(cmd, description)
    
    if success:
        print(f"\n🎉 {description} completed successfully!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print(f"\n💥 {description} failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
