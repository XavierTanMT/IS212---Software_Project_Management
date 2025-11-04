#!/usr/bin/env python3
"""Quick script to get coverage for admin.py and reports.py"""
import subprocess
import sys

def run_coverage(module_name):
    """Run coverage for a specific module"""
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/unit',
        f'--cov=backend.api.{module_name}',
        '--cov-report=term-missing:skip-covered',
        '--cov-branch',
        '-q',
        '--tb=no',
        '--ignore=tests/unit/test_auth.py'
    ]
    
    print(f"\n{'='*80}")
    print(f"Running coverage for {module_name}...")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"Timeout running tests for {module_name}")
        return 1

if __name__ == "__main__":
    print("Getting coverage reports for admin.py and reports.py...\n")
    
    # Run for admin
    run_coverage("admin")
    
    # Run for reports
    run_coverage("reports")
    
    print("\n" + "="*80)
    print("Coverage reports complete!")
    print("="*80)
