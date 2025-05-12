import click
import csv
from dotenv import load_dotenv
import json
import logging
from pathlib import Path
import sys
import time

from helpers import get_and_validate_env
from delete_urls import delete_urls
from shorten_urls import find_urls, shorten_urls, update_file_content


load_dotenv()

YOURLS_URL = get_and_validate_env("YOURLS_URL") # load and validate here, so any errors occur early
YOURLS_KEY = get_and_validate_env("YOURLS_KEY")


def setup_logging():
    # Configure root logger (applies to all modules)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    handler.setLevel(logging.INFO)

    if not root_logger.handlers:
        root_logger.addHandler(handler)

    # Reduce spamming from other libraries
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def read_json_file_list(
        filepath: Path,
        permitted_filetypes: list[str] = [".html", ".adoc", ".asciidoc"]
        ) -> list[Path]:
    """
    Get list of files from a `file` list in a JSON file.

    Expects `file` list to contain strings representing relative paths
    to files in the same directory as the JSON file.
    """
    filepath = Path(filepath) 
    project_dir = filepath.parent

    filepaths = []

    try:
        json_data = json.loads(filepath.read_text(encoding='utf-8'))
    except Exception as e:
        raise Exception(f"Failed to read or parse JSON file: {e}")

    for rel_path in json_data.get("files", []):
        abs_path = (project_dir / rel_path).resolve()
        if abs_path.exists() and abs_path.is_file() and abs_path.suffix.lower() in permitted_filetypes:
            filepaths.append(abs_path)

    if not filepaths:
        raise ValueError("No files found in the JSON `file` list.")

    return filepaths


def resolve_input_paths(
        inputs: list, 
        permitted_filetypes: list[str] = [".html", ".adoc", ".asciidoc"]
    ) -> list[Path]:
    """
    Takes in a list of input paths and resolves them into a list of Path objects.
    Supports:
    - A folder path containing files
    - A path to a .json file with a `files` key
    - One or more individual file paths
    """
    resolved_files = []

    json_filepath = next(
        (Path(i) for i in inputs if Path(i).is_file() and Path(i).suffix.lower() == '.json'),
        ''
    )

    # handle JSON input
    if json_filepath:
        resolved_files = read_json_file_list(Path(json_filepath))
        return resolved_files

    for input_str in inputs:
        input_path = Path(input_str)

        # handle directory input
        if input_path.is_dir():
            resolved_files.extend(
                f for f in input_path.glob("*") if f.exists() and f.is_file() and f.suffix.lower() in permitted_filetypes
            )

        # handle filepaths input
        elif input_path.is_file():
            if input_path.suffix.lower() in permitted_filetypes:
                resolved_files.append(input_path)
            else:
                raise ValueError(
                    f"If passing a list of filepaths, all files must be of types: {', '.join(permitted_filetypes)}"
                    )
        
        else:
            raise FileNotFoundError(f"Input path does not exist: {input_path}")

    return resolved_files


def process_csv_input(csv_filepath: Path) -> list[str]:
    first_column_values = []
    
    with open(csv_filepath, mode='r', newline='', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            if row:  # Check if the row is not empty
                first_column_values.append(row[0])  # Add the first column value to the list
    
    return first_column_values


@click.group()
def cli():
    """Utility for working with YOURLs in a project repo."""
    setup_logging()


@cli.command(help="""
Provide one of the following:
(1) path to a directory containing HTML or Asciidoc files,
(2) space-delimited paths to such files,
(3) path to a JSON file with a 'files' list of such files.
""")
@click.argument("input_path", nargs=-1)
@click.option("--use-existing-csv", "-c", default=None, help="Provide an optional existing CSV file of URLs for the script to process. The script will skip any URLs not included in the CSV.")
def shorten(input_path, use_existing_csv = None):
    if not input_path:
        raise click.UsageError('`input_path` argument is required.')

    filepaths = resolve_input_paths(input_path)
   
    if use_existing_csv:
        csv_filepath = Path(use_existing_csv)
        if not csv_filepath.is_file() or csv_filepath.suffix.lower() != '.csv':
            raise ValueError('If --use-existing-csv option is invoked, path to a valid CSV file must be provided.')
        url_input_list = process_csv_input(csv_filepath)
    else:
        url_input_list = None

    click.echo("Warning: Please make sure to run this script on a clean Git repo.")
    click.echo("This script will replace *ALL* URLs, including those within code blocks and inline code. May not be appropriate for some repos. Use with caution and review changes carefully!")
    
    filelist = '\n'.join([str(f) for f in filepaths])
    click.echo(f"Files to be processed include:\n{filelist}")
    
    if not click.prompt("Do you wish to continue? (y/n)").strip().lower() in ['y', 'yes']:
        click.echo("Exiting.")
        sys.exit(0)
    
    click.echo("\nProgress: Script is running. This may take up to several minutes to complete. Please wait...\n")

    if url_input_list is not None:
        file_urls, all_urls = find_urls(filepaths, url_input_list)
    else:
        file_urls, all_urls = find_urls(filepaths)


    review_filepath = Path.cwd() / f"review_file_{int(time.time())}.csv"

    with open(review_filepath, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        for url in all_urls:
            csv_writer.writerow([url])
    
    click.echo(f"\nURLs to be shortened have been saved to {review_filepath}. Please review.")
    click.echo("Note that the script will ignore changes you make to the review file at this time. If you wish to make changes, please rerun the script with the modified review file as your --use-existing-csv input.")

    if not click.prompt("Do you wish to continue? (y/n)").strip().lower() in ['y', 'yes']:
        click.echo("Exiting.")
        sys.exit(0)

    click.echo("\nContinuing. This may take up to several minutes to complete. Please wait...\n")

    filepaths_w_shortened_urls = shorten_urls(file_urls, all_urls, YOURLS_URL, YOURLS_KEY)

    for filepath, urls in filepaths_w_shortened_urls.items():
        update_file_content(filepath, urls)

    output_csv = Path.cwd() / f"output_{int(time.time())}.csv"

    with open(output_csv, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['File', 'Original URL', 'Shortened URL'])

        for filepath, urls in filepaths_w_shortened_urls.items():
            for original_url, shortened_url in urls:
                csv_writer.writerow([filepath, original_url, shortened_url])

    click.echo(f"\nScript completed. Results saved to {output_csv}")


@cli.command(help="""
Provide a path to a CSV file of shortened URLs to delete.
""")
@click.argument("input_path", type=click.Path(exists=True))
def delete(input_path):
    
    csv_filepath = Path(input_path)

    if not csv_filepath.is_file() and csv_filepath.suffix.lower() == '.csv':
        raise ValueError('Path to a valid CSV file must be provided.')
    
    url_input_list = process_csv_input(csv_filepath)

    click.echo("The following short URLs will be deleted and unusable:")
    
    for url in url_input_list:
        click.echo(url)

    if not click.prompt('Do you wish to continue? (y/n)').strip().lower() in ['y', 'yes']:
        click.echo("Exiting.")
        sys.exit(0)

    results = delete_urls(url_input_list, YOURLS_URL, YOURLS_KEY)

    click.echo('Script complete.')

if __name__ == '__main__':
    cli()