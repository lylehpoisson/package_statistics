"""
This test module covers various functionalities of the package_statistics module, ensuring
that all components behave as expected under various scenarios. It includes unit tests for
handling HTTP errors, timeouts, and parsing data from the Debian Contents file in a simulated
gzip format. Additionally, the module tests higher-level functionalities like parsing logic
and the display of statistics in a leaderboard format.

Tests are structured to cover:
- Successful fetch of gzipped content data.
- Handling of HTTP 404 and timeout errors during fetch operations.
- Parsing of both empty and malformed gzip files.
- Display logic of the leaderboard with various numbers of items.
- An integration test that simulates the entire flow from fetching
  the gzip data to displaying the leaderboard.

Each test function within this module uses mocking to isolate functionality and ensure
reliability without the need for actual web requests or file operations.

The test suite employs pytest fixtures for common setup and tear-down operations,
and the mocker patch from the pytest-mock plugin to mock external dependencies
and methods within the module being tested.
"""
from collections import defaultdict
import gzip
import io

from click.testing import CliRunner
import pytest
from requests.exceptions import HTTPError, Timeout
from package_statistics import package_statistics

BASE_PATCH_PATH = 'package_statistics.package_statistics.'


def generate_sample_gz_data() -> io._io.BytesIO:
    """Simulate a Debian Contents file."""
    contents = """\
        /usr/share/doc/pkg1/file1 pkg1
        /usr/share/doc/pkg1/file2 pkg1,pkg2
        /usr/share/doc/pkg2/file3 pkg3
        /usr/share/doc/pkg1/file4 pkg1,pkg3
        """
    gz_bytes = io.BytesIO()
    with gzip.GzipFile(fileobj=gz_bytes, mode='wb') as gz:
        gz.write(contents.encode('utf-8'))
    gz_bytes.seek(0)
    return gz_bytes


def test_fetch_contents_file_success(mocker):
    """Mock the requests.get() call to return a mock response and test """
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    sample_data = generate_sample_gz_data()
    mock_response.raw = sample_data
    mocker.patch(BASE_PATCH_PATH + 'requests.get', return_value=mock_response)

    response = package_statistics.fetch_contents_file('amd64')
    assert response.raw == sample_data


def test_fetch_contents_file_404(mocker):
    """Simulate a 404 error"""
    mock_response = mocker.Mock(status_code=404)
    http_error = HTTPError()
    http_error.response = mock_response
    mock_response.raise_for_status.side_effect = http_error
    mocker.patch(BASE_PATCH_PATH + 'requests.get', return_value=mock_response)

    with pytest.raises(FileNotFoundError):
        package_statistics.fetch_contents_file('amd64')


def test_fetch_contents_file_timeout(mocker):
    """Simulate a timeout"""
    mocker.patch(BASE_PATCH_PATH + 'requests.get', side_effect=Timeout)

    with pytest.raises(ConnectionError):
        package_statistics.fetch_contents_file('amd64')


def test_parse_contents_file_empty(mocker):
    """Test parsing an empty gzip file"""
    empty_gz_data = io.BytesIO()
    with gzip.GzipFile(fileobj=empty_gz_data, mode='wb') as gz:
        gz.write(b"")
    empty_gz_data.seek(0)
    mock_response = mocker.Mock()
    mock_response.raw = empty_gz_data
    mocker.patch('gzip.GzipFile',
                 return_value=gzip.GzipFile(fileobj=empty_gz_data, mode='rb'))
    result = package_statistics.parse_contents_file(mock_response)
    assert result == defaultdict(
        int), f"Expected empty defaultdict, got {result}"
    assert empty_gz_data.tell() == empty_gz_data.getbuffer(
    ).nbytes, "Stream should be at the end"
    assert not empty_gz_data.read(
    ), "No more data should be available in the stream"


def test_parse_contents_file_bad_data(mocker):
    """Test parsing a gzip file with malformed content"""
    bad_gz_data = io.BytesIO()
    with gzip.GzipFile(fileobj=bad_gz_data, mode='wb') as gz:
        gz.write(b"path/to/filepkg1/name,pkg2/name")
    bad_gz_data.seek(0)
    mock_response = mocker.Mock()
    mock_response.raw = bad_gz_data
    mocker.patch('gzip.GzipFile',
                 return_value=gzip.GzipFile(fileobj=bad_gz_data, mode='rb'))
    result = package_statistics.parse_contents_file(mock_response)
    assert result == defaultdict(int)
    assert bad_gz_data.tell() == bad_gz_data.getbuffer(
    ).nbytes, "Stream should be at the end"
    assert not bad_gz_data.read(
    ), "No more data should be available in the stream"


def test_display_leaderboard_less_than_top_n(capsys):
    """Test display_leaderboard with fewer items than top_n"""
    leaderboard = defaultdict(int, {'small_pkg': 5, 'big_pkg': 20})
    package_statistics.display_leaderboard(leaderboard, top_n=5)
    captured = capsys.readouterr()
    # Using a list to circumvent getting the exact number of spaces correct
    expected_output = ['1.', 'big_pkg', '20', '2.', 'small_pkg', '5']
    assert captured.out.split(
    ) == expected_output, "Output format should match expected"


def test_display_leaderboard_exact_top_n(capsys):
    """Test leaderboard display with exactly top_n items"""
    leaderboard = defaultdict(int, {
        'small_pkg': 5,
        'big_pkg': 20,
        'med_pkg': 12
    })
    package_statistics.display_leaderboard(leaderboard, top_n=3)
    captured = capsys.readouterr()
    expected_output = [
        '1.', 'big_pkg', '20', '2.', 'med_pkg', '12', '3.', 'small_pkg', '5'
    ]
    assert captured.out.split(
    ) == expected_output, "Output should list exactly top_n matches"


def test_package_statistics_integration(mocker, capsys):
    """Integration test from fetching the file to displaying leaderboard"""
    # Simulate gzipped content as bytes
    gzipped_content = generate_sample_gz_data()
    # Set up the the mock response to return the gzipped content as bytes
    mock_response = mocker.Mock()
    mock_response.raw = gzipped_content
    mocker.patch(BASE_PATCH_PATH + 'requests.get', return_value=mock_response)

    # Mock the parsing function to return pre-defined results
    mocker.patch(BASE_PATCH_PATH + 'parse_contents_file',
                 return_value=defaultdict(int, {
                     'big_pkg': 20,
                     'small_pkg': 5
                 }))

    # Use this CliRunner object is necessary to test for this function,
    # because click expects CLI arguments to be handled
    # in a way that is different than just passing the arguments to a function.
    runner = CliRunner()
    result = runner.invoke(package_statistics.package_statistics,
                           ['amd64', '--top-n', '2'])
    expected_output = ['1.', 'big_pkg', '20', '2.', 'small_pkg', '5']
    assert result.exit_code == 0, "Command failed"
    assert result.output.split() == expected_output
