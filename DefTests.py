#!/usr/bin/python3
# Test Configuration
import unittest
import Shotwell_event2folder
import datetime
import os



#####TESTS########

TM = Shotwell_event2folder

class itemcheck_text_values (unittest.TestCase):
	'''testing itemcheck function'''
	def test_emptystring (self):
		''' an empty string returns another empty string'''
		self.assertEqual (TM.itemcheck(""),"")

	def test_itemcheck (self):
		''' only text are addmitted as input '''
		sample_bad_values = (True, False, None, 33, 3.5)
		for values in sample_bad_values:
			self.assertRaises (TM.NotStringError, TM.itemcheck, values)

	def test_malformed_paths (self):
		''' malformed path as inputs are ommited and raises an error '''
		malformed_values = ("///","/home//")
		for inputstring in malformed_values:
			self.assertRaises (TM.MalformedPathError, TM.itemcheck, inputstring)


class Nextfilenumber_test (unittest.TestCase):
	""" test for Nextfilenumber function """
	known_values = (
		("file.jpg", "file(0).jpg"),
		("file1.jpg", "file1(0).jpg"),
		("file(0).jpg", "file(1).jpg"),
		("file(222).jpg", "file(223).jpg"),
		("file33", "file33(0)"),
		("file(33)", "file(34)"),
		("file(-1)", "file(-1)(0)"),
		("file.","file(0)."),
		("file(10).", "file(11)."),
		("file(X).jpg", "file(X)(0).jpg"),
		)
	def test_known_input (self):
		for inputfile, outputfile in self.known_values:
			result = TM.Nextfilenumber (inputfile)
			self.assertEqual (outputfile, result)
	def test_mad_values (self):
		self.assertRaises (TM.EmptyStringError, TM.Nextfilenumber, "")
		pass


class extracttitle_test (unittest.TestCase):
	""" Extracts a title from a filename (string) """
	known_values = (
		("2015-02-23 10:22:30 my title"		, "my title"),
		("2015-02-23 10:22:30 123456  ---   my title"		, "my title"),
		("2015-02-23 123456  ---   my title"		, "my title"),
		("2015-02-23123456  ---   my title"		, "my title"),
		("2015-12  ---   my title XXX"		, "my title XXX"),
		("2015-12  #&#$%---#03   my 3rd title XXX"		, "my 3rd title XXX"),
		("2015-12  #&#$%---#03   my title 33"		, "my title"),
		("2015-12  #&#$%---#03   my title 33"		, "my title"),
		('img', None),
		('jpg', None),
		('foto', None),
		('image', None),
		('PhoTo', None),
		('PHOTO', None),
		('picture', None),
		('scan', None),
		('12345', None),
		('00', None),				# titles made by numbers are not allowed
		('--00', None),				# titles made by numbers are not allowed
		('Wa2244 my title', 'my title'),				# titles made by numbers are not allowed
		('20101213-230005Wa2244 my title', 'my title'),				# titles made by numbers are not allowed
		('MVI_1234 my title', 'my title'),
		('my title - MVI_1234 ', 'my title'),
		('123456789 - my title - MVI_1234 ', 'my title'),
		)

	def test_known_input (self):
		for inputfile, outputfile in self.known_values:
			result = TM.extracttitle (inputfile)
			self.assertEqual (outputfile, result)


