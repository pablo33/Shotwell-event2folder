#!/usr/bin/python3

import sqlite3, os, sys, shutil, logging, re, time, pickle
from hashlib import md5

from datetime import datetime
import gi  # used to avoid Gi warning
gi.require_version('GExiv2', '0.10')  # used to avoid Gi warning
from gi.repository import GExiv2  # for metadata management. Dependencies: gir1.2-gexiv2   &   python-gobject
from subprocess import check_output  # Checks if shotwell is active or not


# ------- Class Exceptions  ---------
class OutOfRangeError(ValueError):
	pass
class NotIntegerError(ValueError):
	pass
class NotStringError(ValueError):
	pass
class MalformedPathError(ValueError):
	pass
class EmptyStringError(ValueError):
	pass


# ------- Set Environment ---------
os.stat_float_times (False)  #  So you won't get milliseconds retrieving Stat dates; this will raise in error parsing getmtime.
gi.require_version('GExiv2', '0.10')  # user to avoid Gi warning

# ------- Set Variables ---------
UserHomePath = os.getenv('HOME')
DBpath = os.path.join(UserHomePath,".local/share/shotwell/data/photo.db")  # Path where Shotwell DB is expected to be.
Th128path = os.path.join(UserHomePath,".cache/shotwell/thumbs/thumbs128")  # Path where thumbnails are stored.
Th360path = os.path.join(UserHomePath,".cache/shotwell/thumbs/thumbs360")  # Path where thumbnails are stored.
LastExec = None

# -------- Global Vars ----------
mintepoch = '1800'  # In order to discard low year values, this is the lowest year. // fetched later by user configuration.


monthsdict = {
"01" : ("enero", "ene", "juanuary", "jan"),
"02" : ("febrero", "feb", "february"),
"03" : ("marzo", "mar", "march"),
"04" : ("abril", "abr", "april", "apr"),
"05" : ("mayo", "may","may"),
"06" : ("junio", "jun", "june"),
"07" : ("julio", "jul", "july"),
"08" : ("agosto", "ago", "agost"),
"09" : ("septiembre", "sep", "set","september"),
"10" : ("octubre", "oct", "october"),
"11" : ("noviembre", "nov", "november"),
"12" : ("diciembre", "dic", "december", "dec"),
}  # Months word dict.

# ------ utils --------
def itemcheck(pointer):
	''' returns what kind of a pointer is '''
	if type(pointer) is not str:
		raise NotStringError ('Bad input, it must be a string')
	if pointer.find("//") != -1 :
		raise MalformedPathError ('Malformed Path, it has double slashes')
	
	if os.path.isfile(pointer):
		return 'file'
	if os.path.isdir(pointer):
		return 'folder'
	if os.path.islink(pointer):
		return 'link'
	return ""

def Nextfilenumber (dest):
	''' Returns the next filename counter as filename(nnn).ext
	input: /path/to/filename.ext
	output: /path/to/filename(n).ext
		'''
	if dest == "":
		raise EmptyStringError ('empty strings as input are not allowed')
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

def NoTAlloChReplace (myfilename):
	''' This function gets a string and replace a set of characters by a underscore.
	It is intended to clean filenames and add compatibility with Windows and OSx file systems
		'''
	chars = '/\:*?"<>|'
	for i in chars:
		myfilename = myfilename.replace(i, '_')
	return myfilename


def gsettingsget (schema, key, data_type):
	"""
	Gets a key from dconfig using gsettings binary.
	check_output returns a bites string. You have to decode this string to the expected key data.
	"""
	value = check_output(['gsettings','get', schema, key])

	if data_type == 'bool':
		value = eval(value.decode().strip().capitalize())
		return value


# Functions
def extracttitle (photofilename):
	title = photofilename

	# Discarding fulldate identifiers
	sep = '[-._: ]'
	for expr in ['[12]\d{3}%(sp)s?[01]\d%(sp)s?[0-3]\d%(sp)s?[012]\d%(sp)s?[0-5]\d%(sp)s?[0-5]\d' %{'sp':sep},
					'[12]\d{3}%(sp)s?[01]\d%(sp)s?[0-3]\d' %{'sp':sep},
					'[Ww][Aa]\d{4}',
					'[12]\d{3}%(sp)s?[01]\d' %{'sp':sep},
					'MVI%(sp)s\d{4}' %{'sp':sep} ]:
		while True:
			mo = re.search (expr, title)
			try:
				mo.group()
			except:
				logging.debug ("Fulldate expression was not found in %s" % title)
				break
			else:
				logging.debug ("Filename has a full date expression. Discarding this data on title.")
				title = title.replace(mo.group(),"")
	
	# Replacing starting simbols & numbers
	expr = '[0-9 ]?[-_#.%$& ]?[0-9 ]?'
	while True:
		mo = re.search (expr, title)
		try:
			mo.group()
		except:
			break
		else:
			if title.startswith (mo.group()):
				logging.debug ("Discarding starting sybols and spaces.")
				title = title [len (mo.group()): ]
				if mo.group() == "":
					break
			else:
				break

	# Replacing ending simbols & numbers
	if len(title) > 0:
		while title[-1] in '-_#1234567890 ':
			title = title[:-1]
			if len(title) == 0:
				break


	# Replacing standalone known series
	if title.lower() in ['img', 'jpg', 'foto', 'image', 'photo', 'scan', 'picture']:
		logging.debug ("Discarding known standalone serie:" + title.lower())
		title = ""

	# Assigning a null value if title is empty
	if title == "":
		title = None
	logging.debug ("The title for this entry will be: " + str(title))
	return title

def filemove (origin, dest):
	if itemcheck (origin) != 'file':
		return None
	while itemcheck (dest) != "" :
		infomsg = "File already exists at destination, assigning a new name."
		dest = Nextfilenumber (dest)
		logging.debug (infomsg + " >> " + dest)

	if dummy == False:
		if itemcheck (os.path.dirname(dest)) == '':
			os.makedirs (os.path.dirname(dest))
		shutil.move (origin, dest)
	#print ("      > file has been moved. {}".format(dummymsg))
	logging.debug ("\tfile has been moved. {}".format(dummymsg))
	return dest

def Thumbfilepath (ID,Tablename='PhotoTable'):
	""" This function returns the full-filepath of the thumbnails given an id
		Thumbs are composed by the ID of the file filled with Zeroes at a length of 16.
		ID are expressed in Hex. This is the mask:
		# thumb000000000000000f
		Paths are expressed as follows (ID = 10)
		~/.cache/shotwell/thumbs/thumbs128/thumb000000000000000a.jpg
		~/.cache/shotwell/thumbs/thumbs360/thumb000000000000000a.jpg

		Paths to thumbnails folders are global vars. (Th128path, Th360path)
		"""
	lead = 'thumb'
	if Tablename == 'VideoTable':
		lead = 'video-'

	if type(ID) is not int:
		raise NotIntegerError(ID)
	if ID < 1 :
		raise OutOfRangeError(ID)

	source_id = lead + '%016x'%ID 

	Path128 = os.path.join(Th128path,source_id + ".jpg")
	Path360 = os.path.join(Th360path,source_id + ".jpg")
	return (source_id,Path128,Path360)

