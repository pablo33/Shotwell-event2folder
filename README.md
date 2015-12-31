## Shotwell-event2folder
Shotwell event to folder structure  

This is a python3 script intended to reorder your shotwell library files to an event-oriented folder structure.  

Shotwell can get photo-files from any location, and you can assign each file to an event. But these files will remain on its source storage.
This script will reorder your files in your file system based on shotwell events.

This script will process shotwell DB and make the changes.

**Dependencies:**

it has been tesded with Shotwell 0.18.0 (ubuntu 14-10)

**Usage:**
Just launch the script from command line

_$ python3 Shotwell-event2folder.py_



_TODO_: 

OK - Run on "Dummy mode"  
OK - Add a fulldate identifier on filenames   (optional)  
OK - Clean empty folders  
OK - Leave on its place the last imported nnKbs of data.  
OK - an user config file and an user config path  
OK - Move Thashed files to a specific Trash folder  

(coding) Reorganize main loop and get all the entries in one loop usin Joint in SQL.
Check that current date in filename is correct, and modify in case it is not correct. (because date in file has been modified)  
