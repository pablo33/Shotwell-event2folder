## Shotwell-event2folder
Shotwell event to folder structure  

This is a python3 script intended to reorder your shotwell library files into an event-oriented folder structure.  

Shotwell can get photo-files from any location, and you can assign each file to an event. But these files will remain on its source storage.
This script will reorder your files in your file system based on shotwell events.

This script will process shotwell DB and commit the changes.
and even more, optionally:
- you can automatically rename filenames so they starts with a date identifier (YYYYMMDD_hhmmss filename.jpg)
- you can automatically send the most recent images to a defined folder
- you can get the name of the filename and insert it into Shotwell Database.

**Dependencies:**

Python3
it has been tesded with Shotwell 0.18.0 (ubuntu 14-10)

**Usage:**
Just launch the script from command line

	$ python3 Shotwell-event2folder.py


See wiki page for further information. 
[https://github.com/pablo33/Shotwell-event2folder/wiki](https://github.com/pablo33/Shotwell-event2folder/wiki)