def Deletethumb (ID):
	""" This function deletes thumbnails given an ID
		"""
	for f in Thumbfilepath(ID)[2:3]:
		if itemcheck(f) == 'file':
			if dummy == False:
				os.remove (f)
			infomsg = ('Thumbfile for ID ({}) has been removed'.format(ID))
			print (infomsg)
			logging.debug (infomsg)

def get_pid (app):
	''' returns None if the aplication is not running, or
		returns application PID if the aplication is running 
		'''
	try:
		pids = check_output(["pidof", app ])
	except:
		logging.debug('no {} process is currently running'.format(app))
		return None
	pidlist = pids.split()
	la = lambda x : int(x)
	pidlist = list (map (la , pidlist))
	return pidlist

def getappstatus (app):
	''' Given a list of names's process, it checks if there is any instance running
		DefTest >> OK'''
	state = False
	for entry in app:
		if get_pid (entry) != None:
			state = True
			break
	return state

def addtoconfigfile (linetoadd):
	print ("adding a new parameter to the user config file: {}".format(linetoadd.split()[0]))
	f = open(userfileconfig,"a")
	f.write ("\n" + linetoadd)
	f.close()

def Changes ():
	""" Check if there have been modified ShotwellDatabase since last execution
		The last date of execution is stored in a file at user's configuration folder.
		The file is created only in daemonmode.
		
		It returns True in case it has changed
		It returns False in other case
		"""
	global LastExec, lastExecFile
	shotwellDBstatDate = datetime.fromtimestamp(os.path.getmtime (DBpath))
	if LastExec == None or itemcheck (lastExecFile) != 'file':
		logging.info ('Shotwell DB time: {}'.format(shotwellDBstatDate))
		if itemcheck (lastExecFile) == 'file':
			f = open (lastExecFile, 'rb')
			LastExec = pickle.load (f)
			f.close ()
			logging.info ('LastExec from pickle: {}'.format(LastExec))
		else:
			LastExec = datetime.now()
			logging.info ('Initializing pickle: {}'.format(LastExec))
			return True
	if shotwellDBstatDate > LastExec:
		return True
	logging.debug ('shotwellDB has no changes:')
	logging.debug ('shotwellDBstatDate: {}'.format(shotwellDBstatDate))
	logging.debug ('          LastExec: {}'.format(LastExec))
	return False

class Progresspercent:
	''' Show the progression of an activity in percentage
	it is swhon on the same line'''
	def __init__ (self, maxValue, title = '', showpartial=True):
		if title != '':
			self.title = " {} :".format(title)  # Name of the 
		else:
			self.title = " "
		self.maxValue = maxValue
		self.partial = showpartial

	def showprogress (self, p, valuetext = ""):
		'''
		Shows the progress in percentage vía stdout, and returns its value again.
		'''
		progressvalue = (p / self.maxValue)
		progresspercent = "{:.2%}".format(progressvalue)
		if self.partial == True:
			progresspartial = "({:6}/{:<6})".format(p,self.maxValue)
		else:
			progresspartial = ''
		progresstext = "{}{}{}{}".format (self.title,valuetext, progresspartial, progresspercent)
		#sys.stdout.write (progresstext + chr(8)*len(progresstext))
		sys.stdout.write (progresstext + chr(8)*len(progresstext))
		if p == self.maxValue:
			sys.stdout.write('\n')
		sys.stdout.flush()
		return progresspercent

def md5hash (filepath):
	""" Given a fullpath to a file, it will return the md5 hashstring
		it reads in bytes mode and it will load the full file in memory
		"""
	hasher = md5()
	with open(filepath, 'rb') as afile:
		buf = afile.read()
		hasher.update(buf)
	return (hasher.hexdigest())

def enclosedyearfinder (string):
	""" searchs for a year string,
	it must return the year string if any or None if it doesn't
		"""
	if string.isnumeric():
		return string
	return None

def enclosedmonthfinder (string):
	""" Give a string, returns a string if it is a month number,
		otherwise it returns None,
		"""
	if len (string) == 2 and string.isnumeric ():
		if int(string) in range(1,13):
			logging.debug( 'found possible month in'+ string )
			return string
	for element in monthsdict:
		if string.lower() in monthsdict[element]:
			return element
	return None

def encloseddayfinder (string):
	""" Give a string, returns a string if it is a month number,
		otherwise it returns None,
		"""
	if len (string) == 2 and string.isnumeric ():
		if int(string) in range(1,32):
			logging.debug( 'found possible day in'+ string )
			return string
	return None

def yearmonthfinder (string):
	""" Given a string, returns a combo of numeric  year-month if it is found,
		otherwise returns None .
		"""
	expr = ".*(?P<year>[12]\d{3})[-_ /:.]?(?P<month>[01]?\d).*"
	mo = re.search(expr, string)
	try:
		mo.group()
	except:
		pass
	else:
		num_month = int(mo.group('month'))
		if num_month in range (1,13) :
			fnyear = mo.group ('year')
			fnmonth = '{0:02}'.format(num_month)
			return fnyear, fnmonth
	return None, None

def yearmonthdayfinder (string):
	""" Given a string, returns a combo of numeric  year-month-day if it is found,
		otherwise returns None.
		"""

	expr = "(?P<year>[12]\d{3})[-_ /:.]?(?P<month>[01]?\d)[-_ /:.]?(?P<day>[0-3]?\d)"
	mo = re.search(expr, string)
	try:
		mo.group()
	except:
		pass
	else:
		fnyear, num_month, num_day = mo.group ('year'), int(mo.group('month')), int(mo.group('day'))
		if 0 < num_month < 13 and 0 < num_day < 32:
			fnmonth = '{0:02}'.format(num_month)
			fnday = '{0:02}'.format(num_day)
			return fnyear, fnmonth, fnday
	return None, None, None

def fulldatefinder (string):
	""" Given a string, returns a combo of numeric YYYY-MM-DD-hh-mm-ss True if a full-date-identifier
		if found, otherwise returns None"""
	start = False
	sep = '[-_ :.]'
	expr = '(?P<year>[12]\d{3})%(sep)s?(?P<month>[01]?\d)%(sep)s?(?P<day>[0-3]?\d)%(sep)s?(?P<hour>[012]\d)%(sep)s?(?P<min>[0-5]\d)%(sep)s?(?P<sec>[0-5]\d)' %{'sep':'[-_ .:]'}
	mo = re.search (expr, string)
	try:
		mo.group()
	except:
		logging.debug ("expression %s Not found in %s" %(expr, string))
		pass
	else:
		num_month, num_day = int(mo.group ('month')), int(mo.group ('day'))
		year  = mo.group ('year')
		month = '{0:02}'.format(num_month)
		day   = '{0:02}'.format(num_day)
		hour  = mo.group ('hour')
		minute   = mo.group ('min')
		sec   = mo.group ('sec')
		if mo.start() == 0 :
			start = True
		return year, month, day, hour, minute, sec, start
	return None, None, None, None, None, None, None

