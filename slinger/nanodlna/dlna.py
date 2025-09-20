#!/usr/bin/env python3
# encoding: UTF-8

import os
import pkgutil
import re
import sys
from xml.sax.saxutils import escape as xmlescape
import xml.etree.ElementTree as ET

if sys.version_info.major == 3:
    import urllib.request as urllibreq
else:
    import urllib2 as urllibreq

import urllib
import traceback
import logging
import json

ActionXMLS = {
"action-GetPositionInfo" : \
r"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:GetPositionInfo xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:GetPositionInfo>
  </s:Body>
</s:Envelope>""",

"action-GetTransportInfo" : \
r"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:GetTransportInfo xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:GetTransportInfo>
  </s:Body>
</s:Envelope>""",

"action-Pause" : \
r"""<?xml version='1.0' encoding='utf-8'?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:Pause xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Pause>
  </s:Body>
</s:Envelope>""",

"action-Play" : \
r"""<?xml version='1.0' encoding='utf-8'?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>
  </s:Body>
</s:Envelope>""",

"action-SetAVTransportURI" : \
r"""<?xml version="1.0" encoding="utf-8" standalone="yes" ?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{video_url}</CurrentURI>
      <CurrentURIMetaData>{metadata}</CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>""",

"action-Stop" : \
r"""<?xml version='1.0' encoding='utf-8'?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Stop>
  </s:Body>
</s:Envelope>""",

"action-Seek" : \
r"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:Seek xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Unit>REL_TIME</Unit>
      <Target>{target}</Target>
    </u:Seek>
  </s:Body>
</s:Envelope>""",

"control-SetVolume" : \
r"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
      <InstanceID>0</InstanceID>
      <Channel>Master</Channel>
      <DesiredVolume>{DesiredVolume}</DesiredVolume>
    </u:SetVolume>
  </s:Body>
</s:Envelope>""",

"control-SetMute" : \
r"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetMute xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
      <InstanceID>0</InstanceID>
      <Channel>Master</Channel>
      <DesiredMute>{mute}</DesiredMute>
    </u:SetMute>
  </s:Body>
</s:Envelope>""",

"metadata-audio" : \
r'''<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/" xmlns:sec="http://www.sec.co.kr/" xmlns:pv="http://www.pv.com/pvns/">
	<item id="0" parentID="0" restricted="1">
		<upnp:class>object.item.audioItem.musicTrack</upnp:class>
		<dc:title>{title}</dc:title>
		<dc:creator>{creator}</dc:creator>
		<upnp:artist>{artist}</upnp:artist>
		<upnp:albumArtURI>{art_url}</upnp:albumArtURI>
		<dc:date>{date}</dc:date>
		<upnp:album>{album}</upnp:album>
		<upnp:originalTrackNumber>{trackNo}</upnp:originalTrackNumber>
		<res protocolInfo="http-get:*:{mime_type}:*">{audio_url}</res>
	</item>
</DIDL-Lite>''',

"metadata-video" : \
r"""<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/" xmlns:sec="http://www.sec.co.kr/" xmlns:pv="http://www.pv.com/pvns/">
	<item id="0" parentID="0" restricted="1">
		<upnp:class>object.item.videoItem.movie</upnp:class>
		<dc:title>{title}</dc:title>
		<dc:creator>{creator}</dc:creator>
		<upnp:genre>{genre}</upnp:genre>
        <upnp:actor>{actor}</upnp:actor>
        <upnp:director>{director}</upnp:director>
    	<upnp:albumArtURI>{art_url}</upnp:albumArtURI>
		<dc:date>{date}</dc:date>
		<res protocolInfo="http-get:*:{mime_type}:*">{video_url}</res>
	</item>
</DIDL-Lite>"""

}

#==================================================================

def xml_to_dict(xml_string):
    def is_xml(s):
        try:
            ET.fromstring(s)
            return True
        except ET.ParseError:
            return False
    """
    Convert a simple XML SOAP response into a nested dict.
    Tags are mapped to their text, children become sub-dicts.
    """
    def elem_to_dict(elem):
        d = {}
        # if element has children, recurse
        if list(elem):
            for child in elem:
                m = re.search(r"^(\{.*\})(.*)", child.tag)
                if m:
                    d[m.group(2)] = elem_to_dict(child)
                else:
                    d[child.tag] = elem_to_dict(child)
        else:
            d = elem.text or ""
            if is_xml(d):
                d = xml_to_dict(d)
        return d
    root = ET.fromstring(xml_string)
    return elem_to_dict(root)

def send_dlna_action(device, data, action):
    logging.debug("Sending DLNA Action: {}".format(
        json.dumps({
            "action": action,
            "device": device,
            "data": data
        })
    ))

    action_data = ActionXMLS [f"action-{action}"]
    if data:
        action_data = action_data.format(**data)
    action_data = action_data.encode("UTF-8")

    headers = {
        "Content-type": "text/xml; charset=utf-8",
        "Content-Length": "{0}".format(len(action_data)),
        "Connection": "close",
        "user-Agent": "Android/15 UPnP/1.0 BubbleUPnP/3.4.12",
        "SOAPACTION": "\"{0}#{1}\"".format(device["st"], action)
    }

    logging.getLogger().level = logging.DEBUG
    logging.debug("Sending DLNA Request: {}".format(
        json.dumps({
            "url": device["action_url"],
            "data": action_data.decode("UTF-8"),
            "headers": headers
        })
    ))

    try:
        request = urllibreq.Request(device["action_url"], action_data, headers)
        urllibreq.urlopen(request)
        logging.debug("Request sent")
    except urllib.error.HTTPError as err:
        errBody = err.read().decode('utf-8')
        logging.error (f"DLNA Response Error: {errBody}")
        logging.error("Unknown error sending request: {}".format(
            json.dumps({
                "url": device["action_url"],
                "data": action_data.decode("UTF-8"),
                "headers": headers,
                "error": traceback.format_exc(),
                "errorBody" : errBody
            })
        ))

def send_dlna_control(device, data, action):
    logging.debug("Sending DLNA Action: {}".format(
        json.dumps({
            "action": action,
            "device": device,
            "data": data
        })
    ))

    action_data = ActionXMLS [f"control-{action}"]
    if data:
        action_data = action_data.format(**data)
    action_data = action_data.encode("UTF-8")

    headers = {
        "Content-Type": "text/xml; charset=\"utf-8\"",
        "Content-Length": "{0}".format(len(action_data)),
        "Connection": "close",
        "SOAPACTION": "\"{0}#{1}\"".format(device["render_control_st"], action)
    }

    logging.getLogger().level = logging.DEBUG
    logging.debug("Sending DLNA Request: {}".format(
        json.dumps({
            "url": device["render_control_url"],
            "data": action_data.decode("UTF-8"),
            "headers": headers
        })
    ))

    try:
        request = urllibreq.Request(device["render_control_url"], action_data, headers)
        urllibreq.urlopen(request)
        logging.debug("Request sent")
    except urllib.error.HTTPError as err:
        errBody = err.read().decode('utf-8')
        logging.error (f"DLNA Response Error: {errBody}")
        logging.error("Unknown error sending request: {}".format(
            json.dumps({
                "url": device["render_control_url"],
                "data": action_data.decode("UTF-8"),
                "headers": headers,
                "error": traceback.format_exc(),
                "errorBody" : errBody
            })
        ))

def get_playback_info(device):
    """
    Query DLNA device for playback position, track length, and related info.

    Returns dict like:
      {
        "TrackURI": "...",
        "RelTime": "00:01:23",
        "TrackDuration": "00:03:45"
      }
    or {} if failed.
    """
    try:
        # Build the SOAP body from template
        action_data = ActionXMLS["action-GetPositionInfo"].encode("UTF-8")

        headers = {
            "Content-Type": "text/xml; charset=\"utf-8\"",
            "Content-Length": "{0}".format(len(action_data)),
            "Connection": "close",
            "SOAPACTION": "\"{0}#{1}\"".format(device["st"], "GetPositionInfo")
        }

        request = urllibreq.Request(device["action_url"], action_data, headers)
        with urllibreq.urlopen(request) as response:
            resp_xml = response.read().decode("utf-8")

        # Extract some useful fields
        import re
        info = {}
        for tag in ["TrackURI", "RelTime", "TrackDuration"]:
            m = re.search(r"<{0}>(.*?)</{0}>".format(tag), resp_xml)
            if m:
                info[tag] = m.group(1)
        #return info
        return xml_to_dict(resp_xml)

    except Exception as e:
        logging.error("Error getting playback info: %s", traceback.format_exc())
        return None

def get_play_status(device):
    """
    Query DLNA device for current playback status.

    Returns one of: "PLAYING", "PAUSED_PLAYBACK", "STOPPED", or None if unknown.
    """
    try:
        # Build the SOAP body from template
        action_data = ActionXMLS["action-GetTransportInfo"].encode("UTF-8")
        headers = {
            "Content-Type": "text/xml; charset=\"utf-8\"",
            "Content-Length": "{0}".format(len(action_data)),
            "Connection": "close",
            "SOAPACTION": "\"{0}#{1}\"".format(device["st"], "GetTransportInfo")
        }

        request = urllibreq.Request(device["action_url"], action_data, headers)
        with urllibreq.urlopen(request) as response:
            resp_xml = response.read().decode("utf-8")

        # crude parse – just pull out <CurrentTransportState> tag
        import re
        m = re.search(r"<CurrentTransportState>(.*?)</CurrentTransportState>", resp_xml)
        if m:
            return xml_to_dict(resp_xml)
        return None

    except Exception as e:
        logging.error("Error getting play status: %s", traceback.format_exc())
        return None

#==================================================================

def play(device, url, mime_type, title="", creator="", album="", art_url=""):
    # art url dodgy with parameters!
    #url = "http://192.168.20.16:8008/slinger/a.flac"
    #art_url = ""

    play_data = {"audio_url":  (url),
                 "video_url":  (url),
                 "type_video": mime_type,
                 "title":      title,
                 "creator":    creator,
                 "artist":     creator,
                 "album":      album,
                 "date":       "",
                 "trackNo":    0,
                 "genre":      "",
                 "actor":      "",
                 "director":   "",
                 "art_url":    (art_url),
                 "mime_type":  mime_type,
                 "metadata":   ""}

    if mime_type.split('/')[0].strip().lower() in ('audio',):
        audio_metadata = ActionXMLS["metadata-audio"]
        audio_metadata = audio_metadata.format(**play_data)
        play_data["metadata"] = xmlescape(audio_metadata)
    if mime_type.split('/')[0].strip().lower() in ('video',):
        video_metadata = ActionXMLS["metadata-video"]
        video_metadata = video_metadata.format(**play_data)
        play_data["metadata"] = xmlescape(video_metadata)

    play_data["audio_url"] = xmlescape(url)
    play_data["video_url"] = xmlescape(url)
    play_data["art_url"]   = xmlescape(art_url)

    logging.debug("Created video data: {}".format(json.dumps(play_data)))

    logging.debug("Setting Video URI")
    send_dlna_action(device, play_data, "SetAVTransportURI")
    logging.debug("Playing video")
    send_dlna_action(device, play_data, "Play")\

def resume(device):
    logging.debug("Resume (From Pause) device: {}".format(
        json.dumps({
            "device": device
        }, indent=4)
    ))

    send_dlna_action(device, None, "Play")

def seek(device, pos_seconds):
    pos_seconds = int(abs(pos_seconds))
    secs = int(pos_seconds % 60)
    pos_seconds -= secs
    minsTotal = pos_seconds / 60
    mins = int(minsTotal % 60)
    minsTotal -= mins
    hrs = int(minsTotal / 60)
    target = f"{hrs:02d}:{mins:02d}:{secs:02d}"

    logging.debug("seek device: {}".format(
        json.dumps({
            "device": device,
            "target": target
        })
    ))

    send_dlna_action(device, {"target" : target }, "Seek")

def pause(device):
    logging.debug("Pausing device: {}".format(
        json.dumps({
            "device": device
        })
    ))
    send_dlna_action(device, None, "Pause")

# vol : 0 - 100
def volume(device, vol):
    logging.debug("volume device: {}".format(
        json.dumps({
            "device": device,
            "DesiredVolume" : vol
        })
    ))

    send_dlna_control(device, {"DesiredVolume" : vol}, "SetVolume")

def muted (device, mute):
    if mute:
        mute = 1
    else:
        mute = 0
    logging.debug("Muted device: {}".format(
        json.dumps({
            "device": device,
            "mute" : mute
        })
    ))
    send_dlna_control(device, {"mute" : mute}, "SetMute")

def stop(device):
    logging.debug("Stopping device: {}".format(
        json.dumps({
            "device": device
        })
    ))
    send_dlna_action(device, None, "Stop")