class Thumbfilepath (unittest.TestCase):
	""" Given a ID, it returns a full-filepath to its thumbnails """
	thumbsfolder = os.getenv('HOME')+'/.cache/shotwell/thumbs/'

	known_values = (
		(1, ('thumb0000000000000001',thumbsfolder+'thumbs128/thumb0000000000000001.jpg',thumbsfolder+'thumbs360/thumb0000000000000001.jpg')),
		(2, ('thumb0000000000000002',thumbsfolder+'thumbs128/thumb0000000000000002.jpg',thumbsfolder+'thumbs360/thumb0000000000000002.jpg')),
		(100, ('thumb0000000000000064',thumbsfolder+'thumbs128/thumb0000000000000064.jpg',thumbsfolder+'thumbs360/thumb0000000000000064.jpg')),
		(1555, ('thumb0000000000000613',thumbsfolder+'thumbs128/thumb0000000000000613.jpg',thumbsfolder+'thumbs360/thumb0000000000000613.jpg')),
		)

	def test_known_input (self):
		for inputvalue, expectedvalue in self.known_values:
			result = TM.Thumbfilepath (inputvalue)
			self.assertEqual (expectedvalue, result)

	def test_Thumbfilepathexeptions (self):
		''' only numbers are addmitted as input '''
		sample_bad_values = ("58", "33", True)
		for values in sample_bad_values:
			self.assertRaises (TM.NotIntegerError, TM.Thumbfilepath, values)

		sample_bad_values = (-1, 0, -32323)
		for values in sample_bad_values:
			self.assertRaises (TM.OutOfRangeError, TM.Thumbfilepath, values)


class NoTAlloChReplace_test (unittest.TestCase):
	""" Given a string, replace by an undescore this set of characters
	 / \ : * ? " < > | 
	Empty strings returns empty strings
	"""
	known_values = (
		('myfile:name','myfile_name'),
		('myfile:name.jpg','myfile_name.jpg'),
		('',''),
		('*myfile*name>','_myfile_name_'),
		('myfilenam|e','myfilenam_e'),
		('<myfilename','_myfilename'),
		('myfilename?','myfilename_'),
		('myfile/name\\','myfile_name_'),
		)

	def test_NoTAlloChReplace (self):
		for inputstring, outputstring in self.known_values:
			result = TM.NoTAlloChReplace (inputstring)
			self.assertEqual (outputstring, result)


