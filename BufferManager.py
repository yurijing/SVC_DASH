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
from time import sleep
import time
import glob
import queue
import threading
from multiprocessing import Process
import datetime
from logger import *
from log_utils import timestamp
import time
from threading import Thread
try:
    from MplayerControl import MplayerControl
except ImportError:
    MplayerControl = None
import queue

try:
    import wget
except ImportError:
    wget = None
from strategy.context import StrategyContext
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
        mplayer: MplayerControl instance for video playback.
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
        if MplayerControl is not None:
            self.mplayer = MplayerControl(self.logger_buf_layer)
        else:
            self.mplayer = None


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

    def _init_context(self, parse_result, strategy_name, total_seq):
        """Initialize the strategy context.

        Args:
            parse_result: Parsed MPD data dict.
            strategy_name: Strategy name string (default "fixed").
            total_seq: Total number of segments.

        Returns:
            StrategyContext instance.
        """
        if strategy_name is None:
            strategy_name = "fixed"
        return StrategyContext(
            name=strategy_name,
            thresholds=parse_result["threshold"],
            buffer_length=self.buffer_length,
            total_seq=total_seq,
        )

    def _start_playback(self, video_name, out_name, frame_rate, parse_result,
                        total_seq, durations):
        """Start the video playback thread for the first segment."""
        t1 = datetime.datetime.now()
        message = str(t1) + "\nStart playing!"
        logging.info(message)
        thread1 = Thread(target=self.mplayer.play_video,
                         args=(out_name, frame_rate,
                               parse_result["width"], parse_result["height"],
                               total_seq, durations[0], self.buffer_list))
        thread1.start()

    def _wait_for_completion(self, ctx):
        """Wait for playback to finish and finalize strategy context."""
        while self.mplayer and self.mplayer.thread_live:
            sleep(1)
        self.write_list_to_file("layerRecord.txt", self.logger_buf_layer)
        ctx.finalize()

    def download_all_segments(self, video_name, parse_result, strategy_name=None):
        """Download all segments and coordinate playback (main entry point).

        Iterates through all segments, using the adaptive strategy to
        select quality layers, downloading and merging SVC data, then
        starts playback and waits for completion.

        Args:
            video_name: Name of the video (used for file paths).
            parse_result: Parsed MPD data dict from ParseMpd.parse_mpd().
            strategy_name: Optional strategy name. Defaults to "fixed".

        Returns:
            None. Results are written to layerRecord.txt and strategy
            convergence data is saved.
        """
        threshold = parse_result["threshold"]
        py_t = [threshold[0]/8/1024,threshold[1]/8/1024,threshold[2]/8/1024,threshold[3]/8/1024]
        list_url = parse_result["list_url"]
        durations = parse_result["durations"]
        total_seq = parse_result["total_seq"]
        frame_rate = parse_result["frame_rate"]
        out_name = video_name + "/" + "out_" + video_name + ".264"

        ctx = self._init_context(parse_result, strategy_name, total_seq)

        #download initsegment
        segment_base, speed, time_interval = self.download_init_segment(video_name, parse_result["data"])
        t0 = datetime.datetime.now()
        message = str(t0) + "\nStart processing!"
        selected_layer = 0
        pre_selected_layer = 0 #  old EL choose
        for i in range(0,total_seq):
            message = (timestamp() + ":\n==================================================\n" +
                       "Start handling segment " + str(i) + ", previous reference speed is: " + str(
                speed / 1024 / 8) +
                       "KB/s")
            logging.info(message)
            '''
            If there is "exit" in the last line of the log file, stop download and stop the software.
            '''
            if self.mplayer is None:
                break
            print(self.mplayer.thread_live)
            if self.mplayer.thread_live == False:
                message = timestamp() + ": Stop downloading"
                logging.info(message)
                print("exit ---")
                break
            selected_layer = ctx.select_layer(i, speed, self.buffer_list.qsize(), threshold)
            message = timestamp() + ": SelectedLayer is: " + str(selected_layer)
            file_list, speed_tmp, time_tmp = self.download_segment(selected_layer,i,list_url)
            speed = speed_tmp
            self.logger_buf_layer.append([speed/8/1024,selected_layer,self.buffer_list.qsize(),threshold[selected_layer]/8/1024])

            '''check for very small interval (in case the file size is very small it will mess up the bandwidth calculation)'''
            if time_tmp > 0.05:
                speed = speed_tmp
            else:
                message = timestamp() + ": file size is too small!"
                logging.info(message)
            message = timestamp() + ": Finish download segment " + str(i)
            logging.info(message)
            self.generate_h264(video_name,i,file_list,segment_base,out_name)
            message = (timestamp() + ": Finish handling segment " + str(i) +
                       "\n==================================================")
            logging.info(message)
            cur_segment = {}
            cur_segment["selected_layer"] = selected_layer;
            cur_segment["duration"] = durations[selected_layer];
            self.buffer_list.put(cur_segment)
            ctx.update_state(self.buffer_list.qsize(), speed)
            if i == 0:
                self._start_playback(video_name, out_name, frame_rate,
                                     parse_result, total_seq, durations)

        self._wait_for_completion(ctx)



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
            command = ["python3", "svc_merge.py"]
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
