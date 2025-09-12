import slinger.SlingerGlobalFuncs as SGF
import json
import pychromecast
import threading

self = eval('self'); output = self.output

postData = self.getCGIParametersFormData ()
if not "action"     in postData: postData["action"]     = ''

if postData["action"] in ('get_chromecasts', 'get_chromecasts_forced_scan'):
    if postData["action"] == 'get_chromecasts_forced_scan':
        # Preload the cache for casting objects
        thrdList = []
        thrdList.append(threading.Thread(target=SGF.getCachedChromeCast, kwargs={'force': True, 'wait' : True}))
        thrdList.append(threading.Thread(target=SGF.getCachedDLNA, kwargs={'force': True, 'wait' : True}))
        for thread in thrdList:
            thread.start()
        for thread in thrdList:
            thread.join()

    ccDevices = []
    for cc in SGF.getCachedChromeCast():
        if not cc or isinstance(cc, pychromecast.discovery.CastBrowser): continue
        ccDevices.append({'uuid' : str(cc[0].uuid), 'friendly_name' : str(cc[0].cast_info.friendly_name)} )

    for dlna in SGF.getCachedDLNA():
        ccDevices.append({'uuid' : str(dlna["uuid"]), 'friendly_name' : str(dlna["friendly_name"])})

    output(json.dumps(ccDevices, indent=4))
    exit(0)
