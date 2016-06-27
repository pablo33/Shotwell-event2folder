#!/usr/bin/python3
# Test Configuration
import unittest
import Shotwell_event2folder
import datetime



#####TESTS########


class itemcheck_text_values (unittest.TestCase):
	'''testing itemcheck function'''
	def test_emptystring (self):
		''' an empty string returns another empty string'''
		self.assertEqual (Shotwell_event2folder.itemcheck(""),"")

	def test_itemcheck (self):
		''' only text are addmitted as input '''
		sample_bad_values = (True, False, None, 33, 3.5)
		for values in sample_bad_values:
			self.assertRaises (Shotwell_event2folder.NotStringError, Shotwell_event2folder.itemcheck, values)

	def test_malformed_paths (self):
		''' malformed path as inputs are ommited and raises an error '''
		malformed_values = ("///","/home//")
		for inputstring in malformed_values:
			self.assertRaises (Shotwell_event2folder.MalformedPathError, Shotwell_event2folder.itemcheck, inputstring)



if __name__ == '__main__':
	unittest.main()

