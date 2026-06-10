# encoding='utf-8'
"""DASH video segment download and playback coordination.

Handles downloading SVC (Scalable Video Coding) video segments from
a DASH server, merging them into decodable H.264 streams via svc_merge,
managing the playback buffer, and coordinating with the adaptive
bitrate strategy for quality selection.
"""
import http.client, httplib2, urllib.request
import subprocess, sys
import re
import os.path
import time
import glob
import queue
import threading
from utils.logger import *
from utils.log_utils import timestamp

try:
    import wget
except ImportError:
    wget = None
class BufferManager:
    """DASH segment download manager and playback coordinator.

    Manages the lifecycle of a DASH video streaming session:
    downloading segments, merging SVC layers, maintaining the playback
    buffer, and coordinating with the adaptive strategy.

    Attributes:
        base_url: Base URL of the DASH server.
        cache_match: Cache path pattern for downloaded files.
        buffer_length: Maximum number of segments to buffer (default 10).
        buffer_list: Thread-safe queue holding pending segments.
    """

    def __init__(self, base_url, cache_match):
        """Initialize the buffer manager.

        Args:
            base_url: Base URL of the DASH server for segment downloads.
            cache_match: Cache path pattern derived from the URL.
        """
        self.base_url = base_url
        self.cache_match = cache_match
        self.buffer_length = 10
        self.buffer_list = queue.Queue(self.buffer_length)
        self.speed=0
        self.lock = threading.RLock()
        self.logger_buf_layer = []


    def download_init_segment(self, directory, dom):
        """Download the initialization segment for the video.

        Args:
            directory: Local directory to save the segment.
            dom: XML DOM element containing the initialization source URL.

        Returns:
            Tuple of (segment_file_path, speed_bps, download_time_seconds).
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        source_url = dom.getElementsByTagName("Initialization")[0].attributes['sourceURL'].value
        ###########################################################
        SegmentBase,speed,time_interval = self.download_wget(source_url)
        return SegmentBase,speed,time_interval


    def download_segment(self, selected_layer, seg_id, list_url):
        """Download all SVC layers for a single segment.

        Downloads layers 0 through selected_layer (inclusive) and
        returns their file paths.

        Args:
            selected_layer: Highest quality layer index to download (0-based).
            seg_id: Segment sequence number.
            list_url: Nested list of segment URLs [seg_index][layer_index].

        Returns:
            Tuple of (file_list, speed_bps, total_download_time_seconds).
        """
        file_list = []
        time_intervals = 0
        selected_layer_length = (int)(selected_layer)+1;
        speed = 0
        for layer_id in range(0,selected_layer_length):
            segment, speed, time_interval = self.download_segment_layer(layer_id,seg_id,list_url)
            time_intervals = time_intervals+time_interval;
            file_list.append(segment)

        return file_list,speed,time_intervals

    def download_segment_layer(self, layer_id, seg_id, list_url):
        """Download a single SVC layer file.

        Args:
            layer_id: Quality layer index.
            seg_id: Segment sequence number.
            list_url: Nested list of segment URLs.

        Returns:
            Tuple of (file_path, speed_bps, download_time_seconds).
        """
        source_url = list_url[seg_id][layer_id]
        segment,speed,time_interval = self.download_wget(source_url)
        return segment, speed, time_interval

    def generate_h264(self, video_name, i, file_list, segment_base, out_name):
        """Merge SVC layer files into a single H.264 segment via svc_merge.

        Appends the merged segment data to the output video file.

        Args:
            video_name: Video name for file path construction.
            i: Segment index (0-based). First segment triggers output file init.
            file_list: List of downloaded SVC layer file paths.
            segment_base: Path to the initialization segment.
            out_name: Path to the concatenated output H.264 file.
        """

        try:
            command = ["python3", "streaming/svc_merge.py"]
            output_seg_name = video_name + "/" + "out_" + video_name + "_seg" + str(i) + ".264"
            command.append(output_seg_name)
            command.append(segment_base)
            for j in file_list:
                command.append(j)
            message = timestamp() + ": Start mux video file"
            logging.info(message)
            sub_t = subprocess.call(command)
            message = timestamp() + ": Mux finished"
            logging.info(message)
            if i == 0:
                if os.path.isfile(out_name):
                    try:
                        os.remove(out_name)
                    except OSError:
                        message = timestamp() + ": Initiate error"
                        logging.error(message)
                        quit()
            f1 = open(out_name, 'ab')
            f2 = open(output_seg_name, 'rb')
            content = f2.read()
            f1.write(content)
            f1.flush()
            os.fsync(f1);
        except IOError:
            message = timestamp() + ": Error: can\'t find file or read data"
            logging.error(message)
        else:
            f1.close()
        return

    def download_wget(self, seg_url):
        """Download a file with retry and mirror fallback.

        Tries primary URL first, retries up to 3 times, then
        falls back to mirror URLs if available.

        Args:
            seg_url: Segment URL relative to base_url.

        Returns:
            Tuple of (file_path, speed_bps, download_time_seconds).
        """
        file_name = os.path.basename(seg_url)
        primary_url = self.base_url + seg_url

        # Mirror URLs (try if primary fails)
        mirrors = []
        if "ftp.itec.aau.at" in self.base_url:
            mirrors.append(self.base_url.replace(
                "ftp.itec.aau.at", "concert.itec.aau.at"))
        urls = [primary_url] + mirrors

        last_error = None
        for url in urls:
            for attempt in range(3):
                try:
                    t2 = time.time()
                    if wget is not None:
                        wget.download(url)
                        file_cache_match = seg_url + "*"
                        file = glob.glob(file_cache_match)[0]
                    else:
                        subprocess.run(
                            ["curl", "-sL", "-o", file_name,
                             "--connect-timeout", "15", "--retry", "2",
                             url],
                            check=True, capture_output=True)
                        file = file_name

                    file_size = float(os.path.getsize(file))
                    t3 = time.time()
                    time_interval = float(t3 - t2)
                    speed = float(file_size * 8 / max(t3 - t2, 0.001))
                    message = "Estimate Speed:" + str(speed / 1024 / 8)
                    logging.info(message)
                    return file, speed, time_interval
                except Exception as e:
                    last_error = e
                    if attempt < 2:
                        time.sleep(1)
                    continue

        raise RuntimeError(
            "Failed to download {} after all retries: {}".format(
                seg_url, last_error))

    def write_list_to_file(self, file_name,list_logger):
        f1 = open(file_name, "w")
        for i in list_logger:
            temp = ""
            for j in i:
                temp = temp +str(j) +"\t"
            temp = temp[0:-1]+"\n"
            f1.write(temp)
        f1.close()