class enclosedyearfinder (unittest.TestCase):
	""" searchs for a year in an slash enclosed string,
	it must return the year string if any or None if it doesn't
	"""
	known_values = (
		("1992", "1992"),
		("any string",None),
		("19_90", None),
		("2000", "2000"),
		("/",None ),
		("",None )
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.enclosedyearfinder (string1)
			self.assertEqual (match, result)


class enclosedmonthfinder (unittest.TestCase):
	""" Give a string, it returns a string if it is a month number with 2 digits,
		otherwise it returns None, it also returns a digit mont if it is a text month
		"""
	known_values = (
		("01", "01"),
		("2" , None),
		("10" ,"10"),
		("", None),
		("jkjkj",None),
		("enero", "01"),
		("Febrero", "02"),
		("MaR", "03"),
		("dic", "12"),
		("March", "03"),
		("Jun", "06"),
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.enclosedmonthfinder (string1)
			self.assertEqual (match, result)


class encloseddayfinder (unittest.TestCase):
	""" Give a string, it returns a string if it is a month number with 2 digits,
		otherwise it returns None, it also returns a digit mont if it is a text month
		"""
	known_values = (
		("01", "01"),
		("2" , None),
		("10" ,"10"),
		("", None),
		("jkjkj",None),
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.encloseddayfinder (string1)
			self.assertEqual (match, result)


class yearmonthfinder (unittest.TestCase):
	""" Given a string, returns a combo of numeric  year-month if it is found
		return None if not any. Possible separated chars  -_/ and one space
		"""
	known_values = (
		("2010-08",("2010","08")),
		("2010_09",("2010","09")),
		("2010 10",("2010","10")),
		("2015/01",("2015","01")),
		("2015:01",("2015","01")),
		("2015.01",("2015","01")),
		("2010X10",(None,None)),
		("2010",(None,None)),
		("2010-8",("2010","08")),
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.yearmonthfinder (string1)
			self.assertEqual (match, result)


class yearmonthdayfinder (unittest.TestCase):
	""" Given a string, returns a combo of numeric  year-month-day if it is found,
		otherwise returns None. Possible separated chars  -_/ and one space
		"""
	known_values = (
		("2010-8-01",("2010","08","01")),
		("2007-4-2",("2007","04","02")),
		("2003-7-20",("2003","07","20")),
		("2010-08-01",("2010","08","01")),
		("2010_09-10",("2010","09","10")),
		("2010 10_25",("2010","10","25")),
		("2015/01/31",("2015","01","31")),
		("2015:01.31",("2015","01","31")),
		("2015.01:31",("2015","01","31")),
		("2010X10X03",(None,None,None)),
		("1993-06 some text",(None,None,None)),
		("2010",(None,None,None)),
		("IMG-20170610-WA0014",("2017","06","10")),
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.yearmonthdayfinder (string1)
			self.assertEqual (match, result)


class fulldatefinder (unittest.TestCase):
	known_values = (
		("2010-08-01-120500",("2010","08","01","12","05","00",True)),
		("not at the begining 2010_09-10-00-59-01",("2010","09","10","00","59","01",False)),
		("2010 10_25-15-03:03",("2010","10","25","15","03","03",True)),
		("2015 01 31-080910",("2015","01","31","08","09","10", True)),
		("some text 2015.01.31 18:23:00 more text",("2015","01","31","18","23","00", False)),
		("20150131_050358",("2015","01","31","05","03","58", True)),
		("2010X10X03",(None,None,None,None,None,None,None)),
		("2010/10/1111(a)11",(None,None,None,None,None,None,None)),
		("2010-8-2-12:03:03",('2010', '08', '02', '12', '03', '03', True)),
		("2010-08-2-12:03:03",('2010', '08', '02', '12', '03', '03', True)),
		("2010-8-02-12:03:03",('2010', '08', '02', '12', '03', '03', True)),
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.fulldatefinder (string1)
			self.assertEqual (match, result)


class serieserial (unittest.TestCase):
	known_values = (
		("WA1234", ('WA','1234')),
		("WA-1234", ('WA-','1234')),
		("WA_3456", ('WA_','3456')),
		("WA 1111", ('WA ','1111')),
		("IMG-0001", ('IMG-','0001')),
		("IMG 9999", ('IMG ','9999')),
		("IMG_1234--dfdf", ('IMG_','1234')),
		("beforePICT-0001ending", ('PICT-','0001')),
		("MVI5005", ('MVI','5005')),
		("img_1771", ('img_','1771')),
		("IMG-20170610-WA0014",('WA', '0014')),
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.serieserial (string1)
			self.assertEqual (match, result)

class findeventname (unittest.TestCase):
	""" Given a text, it returns a possible event name:
		returns empty string if no event is found.
		Event-names are retrieved from directories, so an event name input-
		string, should end in slash."""
	known_values = (
		('2016-01-01 Event name 01', ''),
		('2016-01-01 Event name 01/', 'Event name 01'),
		('2016-01-01Event name 01/and some more info.jpg', 'Event name 01'),
		('bla bla bla 2016-01-01Event name 01/and some more info.jpg', 'Event name 01'),
		('bla bla bla/2016-01-01 Event name 01/2010-12-01 picture.jpg', 'Event name 01'),
		('bla bla bla/2016-01 Event name _/2010-12-01 real event name/ picture.jpg', 'real event name'),
		('bla bla bla/2016-01 Event name _/20101201 real event name/ picture.jpg', 'real event name'),
		('bla bla bla/2016-01 Event name _/2010-12 01 real event name/ picture.jpg', 'real event name'),
		('bla bla bla/2016-01 Event name _/2010-12 01real event name/ picture.jpg', 'real event name'),
		)
	def test_known_values (self):
		for string1, match in self.known_values:
			result = TM.findeventname (string1)
			self.assertEqual (match, result)


if __name__ == '__main__':
	unittest.main()

