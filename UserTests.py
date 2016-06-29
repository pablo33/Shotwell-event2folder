#!/usr/bin/python3

''' This script moves Test Packs to a folder on your hard disk.
	and will perform a test upon a database created from Shotwell application.
	'''

# Module import
import unittest
import os, shutil  #sys, logging, datetime, time, re
from glob import glob

# Tools
def addchilddirectory(directorio):
	""" Returns a list of child directories

	Usage: addchilddirectory(directory with absolute path)"""
	paraañadir = []
	ficheros = os.listdir(directorio)
	for a in ficheros:
		item = os.path.join(directorio, a)
		if os.path.isdir(item):
			paraañadir.append(item)
	return paraañadir

def lsdirectorytree(directory):
	""" Returns a list of a directory and its child directories

	usage:
	lsdirectorytree ("start directory")
	By default, user's home directory

	Own start directory is also returned as result
	"""
	#init list to start, own start directory is included
	dirlist = [directory]
	#setting the first scan
	moredirectories = dirlist
	while len (moredirectories) != 0:
		newdirectories = moredirectories
		moredirectories = list ()
		for element in newdirectories:
			toadd = addchilddirectory(element)
			moredirectories += toadd
		dirlist += moredirectories
	return dirlist


def SetTestPack (namepack):
	namepack = os.path.join(dyntestfolder, namepack)
	# delete old contents in test(n) folder
	if os.path.isdir (namepack):
		shutil.rmtree (namepack)

	# decompress pack
	os.system ('unzip %s.zip -d %s'%(namepack, dyntestfolder))
	
	# copying test database
	if os.path.isfile (DBpath):
		os.remove (DBpath)
	shutil.move (os.path.join(namepack,'photo.db'), DBpath)

	# copying user test config file
	if os.path.isfile (usercfgpath):
		os.remove (usercfgpath)
	shutil.move (os.path.join(namepack,'Shotevent2folder_cfg.py'), usercfgpath)


def FetchFileSet (path):
	''' Fetchs a file set of files and folders'''
	listree = lsdirectorytree (path)
	fileset = set()
	for x in listree:
		contentlist = (glob( os.path.join (x,'*')))
		for a in contentlist:
			fileset.add (a)
	return fileset


homedir = os.getenv('HOME')
#dyntestfolder = os.path.join(homedir,'git/Shotwell-event2folder/TESTS')
DBpath = os.path.join(homedir,'.local/share/shotwell/data/photo.db')
usercfgpath = os.path.join(homedir,'.Shotwell-event2folder','Shotevent2folder_cfg.py')
dyntestfolder = 'TESTS'



class TestPack1 (unittest.TestCase):
	''' processing TestPack1 alloptions active'''

	reftest = 'Test1'
	testfolder = os.path.join (dyntestfolder,reftest)


	def test_alloptionsactivated (self):
		''' insertdates in filenames
			clearfolders
			send pictures to a more recent directory
			import titles form filenames (you had to see it on shotwell DB)
			interttitles in files (you had to see it on files)
			'''

		SetTestPack (self.reftest)
		os.system ('python3 Shotwell_event2folder.py')

		known_values = set ([
			'TESTS/Test1/DefinitiveStorage',
			'TESTS/Test1/DefinitiveStorage/2016',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-02',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-02/20160602_120000-IMG-20160602-WA0000.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-03',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-03/20160603_124317-34651951377.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-04',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-04/20160604_102253-IMG_0468.JPG',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-06',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-06/20160606_195355.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-06/20160606_195434.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-09',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-09/20160609_120000-IMG-20160609-WA0001.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-13',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-13/20160613_210952-IMG_20160613_210951.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18/20160618_104842 4841.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18/20160618_113029 img_1263.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18/20160618_113121 img_1264.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18/20160618_113649 img_1265.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18/20160618_113657 3657.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18/20160618_125709-IMG_20160618_125709.jpg',
			'TESTS/Test1/DefinitiveStorage/2016/2016-06-18/20160618_131326-IMG_20160618_131325.jpg',
			'TESTS/Test1/DefinitiveStorage/no_event',
			'TESTS/Test1/DefinitiveStorage/no_event/Screenshot from 2016-06-28 19-56-56.png',
			'TESTS/Test1/Lastphotospath',
			'TESTS/Test1/Lastphotospath/2016',
			'TESTS/Test1/Lastphotospath/2016/2016-06-18',
			'TESTS/Test1/Lastphotospath/2016/2016-06-18/20160618_153207 mvi_1293.mov',
			'TESTS/Test1/Lastphotospath/2016/2016-06-18/20160618_224303 4302.jpg',
			'TESTS/Test1/Lastphotospath/2016/2016-06-22',
			'TESTS/Test1/Lastphotospath/2016/2016-06-22/20160622_141158-VID_20160622_141158.3gp',
			'TESTS/Test1/Lastphotospath/2016/2016-06-22/20160622_141203 No date on filename.jpg',
			])

		result = FetchFileSet (self.testfolder)
		self.assertEqual(known_values, result)




if __name__ == '__main__':
	unittest.main()