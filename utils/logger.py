"""Logging configuration for the DASH client.

Sets up multi-level logging to console and file handlers for
error, debug, and mplayer status messages in the DASH video
streaming pipeline.
"""
import logging
import os.path
 
def initialize_logger(output_dir):
	"""Configure the root logger with console and file handlers.

	Creates handlers for console (INFO+), error.log (ERROR+),
	all.log (INFO+), and mplayer.log (WARNING+).

	Args:
	    output_dir: Directory path for log file output.
	"""
	#get main logger to add new specifications. Then set global log level to debug.
	logger = logging.getLogger()
	logger.setLevel(logging.DEBUG)
     
	# create console handler and set level to info
	handler = logging.StreamHandler()
	handler.setLevel(logging.INFO)
	formatter = logging.Formatter("%(levelname)s - %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	# create error file handler and set level to error
	handler = logging.FileHandler(os.path.join(output_dir, "error.log"),"w", encoding=None, delay="true")
	handler.setLevel(logging.ERROR)
	formatter = logging.Formatter("%(levelname)s - %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	# create debug file handler and set level to debug
	handler = logging.FileHandler(os.path.join(output_dir, "all.log"),"w")
	#handler.setLevel(logging.INFO)
	# filter = logging.Filter('down')
	# handler.addFilter(filter)
	handler.setLevel(logging.INFO)
	formatter = logging.Formatter("%(levelname)s - %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	# create debug file handler Mplay tail status
	handler = logging.FileHandler(os.path.join(output_dir, "mplayer.log"), "w", encoding=None, delay="true")
	handler.setLevel(logging.WARNING)
	formatter = logging.Formatter("%(levelname)s - %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)