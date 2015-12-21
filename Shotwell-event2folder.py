#!/usr/bin/python3

import sqlite3, os, shutil
from datetime import datetime

# ------ utils --------
def itemcheck(a):
	if os.path.isfile(a):
		return 'file'
	if os.path.isdir(a):
		return 'folder'
	if os.path.islink(a):
		return 'link'
	return ""


# ------- Variables ---------

DBpath = "/home/pablo/.local/share/shotwell/data/photo.db"
librarymainpath = "/home/pablo/Dropbox/Camera Uploads"
# librarymainpath = "/home/pablo/Pictures"


dbconnection = sqlite3.connect (DBpath)
dbeventcursor = dbconnection.cursor ()

#dbeventcursor.execute ('sentencia SQL')
dbeventcursor.execute('SELECT id,name FROM EventTable')
for e in dbeventcursor:
	# Retrieve event data
	eventid, eventname = e
	eventtime = datetime.fromtimestamp(dbconnection.execute('SELECT AVG(exposure_time) FROM PhotoTable WHERE event_id = ? and exposure_time is not null',(eventid,)).fetchone()[0])  # Average
	if eventname == None : eventname = ""
	#  ....TODO.... Check for name inconsistences
	print (
		("Moving event nº,",		eventid),
		("eventname:",				eventname),
		("eventdate(average):",	eventtime),
			sep = "\n")

	# defining path:
	
	eventpath = os.path.join(librarymainpath,eventtime.strftime('%Y'),eventtime.strftime('%Y-%m-%d ') + eventname)
	print (eventpath)

	dbtablecursor = dbconnection.cursor()
	dbtablecursor.execute('SELECT id,filename,title,exposure_time, title FROM PhotoTable WHERE event_id = ? UNION SELECT id,filename,title,exposure_time, title FROM VideoTable WHERE event_id = ?',(eventid, eventid))
	for p in dbtablecursor:
		photoid, photopath, phototitle, phototimestamp, phototitle = p
		photodate = datetime.fromtimestamp(phototimestamp)

		# defining filename
		#photofilename = photodate.strftime('%Y%m%d_%H%M%S')
		photofilename = os.path.basename(photopath)
		print (photofilename)

		# Setting the destination
		dest = os.path.join (eventpath, photofilename)
		print (dest)

		# file operations
		if itemcheck (photopath) != "file":
			print ("Image in database is not present at this time. Doing nothing.")
			continue

		if photopath == dest :
			print ("This file is already on its destination. Doing nothing")
			continue

		if itemcheck (dest) != "":
			print (photopath, "Already exists at destination, Skipping")
			continue

		if itemcheck (os.path.dirname(dest)) == '':
			os.makedirs (os.path.dirname(dest))
		print ("OK >> moving: ", photopath, " >> ", dest, "\n",sep = "\n")
		shutil.move (photopath, dest)
		# Changing DB pointer
		'''
		if photoid == dbconnection.execute('SELECT id FROM ? WHERE id = ?', (table, photoid )).fetchone()[0] :
			print ('item is in Photo table', os.path.basename(photopath))
			break
		'''
		# Check if file in photo-DB
		for table in ('PhotoTable', 'VideoTable'):
			if dbconnection.execute ('SELECT id FROM %s WHERE id = ? and filename = ?' % table,(photoid, photopath)).fetchone() != None:
				print ('item is in %s Database' % table)
				# updating new path in PhotoTable
				dbconnection.execute ('UPDATE %s SET filename = ? where id = ?' % table, (dest, photoid))
				break
				'''
				elif dbconnection.execute ('SELECT id FROM VideoTable WHERE id = ? and filename = ?',(photoid, photopath)).fetchone() != None:
					print ('item is in VideoTable Database')
					# updating new path in VideoTable
					dbconnection.execute ('UPDATE VideoTable SET filename = ? where id = ?', (dest, photoid))
				'''
			else:
				print ('photo is missing, something happend!!, can\'t held this error.')

	dbtablecursor.close()

dbeventcursor.close()
dbconnection.commit()
dbconnection.close ()

