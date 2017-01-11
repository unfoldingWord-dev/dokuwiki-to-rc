# dokuwiki-to-rc

__Scripts for converting resources in Dokuwiki repositories to Resource Containers.__

### Requirements

You should use Python 3.5.

Install dependencies:

    pip install -r requirements.txt

### Testing

    python -m unittest discover -s tests

### Usage

Downloads the obs translation from the url and converts it to RC format in the output directory:

    ./execute.py convert-obs -l en -r https://git.door43.org/Door43/en-obs -o myobs
