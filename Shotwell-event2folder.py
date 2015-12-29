#!/usr/bin/python3

import sqlite3, os, sys, shutil, logging, re
from datetime import datetime

# ------- Set Variables ---------

DBpath = os.path.join(os.getenv('HOME'),".local/share/shotwell/data/photo.db")


# ------ utils --------
def itemcheck(a):
	if os.path.isfile(a):
		return 'file'
	if os.path.isdir(a):
		return 'folder'
	if os.path.islink(a):
		return 'link'
	return ""


# Load user config:
# Getting user folder to place log files....
userpath = os.path.join(os.getenv('HOME'),".Shotwell-event2folder")
userfileconfig = os.path.join(userpath,"Shotevent2folder_cfg.py")
if itemcheck (userpath) != "folder":
	os.makedirs(userpath)

if itemcheck (userfileconfig) == "file":
	print ("Loading user configuration....")
	sys.path.append(userpath)
	import Shotevent2folder_cfg
else:
	print ("There isn't an user config file: " + userfileconfig)
	# Create a new config file
	f = open(userfileconfig,"w")
	f.write ('''
# Shotwell-event2folder Config file.
# This options can be overriden by entering a command line options
# This is a python file. Be careful and see the sintaxt.

librarymainpath = "%(home)s/Pictures"
dummy = False # Dummy mode. True will not perform any changes to DB or File structure 
insertdateinfilename = True  #  Filenames will be renamed with starting with a full-date expression
clearfolders = True  # Delete empty folders
leaveamount = 0 # 2500000000  > this would be 2,5Gb in Kbs#  Leave this amount of KB in place. This affects to the more recent imported images and with the more recent date. use 0 to disable and move all the pictures.
'''%{'home':os.getenv('HOME')}
	)
	f.close()
	print ("Your user config file has been created at:", userfileconfig)
	print ("Please customize by yourself before run this software again.")
	print ("This software is will try to open it with a text editor (gedit).")
	os.system ("gedit " + userfileconfig)
	exit()

# Getting variables.
librarymainpath = Shotevent2folder_cfg.librarymainpath
dummy = Shotevent2folder_cfg.dummy  # Dummy mode. True will not perform any changes to DB or File structure 
insertdateinfilename = Shotevent2folder_cfg.insertdateinfilename  #  Filenames will be renamed with starting with a full-date expression
clearfolders = Shotevent2folder_cfg.clearfolders  # Delete empty folders
leaveamount = Shotevent2folder_cfg.leaveamount  #  Leave this amount of KB in place. This affects to the more recent imported images and with the more recent date. use 0 to disable and move all the pictures.


# ===============================
# The logging module.
# ===============================
loginlevel = 'DEBUG'
logpath = './'
logging_file = os.path.join(logpath, 'Shotwell-event2folder.log')


# Getting current date and time
now = datetime.now()
today = "/".join([str(now.day), str(now.month), str(now.year)])
tohour = ":".join([str(now.hour), str(now.minute)])

print ("Loginlevel:", loginlevel)
logging.basicConfig(
	level = loginlevel,
	format = '%(asctime)s : %(levelname)s : %(message)s',
	filename = logging_file,
	filemode = 'w'  # a = add
)
print ("logging to:", logging_file)

# initializing vars

dummymsg = ''
if dummy == True:
	dummymsg = '(dummy mode)'

foldercollection = set ()
datelimit2move_import = datetime.now()
datelimit2move_exposure = datetime.now()


# Check if Shotwell DB is present
if itemcheck (DBpath) != "file":
	infomsg = 'Shotwell Database is not present, this script is intended to work on a Shotwell Database located at:\n' + DBpath
	print (infomsg) ; logging.info (infomsg)
	exit()

dbconnection = sqlite3.connect (DBpath)

# Set the last Kb of imported data and stablishing the limit to move if any.
if leaveamount > 0 :
	foundlimit = False
	dballitemscursor = dbconnection.cursor ()
	dballitemscursor.execute ("SELECT filesize,import_id,exposure_time,'PhotoTable' as tabla FROM PhotoTable UNION SELECT filesize,import_id,exposure_time,'VideoTable' as tabla FROM VideoTable ORDER BY import_id DESC, exposure_time DESC")
	acumulatedKb = 0
	for entry in dballitemscursor:
		acumulatedKb = acumulatedKb + entry[0]
		if acumulatedKb > leaveamount :
			foundlimit = True
			break
	if foundlimit == True :
		datelimit2move_import   = datetime.fromtimestamp(entry[1])
		datelimit2move_exposure = datetime.fromtimestamp(entry[2])
		logging.info ("Amount limit: import_id:" + str(entry[1]) + "exposure_time:" + str( entry[2]))
		print (datelimit2move_import, datelimit2move_exposure)
	else:
		leaveamount = 0  # all pictures will be moved
	dballitemscursor.close()


