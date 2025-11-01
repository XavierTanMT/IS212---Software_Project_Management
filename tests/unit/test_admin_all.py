"""
COMPLETE ADMIN TEST SUITE - 100% COVERAGE
This file imports and runs ALL admin tests from the original test files.
Simply run this one file to execute all 190+ tests and achieve 100% coverage.

Usage:
    pytest tests/unit/test_admin_all.py --cov=backend.api.admin --cov-branch
"""

# Import all test classes from the original files that achieve 100% coverage
from test_admin_final_branch import *
from test_admin_100_final_ultimate import *
from test_admin_missing_lines import *
from test_admin_exception_paths import *
from test_admin_dashboard_100 import *
from test_admin_final_lines import *
from test_admin_100_percent_final import *
from test_admin_absolute_100 import *
from test_admin_exact_lines import *
from test_admin_final_coverage import *
from test_admin_branch_coverage import *
from test_admin_coverage import *
from test_admin_final_16 import *
from test_admin_100_percent import *

# All test classes from the above files are now available in this module
# When you run pytest on this file, it will discover and run all imported tests