def serieserial (string):
	''' given a filename string, it returns serie and serial number (tuple)
		otherwise it returns None'''

	sep = '[-_ ]'
	seriallist = ['WA','IMG','PICT','MVI','img']
	#seriallist = seriallist + seriallist.lower() for 
	for key in seriallist :
		expr = '(?P<se>%s%s?)(?P<sn>[0-9]{4})'%(key,sep)

		mo = re.search (expr, string)
		try:
			mo.group()
		except:
			logging.debug ("expression {} Not found in {}".format(expr, string))
			continue
		else:
			logging.debug ("expression {} found in {}".format(expr, string))
			imserie  = mo.group ('se')
			imserial = mo.group ('sn')
			logging.debug ( 'Item serie and serial number ({}): {} {}'.format(string,imserie,imserial))
			return imserie, imserial
	return None, None

def findeventname(Abranch):
	#  /YYYY-MM XeventnameX/
	exprlst = [
		"/[12]\d{3}[-_ ]?[01]\d ?(?P<XeventnameX>.*)/",
		"[12]\d{3}[-_ ]?[01]\d[-_ ]?[0-3]\d ?(?P<XeventnameX>.*)/",
		]

	#  /YYYY-MM-DD XeventnameX/
	eventname = ''
	for expr in exprlst: 
		mo = re.search(expr, Abranch)
		try:
			mo.group()
		except:
			pass
		else:
			eventname = mo.group('XeventnameX')
	return eventname

def mediainfo (abspath, assignstat):
	# Global dependent variables:
	#	mintepoch # In order to discard low year values, this is the lowest year. 

	#1) Retrieve basic info from the file
	logging.debug ('## item: {}'.format(abspath))
	filename, fileext = os.path.splitext(os.path.basename (abspath))
	Statdate = datetime.utcfromtimestamp(os.path.getmtime (abspath))
	filebytes = os.path.getsize(abspath)  # logging.debug ('fileTepoch (from Stat): '.ljust( logjustif ) + str(fileTepoch))
	fnDateTimeOriginal = None  # From start we assume a no date found on the file path
	decideflag = None
	TimeOriginal = None

	#2) Fetch date identificators form imagepath, serie and serial number if any. 

	# Try to find some date structure in folder paths. (abspath)
	''' Fetch dates from folder structure, this prevents losing information if exif metadata 
	doesn't exist. Metada can be lost if you modify files with software. It is also usefull 
	if you move video files (wich doesn't have exif metadata) among cloud services.
	Pej. you can store a folder structure in your PC client dropbox, and you'll lose your "stat" date,
	 but you can always recover it from file name/path.
	Structures:
		Years:
			one of the path-folder starts as a year number with four numbers
				[12]\d{3}    YYYY
		Months:
			one of the path folders is a month numbers
		Combos:
			one of the path folders starts with YYYY-MM

		Full date:
			there is a full-date structure on the path.
			2015-01-04 | 2015_01_04 | 2015:01:04 | 2015 01 04

		The day, hour-minutes and seconds asigned are 01, 12:00:00 + image serial number (in seconds) for each image to preserve an order.
		'''
	## Cutting main tree from fullpaths.
	pathlevels = os.path.dirname (abspath).split ('/')
	# Removig not wanted slashes
	if '' in pathlevels:
		pathlevels.remove('')
	logging.debug ('Found directories levels: '+str(pathlevels))
	# Starting variables. From start, we assume that there is no date at all.
	fnyear  = None
	fnmonth = None
	fnday   = '01'
	fnhour  = '12'
	fnmin   = '00'
	fnsec   = '00'
	for word in pathlevels:
		# C1.1 (/year/)
		yearfound = enclosedyearfinder (word)
		if yearfound != None:
			if mintepoch < yearfound < '2038':
				fnyear = yearfound
				continue

		# C1.2 (/month/)
		monthfound = enclosedmonthfinder (word)
		if monthfound != None:
			fnmonth = monthfound
			continue

		# C1.3 (/day/):
		dayfound = encloseddayfinder (word)
		if dayfound != None:
			fnday = dayfound
			continue

		# C2.1 (Year-month)
		yearfound, monthfound = yearmonthfinder (word)
		if yearfound != None:
			if mintepoch < yearfound < "2038":
				fnyear = yearfound
				fnmonth = monthfound
				logging.debug('month and day found in C2.1 {}-{}'.format(fnyear,fnmonth))

		# C3.1: (Year-month-day)
		yearfound, monthfound, dayfound = yearmonthdayfinder (word)
		if yearfound != None:
			if mintepoch < yearfound < "2038":
				fnyear = yearfound
				fnmonth = monthfound
				fnday = dayfound


	# C4: YYYY-MM-DD  in filename
	yearfound, monthfound, dayfound = yearmonthdayfinder (filename)
	if yearfound != None:
		if mintepoch < yearfound < "2038":
			fnyear = yearfound
			fnmonth = monthfound
			fnday = dayfound
			logging.debug('month and day found in C4 {}-{}-{}'.format(fnyear,fnmonth,fnday))

	# C3.2 (Year-month in filename)
	if fnyear == None and fnmonth == None:
		yearfound, monthfound = yearmonthfinder (filename)
		if yearfound != None:
			if mintepoch < yearfound < "2038":
				fnyear = yearfound
				fnmonth = monthfound
				logging.debug('month and day found in C3.2 {}-{}'.format(fnyear,fnmonth))

	# C5: YYYYMMDD-HHMMSS  in filename and find a starting full-date identifier
	Imdatestart = False  # Flag to inform a starting full-date-identifier at the start of the file.
	foundtuple = fulldatefinder (filename)

	if foundtuple[0] != None:
		if mintepoch < foundtuple[0] < "2038":
			fnyear  = foundtuple[0]
			fnmonth = foundtuple[1]
			fnday   = foundtuple[2]
			fnhour  = foundtuple[3]
			fnmin   = foundtuple[4]
			fnsec   = foundtuple[5]
			logging.debug ( 'found full date identifier in ' + filename)
			#if mo.start() == 0 :
			if foundtuple[6] == True:
				logging.debug ('filename starts with a full date identifier: '+ filename )
				Imdatestart = True  #  True means that filename starts with full-date serial in its name (item will not add any date in his filename again)


	# setting creation date retrieved from filepath
	if fnyear != None and fnmonth != None:
		textdate = '{}:{}:{} {}:{}:{}'.format (fnyear, fnmonth, fnday, fnhour, fnmin, fnsec)
		logging.debug ('This date have been retrieved from the file-path-name: ' + textdate )
		fnDateTimeOriginal = datetime.strptime (textdate, '%Y:%m:%d %H:%M:%S')


	# Fetch Serial number from filename
	imserie, imserial = serieserial (filename)

	# Set Creation Date extracted from filename/path
	if fnDateTimeOriginal != None :
		TimeOriginal = fnDateTimeOriginal
		decideflag = 'Filepath'

	elif assignstat:
		# Set Creation Date from stat file.
		TimeOriginal = Statdate
		decideflag = 'Stat'
	
	if decideflag != None:
		logging.debug ('\tImage Creation date has been set from {}, ({}): '.format (decideflag,str(TimeOriginal)))

	if TimeOriginal == None:
		logging.debug ( "\tCan't guess Image date of Creation" )
		TimeOriginalEpoch = None
	else:
		TimeOriginalEpoch = int(datetime.timestamp(TimeOriginal))
	
	#return filename, fileext, filebytes, Imdatestart, fnDateTimeOriginal, Statdate, TimeOriginal, decideflag, imserie, imserial

	return TimeOriginalEpoch, decideflag

