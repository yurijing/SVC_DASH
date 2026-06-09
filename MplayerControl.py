"""MPlayer-based video playback controller.

Manages the mplayer subprocess, monitors playback progress
via log file parsing, and handles buffer underrun by pausing
and resuming the video until the next segment is downloaded.
"""
import subprocess, sys
import re
import os.path
from time import sleep
from pykeyboard import PyKeyboard
import datetime
from logger import *
from log_utils import timestamp
import time
import threading
import queue
 
class MplayerControl:

    def __init__(self,logger_pause_record):
        self.thread_live = True
        self.logger_pause_record = logger_pause_record
        self.lock = threading.RLock()

    def play_video(self, video_name, frame_rate, width, height,
                   total_seq, base_duration, buffer_list):
        """Launch mplayer and start the playback control loop.

        Args:
            video_name: Path to the H.264 video file.
            frame_rate: Video frame rate string.
            width: Display width.
            height: Display height.
            total_seq: Total number of segments.
            base_duration: Duration of one segment in frames.
            buffer_list: Thread-safe queue of buffered segments.
        """

        message = timestamp() + ": mplayer open"
        logging.info(message)
        log_name = video_name + ".log"
        f = open(log_name, "wb")

        # -geometry WxH%:50%:50%  = sized window centered on screen
        geometry = "%dx%d%%:50%%:50%%" % (int(width), int(height))

        p = subprocess.Popen(
            ["mplayer", "-fps", frame_rate, "-geometry", geometry, video_name],
            stdout=f, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self.mplayer_controller_switch(log_name,total_seq,base_duration,buffer_list)
        p.communicate(input="q")

    def parse_frame_idx(self, text):
        """Extract the current frame index from mplayer log output.

        Args:
            text: One line of mplayer log output.

        Returns:
            Integer frame index, or None if parsing fails.
        """
        if len(text.split("/")) == 1:
            message = (timestamp() + ": error in frame index parse\n" +
                       "last line in log text is:" + str(text))
            logging.error(message)
            return None
        else:
            tmp1 = text.split("/")[-2]
            tmp = tmp1.split(" ")
            current_frame = tmp[-1]
            if current_frame.isdigit():
                return int(current_frame)
            return None

    def _handle_buffer_underrun(self, buffer_list, cur_segment, tmp_idx,
                                 frame_display, frame_idx, keyboard):
        """Pause playback and wait for the next segment to finish downloading."""
        t0_pause = time.time()
        keyboard.tap_key(' ')  # pause the video
        message = (timestamp() +
                   ": Pause the video and wait for segment download. (frameID: " +
                   str(frame_idx) + ")\n")
        logging.info(message)
        cur_segment = buffer_list.get()
        tmp_idx = tmp_idx + 1
        frame_display = frame_display + cur_segment["duration"]
        t1_pause = time.time()
        interval_pause = float(t1_pause - t0_pause)
        keyboard.tap_key(' ')  # continue the video
        self.logger_pause_record.append(["pause: ", str(interval_pause)])
        logging.info(message)
        return cur_segment, tmp_idx, frame_display

    def mplayer_controller_switch(self, log_name, total_seg, base_duration,
                                   buffer_list):
        """Monitor playback and handle buffer underrun (main control loop).

        Reads mplayer log output to track frame progress. Pauses
        when the buffer is empty and resumes when a segment arrives.

        Args:
            log_name: Path to the mplayer log file.
            total_seg: Total number of segments.
            base_duration: Duration of one segment in frames.
            buffer_list: Buffer queue from BufferManager.
        """
        self.thread_live = True
        keyboard = PyKeyboard()
        tmp_idx = 1
        cur_segment = buffer_list.get()
        frame_display = 48
        while True:
            text = subprocess.check_output(["tail", "-1", log_name])
            if "Exit" in text:
                message = timestamp() + ": " + text
                logging.info(message)
                message = (timestamp() + ": Exit mplayer\n" +
                           "==================================")
                logging.info(message)
                self.thread_live = False
                break

            print(str(text))
            frame_idx = self.parse_frame_idx(text)
            if frame_idx is None:
                continue

            if tmp_idx < total_seg:
                if buffer_list.empty():
                    cur_segment, tmp_idx, frame_display = \
                        self._handle_buffer_underrun(
                            buffer_list, cur_segment, tmp_idx,
                            frame_display, frame_idx, keyboard)
                elif frame_idx + base_duration > frame_display:
                    cur_segment = buffer_list.get()
                    tmp_idx = tmp_idx + 1
                    frame_display = frame_display + cur_segment["duration"]





