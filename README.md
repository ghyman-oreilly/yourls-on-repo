# Yourls Project Repo Utility

A script for using the YOURLs API to shorten URLs in a collection of HTML or Asciidoc files, with an option for deleting generated short URLs.

## Requirements

- Python
- URL and API key for hosted YOURLs instance
- [Asciidoctor](https://asciidoctor.org)

### Setup

1. Clone the repository or download the source files:

	```bash
	git clone git@github.com:ghyman-oreilly/generate-alt-text-for-book-repo.git
	
	cd generate-alt-text-for-book-repo
	```

2. Install required dependencies:

	```bash
	pip install -r requirements.txt
	```

3. Create an `.env` file in the project directory to store your YOURLs URL and credentials:

	```bash
	echo "YOURLS_URL=your-url-here" >> .env
	echo "YOURLS_KEY=your-key-here" >> .env
	```

4. Install [Asciidoctor](https://asciidoctor.org) on your system. On mac, you can use brew to install Asciidoctor:

	```bash
	brew doctor
	```

## Usage: Shorten

To shorten URLs, run the following command:

```bash
python main.py shorten <input_path>
```

where `input_path` is one of the following: (1) the path to a directory containing HTML and Asciidoc files; (2) a space-delimited list of paths to individual HTML and Asciidoc files; or (3) the path to a JSON file containing a `files` list of relative filepaths to such files (the JSON file should be in the same folder as the files it lists).

Use the optional `--use-existing-csv` (`-c`) flag to provide the path to CSV file of URLs for the script to process. The script will skip any URLs not included in the CSV.

## Usage: Delete

```bash
python main.py delete <input_path>
```

where `input_path` is the path to a CSV file with the shortened URLs to delete in the first column. The shortened URLs will be deleted and no longer useable.
