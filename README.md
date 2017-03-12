## Shotwell-event2folder
Shotwell event to folder structure  

This is a python3 script intended to reorder your shotwell library files into an event-oriented folder structure.  

Shotwell can get photo-files from the file-system, and you can assign each file to an event. But these files will remain on its source storage or once imported to shotwell they remain always at the same place.
This script will reorder your files in your file system based on shotwell events.

This script will process shotwell DB and commit the changes.
and even more, optionally:
- you can automatically rename filenames so they starts with a date identifier (YYYYMMDD_hhmmss filename.jpg)
- you can automatically send the most recent images to a defined folder.
- you can get the name of the filename and insert it into Shotwell Database as Title.

**Dependencies:**

Python3

This script has been tesded with Shotwell 0.18.0 to 0.24.2 (ubuntu 14.10 to 16.10).

**Usage:**
Just launch the script from command line, this will create a config file, edit to fit your needings and run it again.

	$ python3 Shotwell_event2folder.py


See wiki page for further information. 
[https://github.com/pablo33/Shotwell-event2folder/wiki](https://github.com/pablo33/Shotwell-event2folder/wiki)