dbeventcursor = dbconnection.cursor ()
# Inserting a Trash event
dbeventcursor.execute("INSERT INTO EventTable (id, name) VALUES (-1,'Trash')")
# event cursor
dbeventcursor.execute('SELECT id,name FROM EventTable')
for e in dbeventcursor:
	# Retrieve event data
	eventid, eventname = e
	eventavgtime = dbconnection.execute('SELECT AVG(exposure_time) FROM PhotoTable WHERE event_id = ? and exposure_time is not null',(eventid,)).fetchone()[0]  # Average
	if eventavgtime == None:
		logging.debug ('\tEvent %s has no photos (is empty). Skipping.' % eventid)
		continue
	eventtime = datetime.fromtimestamp(eventavgtime)
	#  ....TODO.... Check for name inconsistences, and change not allowed characters.
	if eventname == None : eventname = ""
	print ("\nProcessing event:(" + str(eventid) + ") " + eventname)
	logging.info ('')
	logging.info ('## Moving event nº' + str(eventid) + ", " + eventname + "(" + str(eventtime) + ")")

	# defining event path:
	
	if eventid == -1 :
		eventpath = os.path.join(librarymainpath, eventname)
	else:
		eventpath = os.path.join(librarymainpath,eventtime.strftime('%Y'),eventtime.strftime('%Y-%m-%d ') + eventname)
		
	eventpath = eventpath.strip()
	logging.info ("path for the event: " + eventpath)

	# retrieving event's photos and videos
	dbtablecursor = dbconnection.cursor()
	dbtablecursor.execute("SELECT id, filename, title, exposure_time, import_id, 'PhotoTable' AS DBTable FROM PhotoTable WHERE event_id = ? UNION SELECT id, filename, title, exposure_time, import_id, 'VideoTable' AS DBTable FROM VideoTable WHERE event_id = ?",(eventid, eventid))

	# Process each file
	for p in dbtablecursor:
		photoid, photopath, phototitle, phototimestamp, import_id, DBTable = p
		photodate = datetime.fromtimestamp(phototimestamp)
		photodateimport = datetime.fromtimestamp(import_id)

		# Check if file is in the last Kb to 
		if leaveamount > 0 and datelimit2move_import <= photodateimport and datelimit2move_exposure <= photodate : 
			logging.info ("File is in the gap of the %s Kbs of the last imported pictures that you don't want to move" % leaveamount)
			print ("\tThis file is in the gap of the amount of the last imported Pictures that you don't want to move.")
			continue

		# adding a folder to scan
		foldercollection.add (os.path.dirname(photopath))	
		logging.debug (os.path.dirname(photopath) + ' added to folders list')
		# defining filename
		photofilename = os.path.basename(photopath)
		infomsg = "Processing(" + str(photoid) + ") filename: " + photofilename
		print (infomsg) ; logging.info (infomsg)

		photonewfilename = photofilename
		# checking a starting date in filename
		if insertdateinfilename == True and phototimestamp != None:
			expr = '[12]\d{3}[01]\d[0-3]\d[.-_ ]?[012]\d[0-5]\d[0-5]\d'
			mo = re.search (expr, photofilename)
			try:
				mo.group()
			except:
				logging.debug ("Fulldate expression was not found in %s" % photofilename)
				photonewfilename = datetime.strftime(photodate, '%Y%m%d_%H%M%S') + " " + photofilename
				print ("\tRenamed: Added a Fulldate")
				logging.info ("Filename will be renamed as: %s" % photonewfilename)
			else:
				logging.debug ("Filename already starts with a full date expression")

		# Setting the destination
		dest = os.path.join (eventpath, photonewfilename)
		logging.info ("will be send to :" + dest)

		# file operations
		if itemcheck (photopath) != "file":
			infomsg = "Image in database is not present at this time. Doing nothing."
			print (infomsg) ; logging.info (infomsg)
			continue

		if photopath == dest :
			infomsg = "This file is already on its destination. Doing nothing."
			print (infomsg) ; logging.info (infomsg)
			continue

		if itemcheck (dest) != "":
			infomsg = "File already exists at destination, Skipping."
			print (infomsg) ; logging.info (infomsg)
			continue

		if itemcheck (os.path.dirname(dest)) == '':
			os.makedirs (os.path.dirname(dest))
		print ("\tmoved:",)
		if dummy == False:
			shutil.move (photopath, dest)
		logging.info ("file has been moved. %s" %dummymsg)

		# Changing DB pointer
		if dummy == False:
			dbconnection.execute ('UPDATE %s SET filename = ? where id = ?' % DBTable, (dest, photoid))
			logging.debug ("Entry %s updated at table %s.%s" % (photoid, DBTable, dummymsg))

	dbtablecursor.close()

dbeventcursor.execute("DELETE FROM EventTable WHERE id = -1")
dbeventcursor.close()
dbconnection.commit()
logging.debug ("Changes were commited")
dbconnection.close ()
logging.debug ("DB connection was closed")

# Cleaning empty folders
if clearfolders == True:
	logging.info ('Checking empty folders to delete them')
	foldercollectionnext = set()
	while len(foldercollection) > 0:
		for i in foldercollection:
			logging.info ('checking: %s' %i)
			if itemcheck(i) != 'folder':
				logging.warning ('\tDoes not exists or is not a folder. Skipping')
				continue			
			if len (os.listdir(i)) == 0:
				shutil.rmtree (i)
				infomsg = "\tfolder: %s has been removed. (was empty)" % i
				print (infomsg)
				logging.info (infomsg)
				foldercollectionnext.add (os.path.dirname(i))
				logging.debug ("\tadded next level to re-scan")
		foldercollection = foldercollectionnext
		foldercollectionnext = set()
print ('Done!')

