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
		(1, (thumbsfolder+'thumbs128/thumb0000000000000001.jpg',thumbsfolder+'thumbs360/thumb0000000000000001.jpg')),
		(2, (thumbsfolder+'thumbs128/thumb0000000000000002.jpg',thumbsfolder+'thumbs360/thumb0000000000000002.jpg')),
		(100, (thumbsfolder+'thumbs128/thumb0000000000000064.jpg',thumbsfolder+'thumbs360/thumb0000000000000064.jpg')),
		(1555, (thumbsfolder+'thumbs128/thumb0000000000000613.jpg',thumbsfolder+'thumbs360/thumb0000000000000613.jpg')),
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






if __name__ == '__main__':
	unittest.main()

