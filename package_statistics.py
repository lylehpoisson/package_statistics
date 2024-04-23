"""This is a helper file to simplify command line usage.

With this file, the user can write

python -m package_statistics.py

instead of

python -m package_statistics/package_statistics.py
"""

from package_statistics.package_statistics import package_statistics

if __name__ == "__main__":
    package_statistics()
