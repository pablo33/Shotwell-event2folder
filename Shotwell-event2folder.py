#!/usr/bin/python3

import sqlite3, os, shutil, logging, re
from datetime import datetime

# ------- Set Variables ---------

DBpath = os.path.join(os.getenv('HOME'),".local/share/shotwell/data/photo.db")
librarymainpath = "/home/pablo/Pictures"
dummy = True # Dummy mode. True will not perform any changes to DB or File structure 
insertdateinfilename = True  #  Filenames will be renamed with starting with a fulldate expression
# librarymainpath = "/home/pablo/Pictures"


# ------ utils --------
def itemcheck(a):
	if os.path.isfile(a):
		return 'file'
	if os.path.isdir(a):
		return 'folder'
	if os.path.islink(a):
		return 'link'
	return ""


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

# 

dummymsg = ''
if dummy == True:
	dummymsg = '(dummy mode)'

# Check if Shotwell DB is present
if itemcheck (DBpath) != "file":
	infomsg = 'Shotwell Database is not present, this script is intended to work on a Shotwell Database located at:\n' + DBpath
	print (infomsg) ; logging.info (infomsg)
	exit()

dbconnection = sqlite3.connect (DBpath)
dbeventcursor = dbconnection.cursor ()

# event cursor
dbeventcursor.execute('SELECT id,name FROM EventTable')
for e in dbeventcursor:
	# Retrieve event data
	eventid, eventname = e
	eventtime = datetime.fromtimestamp(dbconnection.execute('SELECT AVG(exposure_time) FROM PhotoTable WHERE event_id = ? and exposure_time is not null',(eventid,)).fetchone()[0])  # Average
	#  ....TODO.... Check for name inconsistences, and change not allowed characters.
	if eventname == None : eventname = ""
	print ("\nProcessing event:(" + str(eventid) + ") " + eventname)
	logging.info ('')
	logging.info ('## Moving event nº' + str(eventid) + ", " + eventname + "(" + str(eventtime) + ")")

	# defining event path:
	
	eventpath = os.path.join(librarymainpath,eventtime.strftime('%Y'),eventtime.strftime('%Y-%m-%d ') + eventname)
	logging.info ("path for the event: " + eventpath)

	# retrieving event's photos and videos
	dbtablecursor = dbconnection.cursor()
	dbtablecursor.execute('SELECT id,filename,title,exposure_time, title FROM PhotoTable WHERE event_id = ? UNION SELECT id,filename,title,exposure_time, title FROM VideoTable WHERE event_id = ?',(eventid, eventid))

	# Process each file
	for p in dbtablecursor:
		photoid, photopath, phototitle, phototimestamp, phototitle = p
		photodate = datetime.fromtimestamp(phototimestamp)

		# defining filename
		#photofilename = photodate.strftime('%Y%m%d_%H%M%S')
		photofilename = os.path.basename(photopath)
		infomsg = "Processing(" + str(photoid) + ") filename: " + photofilename
		print (infomsg) ; logging.info (infomsg)

		# Setting the destination
		photonewfilename = photofilename
		# checking a starting date in filename
		expr = '(?P<year>[12]\d{3})(?P<month>[01]\d)(?P<day>[0-3]\d)[-_ ]?(?P<hour>[012]\d)(?P<min>[0-5]\d)(?P<sec>[0-5]\d)'
		mo = re.search (expr, photofilename)
		try:
			mo.group()
		except:
			logging.debug ("Fulldate expression was not found in %s" % photofilename)
			if insertdateinfilename == True:
				photonewfilename = datetime.strftime(photodate, '%Y%m%d_%H%M%S') + " " + photofilename
				print ("\tRenamed: Added a Fulldate")
				logging.info ("Filename will be renamed as: %s" % photonewfilename)
		else:
			logging.debug ("Filename already starts with a full date expression")


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
		
		# Check if file in photo-DB
		for table in ('PhotoTable', 'VideoTable'):
			if dbconnection.execute ('SELECT id FROM %s WHERE id = ? and filename = ?' % table,(photoid, photopath)).fetchone() != None:
				logging.debug ('item is in %s Database' % table)
				# updating new path in (Photo/Video)-Table
				if dummy == False:
					dbconnection.execute ('UPDATE %s SET filename = ? where id = ?' % table, (dest, photoid))
					logging.debug ("Entry %s updated at table %s.%s" % (photoid, table, dummymsg))
				break
			else:
				print ("Photo is missing, something happend!!, can't held this error.")

	dbtablecursor.close()
dbeventcursor.close()
dbconnection.commit()
logging.debug ("Changes were commited")
dbconnection.close ()
logging.debug ("DB connection was closed")