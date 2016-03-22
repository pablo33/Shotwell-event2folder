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
# This options can be overriden by entering a command line options (not yet implemented)
# This is a python file. Be careful and see the sintaxt.

librarymainpath = "%(home)s/Pictures"
dummy = False # Dummy mode. True will not perform any changes to DB or File structure 
insertdateinfilename = True  #  Filenames will be renamed with starting with a full-date expression
clearfolders = True  # Delete empty folders
librarymostrecentpath =  "%(home)s/Pictures/mostrecent"  # Path to send the most recent pictures. You can set this path synced with Dropbox pej.
mostrecentkbs = 2000000000  # Amount of max Kbs to send to the most recent pictures path as destination. Set 0 if you do not want to send any pictures there.
importtitlefromfilenames = True  # Get a title from the filename and set it as title in the database. It only imports titles if the photo title at Database is empty.
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
librarymostrecentpath = Shotevent2folder_cfg.librarymostrecentpath    # Path to send the most recent pictures. You can set this path synced with Dropbox pej.
mostrecentkbs = Shotevent2folder_cfg.mostrecentkbs  # Amount of max Kbs to send to the most recent picture path as destination. Set 0 if you do not want to send any pictures there.
importtitlefromfilenames = Shotevent2folder_cfg.importtitlefromfilenames  # Get a title from the filename and set it as title.


# Functions
def extracttitle (photofilename):
	title = photofilename

	# Discarding fulldate identifiers
	expr = '[12]\d{3}[01]\d[0-3]\d[.-_ ]?[012]\d[0-5]\d[0-5]\d'
	mo = re.search (expr, title)
	try:
		mo.group()
	except:
		logging.debug ("Fulldate expression was not found in %s" % title)
	else:
		logging.info ("Filename has a full date expression. Discarding this data on title.")
		title = title [len(mo.group() ):]
	
	# Replacing empty spaces
	title = title.strip()

	# Discarding titles only made by numbers
	expr = '\d*'
	mo = re.search (expr, title)
	try:
		mo.group()
	except:
		pass
	else:
		logging.info ("Name is only made by numbers. Discarding this data on title.")
		title = title [len(mo.group() ):]

	if title == "":
		title = None
	logging.info ("The title for this file will be: " + str(title))
	return title

def Nextfilenumber (dest):
	''' Returns the next filename counter as filename(nnn).ext
	input: /path/to/filename.ext
	output: /path/to/filename(n).ext
		'''
	filename = os.path.basename (dest)
	extension = os.path.splitext (dest)[1]
	# extract secuence
	expr = '\(\d{1,}\)'+extension
	mo = re.search (expr, filename)
	try:
		grupo = mo.group()
	except:
		#  print ("No final counter expression was found in %s. Counter is set to 0" % dest)
		counter = 0
		cut = len (extension)
	else:
		#  print ("Filename has a final counter expression.  (n).extension ")
		cut = len (mo.group())
		countergroup = (re.search ('\d{1,}', grupo))
		counter = int (countergroup.group()) + 1
	if cut == 0 :
		newfilename = os.path.join( os.path.dirname(dest), filename + "(" + str(counter) + ")" + extension)
	else:
		newfilename = os.path.join( os.path.dirname(dest), filename [0:-cut] + "(" + str(counter) + ")" + extension)
	return newfilename

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


# Logging the actual config
logging.info ('Running with this configuraton:')
parametersdyct = {
'librarymainpath'		: 	librarymainpath,
'dummy'					: 	dummy,
'insertdateinfilename'	:	insertdateinfilename,
'clearfolders'			:	clearfolders,
'librarymostrecentpath'	:	librarymostrecentpath,
'mostrecentkbs'			:	mostrecentkbs,
'importtitlefromfilenames':	importtitlefromfilenames,
}
for a in parametersdyct:
	logging.info (a+'\t'+' = '+ str (parametersdyct[a]))
logging.info('')


# initializing vars
dummymsg = ''
if dummy == True:
	dummymsg = '(dummy mode)'

foldercollection = set ()
datelimit2move_exposure = datetime.now()


# Check if Shotwell DB is present
if itemcheck (DBpath) != "file":
	infomsg = 'Shotwell Database is not present, this script is intended to work on a Shotwell Database located at:\n' + DBpath
	print (infomsg) ; logging.info (infomsg)
	exit()

dbconnection = sqlite3.connect (DBpath)

# Set the more recent Kbs of data and stablishing the limit to move if any.
if mostrecentkbs > 0 :
	dballitemscursor = dbconnection.cursor ()
	dballitemscursor.execute ("SELECT filesize,exposure_time,'PhotoTable' as tabla FROM PhotoTable UNION SELECT filesize,exposure_time,'VideoTable' as tabla FROM VideoTable ORDER BY exposure_time DESC")
	acumulatedKb = 0
	for entry in dballitemscursor:
		acumulatedKb = acumulatedKb + entry[0]
		#print (acumulatedKb)
		if acumulatedKb >= mostrecentkbs :
			break
	datelimit2move_exposure = datetime.fromtimestamp(entry[1])
	logging.info ("Files more recent than " + datelimit2move_exposure.strftime('%Y-%m-%d') + " will be send to " + librarymostrecentpath)
	dballitemscursor.close()

