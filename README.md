# Debian Package File Statistics Tool

This Python tool ranks Debian packages based on the number of associated files for a given architecture. It accesses a specified architecture's Contents file from the Debian repository, parses the file, and outputs the statistics of the packages that have the most files associated with them.

## Features

- **Fetch Contents**: Retrieves Contents files for specified architectures from the Debian repository.
- **Analyze File Associations**: Counts and analyzes file associations per package.
- **Display Statistics**: Shows the top packages with the most associated files. Users can specify the number of top packages to display.

## Requirements

- Python 3.6+
- `click`
- `requests`

## Installation

First, ensure that Python 3.6 or higher is installed on your system. You can download it from [python.org](https://www.python.org/downloads/).

### Setting Up a Virtual Environment

It's recommended to use a virtual environment to manage dependencies:

```bash
# Create a virtual environment
python -m venv env

# Activate the virtual environment
# On Windows
env\Scripts\activate
# On Unix or MacOS
source env/bin/activate
```

### Installing Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the script from the command line by specifying an architecture. Here is how you can use the script:

```bash
python package_statistics.py [architecture] --top-n [number]
```

### Arguments

- `architecture`: The architecture for which you want to fetch and analyze package file statistics. 
  - Supported architectures include: `amd64`, `arm64`, `armel`, `armhf`, `i386`, `mips64el`, `mipsel`, `ppc64el`, `s390x`
  - Users can also specify `all` for packages that are architecture-independent, or `source` for source packages.
- `--top-n`: Optional. Specifies the number of top packages to display. The default is 10.

### Examples

To get the top 10 packages for the amd64 architecture, you would run:

```bash
python package_statistics.py amd64
```

To get the top 5 packages for the arm64
architecture, you would run:

```bash
python package_statistics.py arm64 --top-n 5
```

## Logging

The script uses Python's built-in `logging` module to provide info, warning, and error messages. You can adjust the logging level in the script if needed.

## Thought Process and Approach

From the outset I split the task into three parts. I worked "inside-out" so to speak: 

1. Given an already-available Contents file, display the 10 packages with the highest number of associated files.
2. Given a desired archittecture, download or otherwise access the associated Contents file from the website.
3. Allow the user to specify which type of architecture they desire.

Time and space efficiency were a priority for me in writing this code. I used a dictionary since these have O(1) inserts and reads, much faster than a list.

The main time constraints on this script are the network connection and the number of lines in the file. We read every line in the file, so if the average length of a line in the file is m, the reading takes O(nxm). However, m is small in all of the existing files, so it's basically just O(n). Our sorting is O(p logp) in the worst case, where p is the number of unique packages.

Regarding space efficiency, I wanted to make sure I didn't keep things in memory unnecessarily, so I streamed the data and I updated the dictionary line-by-line instead of keeping lines in memory. My original idea was to download the file and store it locally, then clean up at the end of runtime. The approach I ended up using is much more efficient.


One challenge was dealing with the incoming data's type. It is a gzip file, so I had to use the gzip and io libraries to handle this binary data, as opposed to a plain text file where I could have opened and read it in a simpler way.

I originally wrote the script using `argparse` instead of `click`. While debugging, I ran into a reference to `click` on stackexchange. I've never used it before, but I decided to switch to using it over argparse because of the improvements to readability and flexibility. For example, it simplified restricting the `architecture` argument to only the allowed values.

I also wrote the code originally with all of the functionality in one main function. This helped me keep my work concise and centered while I was still figuring out my approach. Once I had solidified my choice of approach, I made the code more modular, added error handling, and wrote a test suite.
