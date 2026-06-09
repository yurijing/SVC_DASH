"""MPD (Media Presentation Description) XML parser for DASH.

Parses MPD manifest files to extract video metadata: available
quality layers, bandwidth thresholds, segment URLs, frame rate,
and timing information needed for adaptive streaming.
"""
import http.client, httplib2, urllib.request
from xml.dom.minidom import parseString
from urllib.parse import urlparse
import re
import datetime
from logger import *
from log_utils import timestamp

class ParseMpd:
    """Parser for DASH MPD XML files.

    Extracts video metadata including SVC layers, bandwidth
    requirements, segment URLs, and timing parameters.
    """

    def __init__(self):
        """Initialize the MPD parser."""
        pass

    def get_xml(self, url):
        """Fetch and parse XML from a URL.

        Tries urllib first (works in Qt event loops), falls back to curl.

        Args:
            url: The MPD file URL.

        Returns:
            Parsed XML DOM document.
        """
        data = None
        # Try urllib first — avoids subprocess deadlock in Qt event loops
        try:
            import urllib.request
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'DASH-Client/3.0')
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode('utf-8')
        except Exception:
            # Fall back to curl for servers that block Python's User-Agent
            try:
                import subprocess
                result = subprocess.run(
                    ["curl", "-sL", "--connect-timeout", "15", url],
                    capture_output=True, text=True, check=True,
                    stdin=subprocess.DEVNULL, timeout=20)
                data = result.stdout
            except Exception as e:
                message = timestamp() + ": MPD file not found: " + str(e)
                logging.error(message)
                raise
        dom = parseString(data)
        return dom

    def parse_mpd(self, url):
        """Parse MPD and extract all video metadata.

        Args:
            url: The MPD file URL.

        Returns:
            Dict with keys: layer_id, layer_list, data, total_seq,
            durations, width, height, layer_bw, threshold, base_url,
            frame_rate, list_url.
        """
        layer_id = []
        layer_bw = []
        threshold = []
        layer_list = ""
        data = self.get_xml(url)
        list_url=[]
        durations = []
        lay_represent_tag = data.getElementsByTagName('Representation')
        width = lay_represent_tag[0].attributes['width'].value
        height = lay_represent_tag[0].attributes['height'].value
        frame_rate = str(lay_represent_tag[0].attributes['frameRate'].value)
        base_url = data.getElementsByTagName('BaseURL')[0].childNodes[0].nodeValue
        for i in lay_represent_tag:
            tmp = int(i.attributes['id'].value)
            layer_id.append(tmp)
            layer_list = layer_list + i.attributes['id'].value + " "
            temp_bw = float(i.attributes['bandwidth'].value)
            layer_bw.append(temp_bw)

        SegmentList = data.getElementsByTagName("SegmentList")
        for item in SegmentList:
            duration = item.attributes["duration"].value
            durations.append(int(duration))

        total_seq = len(SegmentList[0].getElementsByTagName("SegmentURL"))
        for item in range(0,total_seq):
            list_url.append([]);
        tmp = 0
        for j in range(0, len(layer_id)):
            tmp = tmp + layer_bw[j]
            threshold.append(tmp)
        i = 0;
        for i in range(0,total_seq):
            for layerdom in data.getElementsByTagName("Representation"):
                if len(layer_id) >= int(layerdom.attributes["id"].value):
                    seg_name = layerdom.getElementsByTagName("SegmentURL")[i]
                    file_name = str(seg_name.attributes['media'].value)
                    seg_url = file_name
                    list_url[i].append(seg_url)

        return {"layer_id": layer_id, "layer_list": layer_list, "data": data,
                "total_seq": total_seq, "durations": durations, "width": width,
                "height": height, "layer_bw": layer_bw, "threshold": threshold, "base_url": base_url,"frame_rate":frame_rate,"list_url":list_url}