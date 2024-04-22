"""
This module provides functionality to fetch and analyze the file distribution of Debian packages
across different architectures.

It uses the Debian repository to obtain the Contents file for a specified architecture and processes
this file to display the ten packages with the most associated files. It supports multiple
architectures and includes robust error handling and logging for diagnosing issues related
to network errors or data processing. User can also specify a value different than ten for
the number of top packages displayed.

Features:
- Fetch Contents files for architectures like amd64, arm64, etc., from the Debian repository.
- Analyze and count file associations per package.
- Display the top ten (or other user=specified number) packages with the most associated files.
- Extensive error handling including logging for various potential failures
  such as network issues or missing data.

The script is intended to be used as a command-line tool, utilizing the `click` library
for command-line interactions and arguments.

Usage:
    Run the script from the command line specifying an architecture,
    e.g., `python package_statistics/package_statistics.py amd64`.

Requirements:
    Requires Python 3.6+, requests, and click libraries.
"""
import gzip
import io
import logging
from collections import Counter, defaultdict

import click  # Used for creating command-line interfaces
import requests  # Used for HTTP requests

# List of valid architectures for which a Debian contents file can be fetched,
# including `all` and `source`
VALID_ARCHITECTURES = [
    'all', 'amd64', 'arm64', 'armel', 'armhf', 'i386',
    'mips64el', 'mipsel', 'ppc64el', 's390x', 'source'
]

# Configure basic logger at the module level
logger = logging.getLogger(__name__)


def setup_logging(level=logging.WARNING) -> None:
    """Set up the logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')


def fetch_contents_file(architecture) -> requests.Response:
    """Fetch and return the Contents file from the Debian repository for the provided architecture."""
    url = f'http://ftp.uk.debian.org/debian/dists/stable/main/Contents-{
        architecture}.gz'
    try:
        # This line retrieves the contents file. We set stream=True to help
        # parse large files.
        response = requests.get(url, timeout=30, stream=True)
        # Check for HTTP errors.
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        # We explicitly handle three different types of errors here
        if e.response.status_code == 404:
            # This error raises if the file doesn't exist on the website
            logger.error('Contents file not found at the server: %s', e)
            raise FileNotFoundError(
                'The requested file is missing on the server.') from None
        # This handles any other type of HTTP error
        logger.error('HTTP error occurred: %s', e)
        raise SystemError(
            'An HTTP error occurred while trying to fetch data.') from None
    # This handles any network errors, such as the user's
    # computer not being connected to WiFi
    except requests.exceptions.RequestException as e:
        logger.error('Network error occurred: %s', e)
        raise ConnectionError('Failed to connect to the server.' +
                              'Check your internet connection.') from None


def parse_contents_file(contents_file) -> defaultdict:
    """Parse the contents file and create a dictionary that ."""
    # We use a defaultdict object, which defines default behavior
    # for any new key added to the dictionary.
    # In this case, if we tell the dictionary to increment the value of
    # a key that doesn't exist, it creates an item with the specified key
    # and a value of 0 (since we specified int), and increments the value
    # from 0 to 1.
    leaderboard = defaultdict(int)
    with gzip.GzipFile(fileobj=contents_file) as gz:
        for line_bytes in io.BufferedReader(gz):
            # We split the line on whitespace and take just the final value.
            # This is the list of packages associated with the file.
            # We further split this string on commas, for the cases
            # where there is more than one package.
            split_line = line_bytes.decode('utf-8').strip().split()
            # Check if line matches expected format. This handles
            # any lines that are missing spaces.
            # Known bug: does not handle lines where there is a space
            # in the filename, but no space between the filename
            # and the package name(s).
            # I have seen no real-life examples of this behavior,
            # but I wanted to document it for posterity.
            # I was originally going to use a regex, but the fact that
            # files can have spaces in their names combined with
            # the fact that there can be as few as 1 spaces
            # between the filename and package name(s) makes it overly complicated,
            # if at all possible.
            if len(split_line) < 2:
                logger.warning('Skipping malformed line: %s', split_line)
                continue  # Skip to the next line
            packages_from_line = split_line[-1].split(',')
            for package in packages_from_line:
                # This is where that defaultdict behavior
                # is used. If there is no key called package
                # in the dictionary, one is created and given
                # a value of 0. Then it is immediately incremented
                # by the `+= 1``
                leaderboard[package] += 1
    return leaderboard


def display_leaderboard(leaderboard, top_n=10) -> None:
    """Display the top NUMBER packages with the most associated files."""
    # Here we use the Counter object to identify the keys with the
    # highest values in our defaultdict. We make a dictionary out of those
    # keys and their values, then print an ordered list in the
    # required format
    top_packages = dict(Counter(leaderboard).most_common(top_n))
    for index, (package, num_assoc_files) in enumerate(
            list(top_packages.items())):
        # The ':<5' and ':<50' are used for aligning the result
        # into columns. If we just used spaces, the line lengths
        # would vary depending on the package name and the index
        print(f'{str(index + 1) + '.':<5}{package:<50}{num_assoc_files}')

# Initiate click for this function. It will expect CLI inputs


@click.command()
# CLI argument for the architecture. Only accepts values from
# our VALID_ARCHIECTURES list. If input is not in that list,
# the user is given a list of valid inputs..
@click.argument('architecture', type=click.Choice(VALID_ARCHITECTURES))
# Added functionality to optionally specify the number of top packages displayed.
# Default value is 10, but it can take any integer.For any value less than 1,
# zero results are shown.
@click.option('--top-n', default=10, show_default=True, type=int,
              help='Number of top packages to display.')
def package_statistics(architecture, top_n) -> None:
    """
    This script displays the 10 (or top_n if specified) packages
    with the most associated files for a given architecture.

       Valid inputs are:
       'all', 'amd64', 'arm64','armel',
       'armhf', 'i386','mips64el', 'mipsel',
       'ppc64el', 's390x', 'source'

    """
    # Including this allows the user to specify a different logging level
    setup_logging()
    logger.info('Application started')
    # First get the Contents file from the Debian repo
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
    package_statistics()