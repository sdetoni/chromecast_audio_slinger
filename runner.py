#!/usr/bin/python3.8
'''
####################################################
# Written by Steven De Toni 2019
####################################################
'''
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "daemon"))

import daemon.HTTPDaemon  as HTTPDaemon
import daemon.GlobalFuncs as GF
import socket
import sys
import logging

# handle default strings and utf8 and not 7bit ascii
#reload(sys)
#sys.setdefaultencoding('utf8')

# Main web server loop to init, run, shutdown
GF.DaemonRunningState = GF.DAEMON_RUNMODE_RUN
while GF.DaemonRunningState == GF.DAEMON_RUNMODE_RUN:
    # init Config, DB, and Logging
    GF.initGlobalFuncs("./config/daemon.cfg")

    httpPortList  = sorted([int(item) for item in set(GF.Config.getSetting('HTTP_PORT', '').split(',')) if item.strip()])
    httpsPortList = sorted([int(item) for item in set(GF.Config.getSetting('HTTPS_PORT', '').split(',')) if item.strip()])
    lastHTTP = None
    lastHTTPS = None

    if len(httpPortList) > 0:
        lastHTTP = httpPortList[-1]
    if len(httpsPortList) > 0:
        lastHTTPS = httpsPortList[-1]

    thrdDaemon = False
    # Start the HTTP server and run as thread
    if lastHTTP:
        if lastHTTPS:
            thrdDaemon = True
        for httpPort in httpPortList:
            HTTPDaemon.startDaemon (host_name        = GF.Config.getSettingStr  ('HTTP_SERVERNAME',         socket.gethostname()),
                                    port_number      = httpPort,
                                    homeDir          = GF.Config.getSettingStr  ('HTTP_HOME_DIRECTORY',     './webapps'),
                                    homeScriptName   = GF.Config.getSettingStr  ('HTTP_HOME_SCRIPT_NAME',   'index.py'),
                                    mimeTypeFilename = GF.Config.getSettingStr  ('HTTP_MIMETYPES_FILENAME', './config/mimetypes.txt'),
                                    serve_via_ssl    = False,
                                    threaded         = thrdDaemon)

    # Start the HTTPS server, and run as a blocking process
    if lastHTTPS:
        for httpsPort in httpsPortList:
            HTTPDaemon.startDaemon (host_name        = GF.Config.getSettingStr  ('HTTP_SERVERNAME',         socket.gethostname()),
                                    port_number      = httpsPort,
                                    ssl_server_pem   = GF.Config.getSettingStr  ('HTTPS_SSL_SERVER_PEM',    './config/server.pem'),
                                    homeDir          = GF.Config.getSettingStr  ('HTTP_HOME_DIRECTORY',     './webapps'),
                                    homeScriptName   = GF.Config.getSettingStr  ('HTTP_HOME_SCRIPT_NAME',   'index.py'),
                                    mimeTypeFilename = GF.Config.getSettingStr  ('HTTP_MIMETYPES_FILENAME', './config/mimetypes.txt'),
                                    serve_via_ssl    = True,
                                    threaded         = httpsPort != lastHTTPS)

    # TODO: To shutdown HTTPDaemon, call GlobalFuncs.shutdownDaemon(), or GlobalFuncs.restartDaemon()

    logging.info (__name__+" : HTTP Daemon Shutdown ...")
    GF.shutdownGlobalFuncs()

    if GF.DaemonRunningState == GF.DAEMON_RUNMODE_RESTART:
        logging.info(__name__ + " : HTTP Daemon Restarting ...")
        GF.DaemonRunningState = GF.DAEMON_RUNMODE_RUN
