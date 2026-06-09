# DEPRECATED: This CLI entry point is superseded by dash_qt/main.py
# See dash_qt/ for the new PySide6 Qt GUI application.
"""DASH client entry point for SVC video streaming.

Connects to a DASH server, fetches and parses the MPD manifest,
downloads SVC video segments with adaptive quality selection,
and plays back the assembled H.264 video via mplayer.
"""
from xml.dom.minidom import parseString
from urllib.parse import urlparse
from threading import Thread
import subprocess, sys
import re
import os.path
from time import sleep
import time
import queue
import threading
from multiprocessing import Process
from ParseMpd import ParseMpd
from BufferManager import BufferManager
from MplayerControl import MplayerControl
from logger import *
from log_utils import timestamp, sanitize_filename, validate_mpd_url
import datetime

#
#  mpd_url = "http://concert.itec.aau.at/SVCDataset/dataset/mpd/factory-I-360p.mpd"		#for example  http://localhost/video/video_1.264.mpd		#video/video_1.264.mpd
# SECURITY: Hardcoded server URL. Consider using an environment variable.
#   mpd_url = os.environ.get("MPD_URL", "http://localhost:8087/...")
mpd_url = "http://192.168.228.129:8087/SVCDataset/dataset/mpd/BBB-I-360p.mpd"
validate_mpd_url(mpd_url)
mpd_name = sanitize_filename(mpd_url.split('/')[-1])  # e.g. BBB-I-360p.mpd			#video_1.264.mpd
video_name = sanitize_filename(mpd_name.split('.mpd')[0])
action = "-play"
idx  = 0
while idx < 1:
	if(action=="-play"):
		'''
		Read and parse information in mpd file
		'''
		print("start processing!")
		parse_mpd_module = ParseMpd()
		parse_result = parse_mpd_module.parse_mpd(mpd_url)
		base_url = parse_result["base_url"];
		cache_match = base_url.split("//")[-1]
		cache_match = cache_match.replace("/", ",")
		cache_match = cache_match.replace(":", ",")
		buffer = BufferManager(base_url,cache_match)
		log_path = os.getcwd() + "/log"
		if not os.path.exists("log"):
			os.makedirs("log")
		initialize_logger(log_path)
		t0 = datetime.datetime.now()
		message = str(t0) + "\nStart processing!"
		logging.info(message)
		# print "start processing!"
		message = (timestamp() + ":\n========================================================\n" +
				   "Video information:"+video_name+"\n" + "Video resolution is:" + parse_result["width"] + "x" + parse_result["height"] +
				   "\nLayerID is: " + parse_result["layerList"] + "\nBandwidth requirement for each layer is: " +
				   str(parse_result["layerBW"]) + " bits/s" + "\nSegment number is: " + str(parse_result["totalSeq"]) +
				   "\nDuration of each segment is: " + str(parse_result["durations"][0]) + " frames\n" +
				   "========================================================")
		logging.info(message)
		'''Download each segment according to segCheckList'''
		buffer.download_all_segments(video_name, parse_result)


	elif(action=="-detail"):
		'''
		Read and parse information in mpd file
		'''
		parse_mpd_module = ParseMpd()
		parse_result = parse_mpd_module.parse_mpd(mpd_url)
		print("video resolution is:" + parse_result["width"] + "x" + parse_result["height"])
		print("layerID is: " + parse_result["layerList"])
		print("bandwidth requirement for each layer is: " + str(parse_result["layerBW"]))
		print("Segment number is: " + str(parse_result["totalSeq"]))
		print("Durations of each segment is: " + str[parse_result["durations"][0]] + " frames")
	else :
		print("Action Wrong !!")
	idx  = idx + 1

