"""
This module provides functionality to fetch and analyze the file distribution of Debian packages
across different architectures.

It uses the Debian repository to obtain the Contents file for a specified architecture and processes
this file to display the ten packages with the most associated files. It supports multiple
architectures and includes robust error handling and logging for diagnosing issues related
to network errors or data processing.

Features:
- Fetch Contents files for architectures like amd64, arm64, etc., from the Debian repository.
- Analyze and count file associations per package.
- Display the top ten packages with the most associated files.
- Extensive error handling including logging for various potential failures
  such as network issues or missing data.

The script is intended to be used as a command-line tool, utilizing the `click` library
for command-line interactions and arguments.

Usage:
    Run the script from the command line specifying an architecture,
    e.g., `python package_statistics.py amd64`.

Requirements:
    Requires Python 3.6+, requests, and click libraries.
"""
import gzip
import io
import logging
from collections import Counter, defaultdict

import click
import requests

VALID_ARCHITECTURES = [
    'all', 'amd64', 'arm64', 'armel', 'armhf', 'i386',
    'mips64el', 'mipsel', 'ppc64el', 's390x', 'source'
]


def setup_logging(level=logging.WARNING) -> None:
    """Configure the root logger."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')


def fetch_contents_file(architecture) -> requests.Response:
    """Fetch and return the contents file for the provided architecture."""
    url = f'http://ftp.uk.debian.org/debian/dists/stable/main/Contents-{
        architecture}.gz'
    try:
        # This line retrieves the contents file. We set stream=True to help
        # parse large files
        response = requests.get(url, timeout=30, stream=True)
        # This will raise an HTTPError for bad responses
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        # We explicitly handle three different types of errors here
        if e.response.status_code == 404:
            # This error raises if the file doesn't exist on the website
            # pylint: disable=used-before-assignment
            logger.error('Contents file not found at the server: %s', e)
            # pylint: enable=used-before-assignment
            raise FileNotFoundError(
                'The requested file is missing on the server.') from None
        # This handles any other type of HTTP error
        logger.error('HTTP error occurred: %s', e)
        raise SystemError(
            'An HTTP error occurred while trying to fetch data.') from None
    # This handles any network errors, such as the user's
    # computer not being connected to WiFi.
    except requests.exceptions.RequestException as e:
        logger.error('Network error occurred: %s', e)
        raise ConnectionError('Failed to connect to the server.' +
                              'Check your internet connection.') from None


def parse_contents_file(contents_file) -> defaultdict:
    """Parse the contents file and create a dictionary that ."""
    leaderboard = defaultdict(int)
    with gzip.GzipFile(fileobj=contents_file) as gz:
        for line in io.BufferedReader(gz):
            # We split the line on whitespace and take just the final value.
            # This is the list of packages associated with the file.
            # We further split this string on commas, for the cases
            # where there is more than one package.
            packages_from_line = line.decode('utf-8').split()[-1].split(',')
            for package in packages_from_line:
                leaderboard[package] += 1
    return leaderboard


def display_leaderboard(leaderboard, top_n=10) -> None:
    """Display the top NUMBER packages with the most associated files."""
    top_packages = dict(Counter(leaderboard).most_common(top_n))
    for index, (package, num_assoc_files) in enumerate(
            list(top_packages.items())):
        print(f'{str(index + 1) + '.':<5}{package:<50}{num_assoc_files}')


@click.command()
@click.argument('architecture', type=click.Choice(VALID_ARCHITECTURES))
@click.option('--top-n', default=10, type=int,
              help='Number of top packages to display.')
def package_statistics(architecture, top_n) -> None:
    """
    This script displays the 10 packages with the most associated files for a given architecture.

       Valid inputs are:
       'all', 'amd64', 'arm64','armel',
       'armhf', 'i386','mips64el', 'mipsel',
       'ppc64el', 's390x', 'source'

    """
    # We will use a defaultdict object.
    # The keys are packages,
    # and the values are the number of files for that package.
    # For each line where a given package is referenced,
    # we increment its value by 1

    # First get the Contents file from the mirror
    response = fetch_contents_file(architecture)

    # Convert the raw binary content of the response into a BytesIO object.
    # This allows the gzip module to treat it like a file,
    # without writing it to disk.
    contents_file = io.BytesIO(response.content)

    # Now we create a leaderboard with all packages and their associated
    # number of files.
    leaderboard = parse_contents_file(contents_file)

    # Finally, we display the top n packages with the most associated files.
    # The default performance is to display the top 10.
    display_leaderboard(leaderboard, top_n)


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Application started")
    package_statistics()  # pylint: disable=no-value-for-parameter
