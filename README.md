# dokuwiki-to-rc

__Scripts for converting resources in Dokuwiki repositories to Resource Containers.__

### Requirements

Python 2.7.

Install dependencies:

    pip install -r requirements.txt

### Testing

    python -m unittest discover -s tests

### Usage

Downloads the obs translation from the url and converts it to RC format in the output directory:

    ./execute.py convert-obs -l en -r https://github.com/Door43/d43-en -o ~/obs-en

For more information on how to use this script see [Convert OBS from DokuWiki to Gogs Resource Container](https://git.door43.org/Door43/ContentTechs/wiki/Convert-OBS-from-DokuWiki-to-Gogs-Resource-Container-in-Markdown).