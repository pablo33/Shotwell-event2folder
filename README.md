## Shotwell-event2folder
Shotwell event to folder structure  

This python3 script reorders your shotwell library files into an event-oriented folder structure.  

Shotwell can get photo-files from the file-system, assigning each file to an event. But these files will remain on its source storage or once imported to shotwell they remain always at the same place.
This script will rearrange your files in your file system based on shotwell events.

The script will process shotwell DB and commit the changes.
and even more, optionally:
- it can automatically rename filenames by starting with its date identifier (YYYYMMDD_hhmmss filename.jpg)  
- it can automatically send the most recent images to a defined folder.  
- it can get the name of the filename and insert it into Shotwell Database as Title.  
- it can process and recompress diverse movie files into .mov files.  

**Dependencies:**

Python3, GExiv2 from Gi.repository, ffmpeg  

This script has been tesded with Shotwell 0.18.0 to 0.28.2 (ubuntu 14.10 to 18.04LTS).

Installing dependencies:  
I'm sure that python3 comes with your linux distribution.  
You can install the packages from the command line: GExiv2 is the "GObject-based wrapper around the Exiv2 library - introspection data"

	sudo apt-get install gir1.2-gexiv2-0.10 ffmpeg


**Usage:**
Just launch the script from command line, it will create a config file, you can edit it to fit by your needings and then run it again.

	python3 Shotwell_event2folder.py



See wiki page for further information. 
[https://github.com/pablo33/Shotwell-event2folder/wiki](https://github.com/pablo33/Shotwell-event2folder/wiki)