def add_date_metadate (imagepath,TimeEpoch):
	metadata = GExiv2.Metadata(imagepath)
	metadata.set_date_time (datetime.fromtimestamp(TimeEpoch))
	metadata.save_file()
	logging.debug ('\t' + 'writed metadata to image file.')
	logging.debug ('\t' + imagepath)
	return


if __name__ == '__main__':

	# Load user config:
	# Getting user folder to place log files....
	appuserpath= os.path.join (UserHomePath,".Shotwell-event2folder")
	userfileconfig = os.path.join (appuserpath,"Shotevent2folder_cfg.py")
	lastExecFile = os.path.join (appuserpath,".LastExec.dump")
	if itemcheck (appuserpath) != "folder":
		os.makedirs(appuserpath)

	if itemcheck (userfileconfig) == "file":
		print ("Loading user configuration....")
		sys.path.append(appuserpath)
		import Shotevent2folder_cfg
	else:
		print ("\nThere isn't an user config file: {}".format (userfileconfig))
		# Create a new config file
		f = open(userfileconfig,"w")
		f.write ('# Shotwell-event2folder Config file.\n# This is a python file. Be careful and see the sintaxt.\n\n')
		f.close()
		print ("\nYour user config file has been created at:", userfileconfig)
		Shotevent2folder_cfg = None

	abort = False

	# Getting variables from user's config file and/or updating it.
	Default_Config_options = (
		('librarymainpath',	 		"'{}/Pictures'".format(UserHomePath), '# Main path where your imeges are or you want them to be.'),
		('dummy',			 		'False', '# Dummy mode. True will not perform any changes to DB or File structure.'),
		('insertdateinfilename',	'False', '#  Filenames will be renamed with starting with a full-date expression.'),
		('clearfolders', 			'True' , '# Delete empty folders.'),
		('librarymostrecentpath',	"'{}/Pictures/mostrecent'".format(UserHomePath), '# Path to send the most recent pictures. You can set this path synced with Dropbox pej.'),
		('mostrecentkbs', 			'0', '# Max amount of Kbs to send to the most recent pictures path as destination. Set 0 if you do not want to send any pictures there. (2000000000 is 2Gb)'),
		('morerecent_stars',		'-1', '# use values from -1 to 5 . Filter pictures or videos by rating to send to the more recent pictures path as destination. use -1 to move all files or ignore this option (default).'),
		('importtitlefromfilenames','False', '# Get a title from the filename and set it as title in the database. It only imports titles if the photo title at Database is empty.'),
		('inserttitlesinfiles',		'False', '# Insert titles in files as metadata, you can insert or update your files with the database titles. If importtitlefromfilenames is True, and the title\'s in database is empty, it will set this retrieved title in both file, and database.'),
		('daemonmode',				'False','# It keeps the script running and process Shotwell DataBase if it has changes since last execution.'),
		('sleepseconds',			'120','# Number of seconds to sleep, until another check in daemon mode.'),
		('conv_mov',				'False','# Convert movies with ffmpeg to shrink their size'),
		('conv_bitrate_kbs',		'1200','# Movies under this average bitrate will not be processed'),
		('conv_flag',				"''",'# Only convert .mov videos wich ends on this string. leave an empty string to convert all videos.'),
		('conv_extension',			"'MOV'", '# Filter video conversion to this kind of movies, leave an empty string to convert all file formats.'),
		('autodate',				'False', '# When True, it tries to auto-date _no date event_ photos. It will retrieve dates from filenames and add them to an existing event. A new event is created in case no event is found.'),
		('assignstat',				'False', '# on autodate routine, assign a date from file creation (stat) in case a no valid date were found.'),
		('mintepoch',				'1998',	 '# Minimun year, in order to fetch years from filenames.')
		)

	retrievedvalues = dict ()
	for option in Default_Config_options:
		try:
			 retrievedvalues[option[0]] = eval('Shotevent2folder_cfg.{}'.format (option[0]))

		except AttributeError:
			addtoconfigfile ('{} = {}  {}'.format(*option))
			abort = True

	if abort:
		print ("Your user config file has been updated with new options:", userfileconfig, '\n')
		print ("A default value has been assigned, please customize by yourself before run this software again.\n")
		print ("This software will attempt to open your configuration file with a text editor (gedit).")
		input ("Press a key.")
		os.system ("gedit " + userfileconfig)
		exit()

	librarymainpath = retrievedvalues ['librarymainpath']
	dummy = retrievedvalues ['dummy']
	insertdateinfilename = retrievedvalues ['insertdateinfilename']
	clearfolders = retrievedvalues ['clearfolders']
	librarymostrecentpath = retrievedvalues ['librarymostrecentpath']
	mostrecentkbs = retrievedvalues ['mostrecentkbs']
	morerecent_stars = retrievedvalues ['morerecent_stars']
	importtitlefromfilenames = retrievedvalues ['importtitlefromfilenames']
	inserttitlesinfiles = retrievedvalues ['inserttitlesinfiles']
	daemonmode = retrievedvalues ['daemonmode']
	sleepseconds = retrievedvalues ['sleepseconds']
	conv_mov = retrievedvalues ['conv_mov']
	conv_bitrate_kbs = retrievedvalues ['conv_bitrate_kbs']
	conv_flag = retrievedvalues ['conv_flag']
	conv_extension = retrievedvalues ['conv_extension']
	autodate = retrievedvalues ['autodate']
	assignstat = retrievedvalues ['assignstat']
	mintepoch = retrievedvalues ['mintepoch']

	# Fetched from Shotwell's configuration
	commit_metadata = gsettingsget('org.yorba.shotwell.preferences.files','commit-metadata','bool')


	# ===============================
	# The logging module.
	# ===============================
	loginlevel = 'INFO'  # INFO ,DEBUG
	logpath = './'
	logging_file = os.path.join(logpath, 'Shotwell_event2folder.log')


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
	print ("Logging to:", logging_file)

	# Check inconsistences.
	errmsgs = []
	
	#	--morerecent_stars
	if type(morerecent_stars) != int:
		errmsgs.append ("\n morerecent_stars at configuration file is not an integer. Must be from -1 to 5. (use -1 to move all files)")
		logging.critical ("morerecent_stars is not a integer")
	elif morerecent_stars not in range(-1,6):
		errmsgs.append ("\n morerecent_stars at configuration out of range. Must be from -1 to 5. (use -1 to move all files)")
		logging.critical ("morerecent_stars out of range. actual value: {}".format (morerecent_stars))

	#	--conv_mov
	if type(conv_mov) != bool:
		errmsgs.append ("\n conv_mov at configuration file must be True or False.")
		logging.critical ("conv_mov value is not boolean.")
	else:
		#	--conv_bitrate_kbs
		if conv_mov:
			if type(conv_bitrate_kbs) != int:
				errmsgs.append ("\n conv_bitrate_kbs at configuration file is not an integer and it should be greater than 800.")
				logging.critical ("conv_bitrate_kbs is not a integer")
		#  --conv_flag
			if type (conv_flag) != str:
					errmsgs.append ("\n conv_flag at configuration file is not an string. It marks the video file to be converted, a good choice is (conv).")
					logging.critical ("conv_flag is not a string")
			elif conv_flag in ('_c','_f'):
					errmsgs.append ("\n conv_flag can't get this two values: _c or _f. A file ending in _c means a converted video, and _f means a failed conversion. Please choose other values.")
					logging.critical ("conv_flag is using Predefined values")
		#  --conv_extension
			if conv_extension == '':
				conv_extension_q = '%'
			else:
				conv_extension_q = conv_extension

	#	--autodate
	if type(autodate) != bool:
		errmsgs.append ("\n autodate at configuration file must be True or False.")
		logging.critical ("autodate value is not boolean.")
	else:
		if autodate:
			#	--assignstat
			if type(assignstat) != bool:
				errmsgs.append ("\n assignstat at configuration file must be True or False.")
				logging.critical ("assignstat value is not boolean.")
			#	--mintepoch
			if type(mintepoch) != int:
				errmsgs.append ("\n mintepoch at configuration file is not an integer. Default value is 1998.")
				logging.critical ("mintepoch is not a integer")
			else:
				mintepoch = str(mintepoch)

	# exit if errors are econuntered
	if len (errmsgs) != 0 :
		for a in errmsgs:
			print (a)
		print ('\nplease revise your config file.','\n ....exitting',sep='\n')
		print ("This software will attempt to open your configuration file with a text editor (gedit).")
		os.system ("gedit {}".format (userfileconfig))
		exit()


	# Logging the actual config
	logging.info ('Running with this configuraton:')
	parametersdyct = {
	'librarymainpath'		: 	librarymainpath,
	'dummy'					: 	dummy,
	'insertdateinfilename'	:	insertdateinfilename,
	'clearfolders'			:	clearfolders,
	'librarymostrecentpath'	:	librarymostrecentpath,
	'mostrecentkbs'			:	mostrecentkbs,
	'morerecent_stars'		:	morerecent_stars,
	'importtitlefromfilenames':	importtitlefromfilenames,
	'daemonmode'			:	daemonmode,
	'sleepseconds'			:	sleepseconds,
	'conv_mov'				:	conv_mov,
	'conv_bitrate_kbs'		:	conv_bitrate_kbs,
	'conv_flag'				:	conv_flag,
	'conv_extension'		:	conv_extension,
	'autodate'				:	autodate,
	'assignstat'			:	assignstat,
	'commit_metadata'		:	commit_metadata,
	'mintepoch'				:	mintepoch,
	}

	
	for a in parametersdyct:
		logging.info ('{}{} = {}'.format(" "*(30-len(a)), a, parametersdyct[a]))
	logging.info('')

	# Inserting Escape chars for SQL querying
	conv_flag_q = conv_flag.replace ('/','//')
	conv_flag_q = conv_flag_q.replace ('%','/%')
	conv_flag_q = conv_flag_q.replace ('_','/_')

	# initializing global execution vars
	dummymsg = ''
	if dummy == True:
		dummymsg = '(dummy mode)'
		print ('Running in dummy mode.')

	# Checking if ffmpeg is at the system
	ffmpeg = False
	if conv_mov:
		if os.system('ffmpeg --help') != 0:
			print ('No ffmpeg tool is found. I will not able to process video files.')
			print ('You can install it by typing $sudo apt-get install ffmpeg.')
		else:
			print ('ffmpeg is present.')
			ffmpeg = True

	if daemonmode:
		print ('Running in daemon mode. I will iterate every {} seconds.'.format(sleepseconds))

	while True:
		foldercollection = set ()
		datelimit2move_exposure = datetime.now()

		# Check if Shotwell DB is present
		if itemcheck (DBpath) != "file":
			infomsg = 'Shotwell Database is not present, this script is intended to work on a Shotwell Database located at: {}'.format(DBpath)
			print (infomsg) ; logging.critical (infomsg)
			exit()

		countdown = 12
		execution = True

		if daemonmode:
			execution = Changes ()

		if execution:
			execution = False
			for a in range (countdown,0,-1):
				if getappstatus (['shotwell']):
					print ('\nWARNING: Shotwell process is running, I will not run meanwhile Shotwell application is running.')
					logging.warning ('Shotwell process is running')
					if daemonmode:
						execution = False
						break
					print ('{} retries left to desist'.format(a))
					time.sleep (10)
				else:
					execution = True
					break

		if execution:
			dbconnection = sqlite3.connect (DBpath)

			__Schema__, __appversion__ = dbconnection.execute ("SELECT schema_version, app_version FROM versiontable").fetchone()
			if __Schema__ != 20 :
				print ("This utility may not work properly with a Shotwell DataBase Schema other than 20")
				print ("DB schema 20 is used on Shotwell version 0.22 - 0.29.1")
				print ("Actual DB Schema is {}".format (__Schema__))
				print ("Actual Shotwell Version is {}".format (__appversion__))
				exit ()

			# Autodate rutine.
			if autodate:
				neweventsids = []  # I will try to add images to new created events.
				logging.debug ('Starting autodate routine')
				deltaHours = 8  # Gap to find an existent event for the images.
				deltatime = int(deltaHours*60*60/2)

				dbnoeventcursor = dbconnection.cursor()
				dbnoeventcursor.execute ("SELECT id,filename,timestamp,'PhotoTable', file_format FROM PhotoTable WHERE event_id = -1 and exposure_time = 0 UNION SELECT id,filename,timestamp,'VideoTable', null FROM VideoTable WHERE event_id = -1 and exposure_time = 0")
				for entry in dbnoeventcursor:
					logging.debug('Procesing no event_entry: {}'.format (entry))
					Id, Filepath, Timestamp, Table, File_Format = entry
					if itemcheck (Filepath) != 'file':
						logging.warning ('\tFile is not accesible: ({}) from {}'.format(Id,Table))
						continue
					TimeOriginalEpoch, decideflag = mediainfo (Filepath, assignstat)
					if decideflag == None:
						logging.info ("\tWe couldn't assign a date from the filename: {}".format(Filepath))
						continue
					else:
						logging.debug ("\t Searchign an event to add the item...")
						ocurrences, eventID = dbconnection.execute ("SELECT count(ocurrences) as events_count, event_id from \
							(select count(event_id) as ocurrences, event_id FROM \
								(select event_id, id from PhotoTable WHERE exposure_time < {0} and exposure_time > {1} \
									union	\
								select event_id, id from VideoTable WHERE exposure_time < {0} and exposure_time > {1})	\
							group by event_id order by ocurrences desc)".format(TimeOriginalEpoch + deltatime,TimeOriginalEpoch - deltatime)).fetchone()
						logging.debug ('\t{} occurences found'.format(ocurrences))
						if ocurrences != 1 and eventID not in neweventsids:
							logging.debug ('\tCreating a new event for the item.')
							#Selecting next event ID
							eventID = dbconnection.execute("SELECT max(id)+1 FROM EventTable").fetchone()[0]
							Time_created = int(datetime.timestamp(datetime.now()))
							Primary_source_id = Thumbfilepath (Id,Table)[0]
							neweventsids.append (eventID)
							#Inserting new event
							dbconnection.execute ("INSERT INTO EventTable \
										(name,primary_photo_id,time_created,primary_source_id,comment) \
									VALUES (null,null,{},'{}',null)".format( Time_created , Primary_source_id ))
						# assigning event to the image/video
						logging.debug ('\tAssigning image to the event')
						dbconnection.execute ("UPDATE {} SET exposure_time = {}, event_id = {} where id = {}".format(Table,TimeOriginalEpoch,eventID,Id))
						if commit_metadata and File_Format == 0 :
							if dummy == False:
								add_date_metadate (Filepath,TimeOriginalEpoch)
							MD5 = md5hash (Filepath)
							dbconnection.execute ("UPDATE {} SET md5 = '{}' where id = {}".format(Table, MD5, Id))
							logging.debug ('\tMetadata inserted into the image, updated md5 {}.{}'.format(MD5, dummymsg))

						if dummy == False:
							dbconnection.commit()
						logging.debug('\tChanges commited.{}'.format(dummymsg))
				dbnoeventcursor.close()
			
			totalreg = dbconnection.execute ('SELECT sum (ids) FROM (SELECT count (id) AS ids FROM phototable UNION SELECT count(id) AS ids FROM videotable )').fetchone()[0]
			progress = Progresspercent (totalreg)
			idcounter = 0

			if mostrecentkbs > 0 :
				dballitemscursor = dbconnection.cursor ()
				dballitemscursor.execute ("SELECT filesize, exposure_time, rating, 'PhotoTable' as tabla FROM PhotoTable WHERE rating >= %(rating)s UNION SELECT filesize, exposure_time, rating,'VideoTable' as tabla FROM VideoTable WHERE rating >= %(rating)s ORDER BY exposure_time DESC" %{'rating':morerecent_stars} )
				acumulatedKb = 0
				for entry in dballitemscursor:
					acumulatedKb = acumulatedKb + entry[0]
					#print (acumulatedKb)
					if acumulatedKb >= mostrecentkbs :
						break
				datelimit2move_exposure = datetime.fromtimestamp(entry[1])
				logging.info ("Files earlier than {} and with a rating of {} or more will be sent to {}".format (datelimit2move_exposure.strftime('%Y-%m-%d'), morerecent_stars, librarymostrecentpath))
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
					logging.debug ('\tEvent {} has no photos or videos (is empty). Skipping.'.format(eventid))
					continue
				eventavgtime = suma/count
				eventtime = datetime.fromtimestamp(eventavgtime)

				if eventname == None :
					eventname = ""
				else:
					eventname = NoTAlloChReplace (eventname)  # Replace not allowed character for some filesystems

				# print ("Processing event:({})".format(eventid, eventname), end='')
				logging.debug ('')
				logging.debug ('## Processing event nº {}: {} ({})'.format(eventid,eventname,eventtime))

				# defining event path:
				if eventid == -1 :
					eventpath = os.path.join(librarymainpath, eventname)
					eventpathlast = os.path.join(librarymostrecentpath, eventname)
				else:
					eventpath = os.path.join(librarymainpath,eventtime.strftime('%Y'),eventtime.strftime('%Y-%m-%d ') + eventname)
					eventpathlast = os.path.join(librarymostrecentpath,eventtime.strftime('%Y'),eventtime.strftime('%Y-%m-%d ') + eventname)

				eventpath, eventpathlast = eventpath.strip(), eventpathlast.strip()

				logging.debug ("path for the event: " + eventpath)
				logging.debug ("path for the event in case of the the most recent pictures: " + eventpathlast)

				# retrieving event's photos and videos
				dbtablecursor = dbconnection.cursor()
				dbtablecursor.execute("SELECT id, filename, title, exposure_time, import_id, 'PhotoTable' AS DBTable, editable_id, rating, md5 FROM PhotoTable WHERE event_id = ? UNION SELECT id, filename, title, exposure_time, import_id, 'VideoTable' AS DBTable, -1 AS editable_id, rating, md5 FROM VideoTable WHERE event_id = ?",(eventid, eventid))

				# Process each file
				for p in dbtablecursor:
					idcounter += 1
					eventpathF = eventpath
					photoid, photopath, phototitle, phototimestamp, import_id, DBTable, editable_id, stars, filemd5 = p
					photodate = datetime.fromtimestamp(phototimestamp)
					photodateimport = datetime.fromtimestamp(import_id)
					photofilename = os.path.basename(photopath)

					if itemcheck (photopath) != "file":
						infomsg = "! Image or video in database is not present at this moment."
						print (infomsg) ; logging.warning (infomsg)
						continue

					# logging the editable ID, just for info.
					if editable_id != -1:
						editablestring = "Editable id:(" + str(editable_id) + ")"
					else:
						editablestring = ''
					#progress.showprogress (idcounter,"Processing event:({}){}, file:({}){}.".format(eventid, eventname,photoid,editablestring))
					progress.showprogress (idcounter,"Processing entry id:{:6} ".format(photoid))
					logging.debug ("# Processing({}) {}, filename: {}".format(photoid,editablestring,photofilename))

					# Check if file is in the last Kb to move to most recent dir.
					# It also overrides files from trash beign sent to the more recent dir.
					if mostrecentkbs != 0 and photodate >= datelimit2move_exposure and stars >= morerecent_stars and eventid != -1: 
						logging.debug ("File will be sent to the recent pictures folder")
						eventpathF = eventpathlast

					photonewfilename = photofilename
					# checking a starting date in filename
					sep = ""
					if insertdateinfilename == True and phototimestamp != None and eventid != -1:
						expr = '[12]\d{3}[01]\d[0-3]\d[.-_ ]?[012]\d[0-5]\d[0-5]\d'
						mo = re.search (expr, photofilename)
						try:
							mo.group()
						except:
							logging.debug ("Predefined fulldate expression was not found in %s" % photofilename)
							sep = " "
						else:
							logging.debug ("Filename already starts with a full date expression")
							logging.debug ("Checking date on filename")
							photofilename = photofilename [len(mo.group() ):]
							if photofilename[0].lower() in '1234567809qwertyuiopasdfghjklñzxcvbnm':
								sep = " "

						photonewfilename = datetime.strftime(photodate, '%Y%m%d_%H%M%S') + sep + photofilename
						logging.debug ("Filename will be renamed as: %s" % photonewfilename)



					# Setting the destination
					if datetime.strftime(photodate, '%Y%m%d') == '19700101' and eventid == -1:
						logging.debug ('This file goes to the no-date folder')
						eventpathF = eventpathF.replace('/Trash','/no_event',1)

					# (option) import title from filenames
					if importtitlefromfilenames == True and phototitle == None:
						phototitle = extracttitle (os.path.splitext(photofilename)[0])
								# Changing Title pointer
						if dummy == False:
							dbconnection.execute ('UPDATE %s SET title = ? where id = ?' % DBTable, (phototitle, photoid))
						logging.debug ("Entry %s, title updated at table %s. Title:%s %s" % (photoid, DBTable, phototitle, dummymsg))

					# writting titles from database to file
					# database title = Extracted title = phototitle
					fileextension = os.path.splitext (photofilename)[1]
					if inserttitlesinfiles == True and phototitle != None and fileextension.lower() in ['.jpg']:
						try:
							image_metadata = GExiv2.Metadata(photopath)
						except:
							logging.warning ('\tAn error occurred during obtaining metadata on this file')
						else:
							if image_metadata.get('Iptc.Application2.Caption') != phototitle:
								mydictofmetadatas = {
								'Iptc.Application2.Caption': phototitle,
								'Iptc.Application2.Headline': phototitle,
								'Xmp.dc.title': 'lang="x-default" ' + phototitle,
								'Xmp.photoshop.Headline' : phototitle,
								}

								for x in mydictofmetadatas:
									image_metadata.set_tag_string (x, mydictofmetadatas[x])
								if dummy == False :
									image_metadata.save_file()
								#print ("    Image title metadata has been updated with database title: {}{}".format(phototitle, dummymsg))
								logging.info ("\tImage title metadata has been updated with database title: {}{}".format(phototitle, dummymsg))
					
					photonewfilename = NoTAlloChReplace (photonewfilename)  # Replace not allowed Characters on filename for some filesystems
					dest = os.path.join (eventpathF, photonewfilename)
					logging.debug ("destination is set to :" + dest)

					## Deletes thumbnails due a condition. Shotwell will restore deleted thumbnails
					'''
					if editable_id != -1:
						Deletethumb (photoid)
						'''

					## Checks the md5 hash of the files and it compares it with the DB
						# Note that Shotwell updates the md5hash if the file has changed externally
					'''fh = md5hash (photopath)
					logging.debug ("md5 in DB is the same as the file: {}".format(fh == filemd5))
						'''
					
					# file operations
					if photopath == dest:
						infomsg = "This file is already on its destination. This file remains on its place."
						logging.debug (infomsg)
						continue
					else:
						#moving files from photopath to dest
						#print ('\n    moving file {}'.format(photofilename))
						dest = filemove (photopath, dest)
						# Changing DB pointer
						if dummy == False:
							dbconnection.execute ('UPDATE {} SET filename = ? where id = ?'.format(DBTable), (dest, photoid))
						# adding a folder to scan
						foldercollection.add (os.path.dirname(photopath))	
						logging.debug (os.path.dirname(photopath) + ' added to folders list')
						logging.debug ("Entry {} updated at table {}. {}".format(photoid, DBTable, dummymsg))
					
					if editable_id != -1:
						editable_photo = dbconnection.execute ('SELECT filepath FROM BackingPhotoTable WHERE id = %s' %editable_id).fetchone()[0]
						editable_dest = os.path.splitext(dest)[0] + '_modified' + os.path.splitext(dest)[1]
						if os.path.dirname(editable_photo) == os.path.dirname(editable_dest) and editable_photo == editable_dest:
							infomsg = "This file is already on its destination. This file remains on its place."
							logging.debug (infomsg)
							continue			
						else:
							#moving files from editable_photo to editable_dest
							result = filemove (editable_photo, editable_dest)
							if result != None:
								editable_dest = result
								foldercollection.add (os.path.dirname(editable_photo))
								logging.debug (os.path.dirname(editable_photo) + ' added to folders list')
								# Changing DB pointer
								if dummy == False:
									dbconnection.execute ('UPDATE BackingPhotoTable SET filepath = ? where id = ?', (editable_dest, editable_id))
								logging.debug ("Entry %s updated at table %s. %s" % (editable_id, 'BackingPhotoTable', dummymsg))
							else:
								infomsg = 'Cannot find editable file id(%s): %s'%(editable_id,editable_photo)
								logging.warning (infomsg)

				dbtablecursor.close()

			dbeventcursor.execute("DELETE FROM EventTable WHERE id = -1")
			dbeventcursor.close()
			dbconnection.commit()
			logging.debug ("Changes were commited")

			# Cleaning empty folders
			if clearfolders == True:
				logging.info ('== Checking empty folders to delete them ==')
				foldercollectionnext = set()
				while len(foldercollection) > 0:
					for i in foldercollection:
						logging.debug ('checking: %s' %i)
						if itemcheck(i) != 'folder':
							logging.warning ('\tDoes not exists or is not a folder. Skipping')
							continue			
						if len (os.listdir(i)) == 0:
							if i == os.path.join (UserHomePath,'Desktop'):
								logging.warning ('I will not delete your Desktop directory.')
								continue
							shutil.rmtree (i)
							ftext = i
							if len (ftext) > 50:
								ftext = "..." + ftext [-47:]
							print ("    empty folder removed: {}".format(ftext))
							logging.info ('Empty folder removed: {}'.format(i))
							foldercollectionnext.add (os.path.dirname(i))
							logging.debug ("\tadded next level to re-scan")
					foldercollection = foldercollectionnext
					foldercollectionnext = set()

			# Checking and Converting MOV files
			if conv_mov and ffmpeg:
				logging.debug ('Querying DB for video conversions.')
				newImportID = int(now.timestamp())
				dbMOVcursor = dbconnection.cursor()
				dbMOVcursor.execute (
						"SELECT ROUND ((filesize/clip_duration)/(width*height/1000)) AS bitrate,* FROM videotable WHERE \
						filename LIKE '%{0}.{1}' ESCAPE '/' \
						AND bitrate > {2} \
						AND filename NOT LIKE '%/_c.mov' ESCAPE '/' \
						AND filename NOT LIKE '%/_f.{1}' ESCAPE '/' \
						AND rating > -1 \
						AND (event_id <> -1 OR (event_id = -1 and exposure_time = 0))".format (conv_flag_q, conv_extension_q, conv_bitrate_kbs,)
						)
				for entry in dbMOVcursor:
					Entry_id = entry [1]
					sourcefile = entry[2]
					Entry_width = entry [3]
					Entry_height = entry [4]
					Entry_clip_duration = entry [5]
					Entry_filesize = entry [7]
					Entry_timestamp = entry [8]
					Entry_exposure_time = entry [9]
					Entry_event_id = entry [11]
					Entry_rating = entry [14]
					Entry_title = entry [15]
					Entry_comment = entry [19]

					if itemcheck (sourcefile) != 'file':
						logging.warning ('\tThis file cannot be accessed, or does not exist at this very moment.')
						continue
										
					Entry_tag_id = 'video-%016x,'%Entry_id
					metadataparam = ''
					if Entry_exposure_time != 0:
						videoCreationTime = datetime.fromtimestamp (Entry_exposure_time)
						videoStringTime = datetime.isoformat(videoCreationTime, timespec='microseconds') + 'Z'  # Example:   2018-01-03T18:25:34.000000Z
						metadataparam += '-metadata creation_time="{}"'.format(videoStringTime)

					logging.info ('Processing file with ffmpeg: {}'.format(sourcefile))
					newFilename = os.path.splitext(sourcefile)[0]+'_c.mov'
					if itemcheck (newFilename) == 'file':
						if dummy == False:
							os.remove(newFilename)
						logging.warning ('\tIt seems that an old converted file was there, it has been deleted.{}'.format(dummymsg))
					
					if dummy == False:
						ffmpeg_status = os.system ('ffmpeg -i "{}" {} "{}"'.format(sourcefile, metadataparam, newFilename))
					else:
						ffmpeg_status = 0
					logging.debug ('\tffmpeg exitted with code: {}{}'.format(ffmpeg_status, dummymsg))

					if getappstatus (['shotwell']):
						print ('\nWARNING: Shotwell process is running, I will not run meanwhile Shotwell application is running.')
						logging.warning ('Shotwell process is running. Aborting current conversion.')
						ffmpeg_status = None  # Exit conversion sesion.

					if ffmpeg_status == 0:
						# (ffmpeg exitted with no errors)
						logging.debug ('\tFile converted, adding or updating new entries to DB')
						# Getting new values for update DB registry.
						newMD5 = 0
						newFilesize = 0
						if dummy == False:
							newMD5 = md5hash (newFilename)
							newFilesize = os.path.getsize (newFilename)
						newEntry = (None,
									newFilename,
									Entry_width,
									Entry_height,
									Entry_clip_duration,
									1,
									newFilesize,
									Entry_timestamp,
									Entry_exposure_time,
									newImportID,
									Entry_event_id,
									newMD5,
									int(now.timestamp()),
									Entry_rating,
									Entry_title,
									None,
									None,
									0,
									Entry_comment
									)
						# Fetching videoentry for an already converted video.
						videoConvlineID = dbconnection.execute ('SELECT id FROM videotable WHERE filename=? ', (newFilename,)).fetchone()
						if videoConvlineID is None:
							logging.debug ('\tInserting new line at VideoTable.{}'.format(dummymsg))
							if dummy == False:
								dbconnection.execute ('INSERT INTO videotable VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ', newEntry )
								# Adding new videofiles to tag table (cloning values)
								dbconnection.commit ()
								newEntry_id = dbconnection.execute ('SELECT max(id) FROM videotable').fetchone()[0]
								newVideoTag_id = 'video-%016x'%newEntry_id + ','
								TagCursor = dbconnection.cursor ()
								TagCursor.execute ("SELECT id, photo_id_list FROM tagtable WHERE photo_id_list LIKE '%{}%'".format(Entry_tag_id,))
								for TagEntry in TagCursor:
									lineID , tagtext = TagEntry[0], TagEntry[1]
									newTagText = tagtext + newVideoTag_id
									dbconnection.execute ('UPDATE tagtable SET photo_id_list=? WHERE id=?',(newTagText,lineID))

						else:
							logging.debug ('\tUpdating an existent registry for converted video.{}'.format(dummymsg))
							# This will not update or clone the tag registry, it will preserve existent converted video tag attributes and rating.
							if dummy == False:
								dbconnection.execute ('UPDATE videotable SET filesize=?, import_id=?, md5=?, time_created=? WHERE id = ?', (newFilesize, newImportID, newMD5, int(now.timestamp()), videoConvlineID[0]))
						
						# Set original video as rejected. (rating = -1)
						if dummy == False:
							dbconnection.execute ('UPDATE videotable SET rating=-1 WHERE id = ?', (Entry_id,))
						
					else:
						# ffmpeg encounterered errors
						if dummy == False:
							if itemcheck (newFilename) == 'file':
								os.remove(newFilename)
							if ffmpeg_status is not None:
								failedName = os.path.splitext(sourcefile)[0]+'_f.{}'.format (conv_extension)
								os.rename (sourcefile, failedName)
								dbconnection.execute('UPDATE videotable SET filename=? WHERE id=?', (failedName,Entry_id))
							else:
								break

					if dummy == False:
						dbconnection.commit()
					
				dbMOVcursor.close()
			# Closing db Connection
			dbconnection.close ()
			logging.debug ("DB connection was closed")


		if daemonmode:
			if execution:
				f = open (lastExecFile, 'wb')
				LastExec = datetime.now()
				logging.debug ('Creating/updating LastExecFile.dump')
				pickle.dump (LastExec, f)
				f.close()
			if sleepseconds > 0:
				time.sleep (sleepseconds)
			else:
				break
		else:
			break
	print ('Done!')