dbeventcursor = dbconnection.cursor ()
# Inserting a Trash event
dbeventcursor.execute("INSERT INTO EventTable (id, name) VALUES (-1,'Trash')")
# event cursor
dbeventcursor.execute('SELECT id,name FROM EventTable')
for e in dbeventcursor:
	# Retrieve event data
	eventid, eventname = e	
	times = dbconnection.execute('SELECT exposure_time FROM videotable WHERE event_id = ? and exposure_time is not null UNION select exposure_time from phototable where event_id = ? and exposure_time is not null',(eventid,eventid))

	#    calculating event date by average
	suma, count = 0, 0 
	for l in times:
		count += 1 
		suma += l[0]
	if count == 0:
		logging.debug ('\tEvent %s has no photos or videos (is empty). Skipping.' % eventid)
		continue
	eventavgtime = suma/count
	eventtime = datetime.fromtimestamp(eventavgtime)

	#  ....TODO.... Check for name inconsistences, and change not allowed characters.
	if eventname == None : eventname = ""
	print ("\nProcessing event:(" + str(eventid) + ") " + eventname)
	logging.info ('')
	logging.info ('## Processing event nº' + str(eventid) + ", " + eventname + "(" + str(eventtime) + ")")

	# defining event path:
	
	if eventid == -1 :
		eventpath = os.path.join(librarymainpath, eventname)
		eventpathlast = os.path.join(librarymostrecentpath, eventname)
	else:
		eventpath = os.path.join(librarymainpath,eventtime.strftime('%Y'),eventtime.strftime('%Y-%m-%d ') + eventname)
		eventpathlast = os.path.join(librarymostrecentpath,eventtime.strftime('%Y'),eventtime.strftime('%Y-%m-%d ') + eventname)

	eventpath, eventpathlast = eventpath.strip(), eventpathlast.strip()

	logging.info ("path for the event: " + eventpath)
	logging.info ("path for the event in case of the the most recent pictures: " + eventpathlast)

	# retrieving event's photos and videos
	dbtablecursor = dbconnection.cursor()
	dbtablecursor.execute("SELECT id, filename, title, exposure_time, import_id, 'PhotoTable' AS DBTable, title  FROM PhotoTable WHERE event_id = ? UNION SELECT id, filename, title, exposure_time, import_id, 'VideoTable' AS DBTable, title FROM VideoTable WHERE event_id = ?",(eventid, eventid))

	# Process each file
	for p in dbtablecursor:
		eventpathF = eventpath
		photoid, photopath, phototitle, phototimestamp, import_id, DBTable, phototitle = p
		photodate = datetime.fromtimestamp(phototimestamp)
		photodateimport = datetime.fromtimestamp(import_id)

		# Check if file is in the last Kb to move to most recent dir.
		if mostrecentkbs != 0 and photodate >= datelimit2move_exposure : 
			logging.info ("File will be sent to the recent pictures folder")
			eventpathF = eventpathlast

		# adding a folder to scan
		foldercollection.add (os.path.dirname(photopath))	
		logging.debug (os.path.dirname(photopath) + ' added to folders list')
		# defining filename
		photofilename = os.path.basename(photopath)
		infomsg = "Processing(" + str(photoid) + ") filename: " + photofilename
		print (infomsg) ; logging.info (infomsg)

		photonewfilename = photofilename
		# checking a starting date in filename
		sep = ""
		if insertdateinfilename == True and phototimestamp != None:
			expr = '[12]\d{3}[01]\d[0-3]\d[.-_ ]?[012]\d[0-5]\d[0-5]\d'
			mo = re.search (expr, photofilename)
			try:
				mo.group()
			except:
				logging.debug ("Fulldate expression was not found in %s" % photofilename)
				sep = " "
			else:
				logging.debug ("Filename already starts with a full date expression")
				logging.debug ("updating date on filename")
				photofilename = photofilename [len(mo.group() ):]
				print (photofilename, mo.group(), len (mo.group()))

			photonewfilename = datetime.strftime(photodate, '%Y%m%d_%H%M%S') + sep + photofilename
			logging.info ("Filename will be renamed as: %s" % photonewfilename)



		# Setting the destination
		if datetime.strftime(photodate, '%Y%m%d') == '19700101' and eventid == -1:
			logging.info ('This file goes to the no-date folder')
			eventpathF = eventpathF.replace('/Trash','/no_event',1)

		# (option) import title from filenames
		
		if importtitlefromfilenames == True and phototitle == None:
			phototitle = extracttitle (os.path.splitext(photofilename)[0])
					# Changing Title pointer
			'''
			if dummy == False:
				dbconnection.execute ('UPDATE %s SET title = ? where id = ?' % DBTable, (phototitle, photoid))
			logging.debug ("Entry %s, title updated at table %s. Title:%s %s" % (photoid, DBTable, phototitle, dummymsg))
			'''

		dest = os.path.join (eventpathF, photonewfilename)
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

		while itemcheck (dest) != "" :
			infomsg = "File already exists at destination, assigning a new name."
			dest = Nextfilenumber (dest)
			logging.info (infomsg + " >> " + dest)

		if itemcheck (os.path.dirname(dest)) == '':
			os.makedirs (os.path.dirname(dest))
		print ("\tmoved.",)
		if dummy == False:
			shutil.move (photopath, dest)
		logging.info ("file has been moved. %s" %dummymsg)

		# Changing DB pointer
		if dummy == False:
			dbconnection.execute ('UPDATE %s SET filename = ? where id = ?' % DBTable, (dest, photoid))
		logging.debug ("Entry %s updated at table %s. %s" % (photoid, DBTable, dummymsg))

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

