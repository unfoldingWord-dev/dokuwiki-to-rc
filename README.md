# dokuwiki-to-rc

__Scripts for converting resources in Dokuwiki repositories to Resource Containers.__

### Requirements

Python 3.5 (for better unicode support).

Install dependencies:

    pip install -r requirements.txt

### Testing

    python -m unittest discover -s tests

### Usage

Downloads the obs translation from the url and converts it to RC format in the output directory:

    ./execute.py convert-obs -l en -r https://github.com/Door43/d43-en -o ~/obs-en

For more information on how to use this script see [Convert OBS from DokuWiki to Gogs Resource Container](https://git.door43.org/Door43/ContentTechs/wiki/Convert-OBS-from-DokuWiki-to-Gogs-Resource-Container-in-Markdown).

### DokuWiki OBS mass migration

Three scripts for moving OBS projects off of DokuWiki (in github.com/Door43), converting to Resource Container, and pushes up to DCS (git.door43.org/DokuWiki).  The first script does downloading of OBS projects from docuWiki and converting to Resource Containers in DESTINATION_FOLDER.  This script keeps track of progress and can be started again without penalty if script dies due to communication errors.

    ./migration_dw_to_rc.py
    
The next script will check-in each resource container in DESTINATION_FOLDER into git and push up to a repo in door43.org/DokuWiki. This script keeps track of progress and can be started again without penalty if script dies due to communication errors.

    ./migration_upload.py

The final script is to show summary of all OBS migrations and uploads in DESTINATION_FOLDER.  The intent here is to see if there are any failures that are not expected.

    ./migration_summary.py
