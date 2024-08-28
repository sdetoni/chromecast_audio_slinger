import logging
import logging.handlers
import sys
import ConfigLoader
import HTTPDaemon
import DBIO

# ------------------ LOGGING FUNCS ----------------------------

LOGLEVELS = {'debug':    logging.DEBUG,
             'info':     logging.INFO,
             'warning':  logging.WARNING,
             'error':    logging.ERROR,
             'critical': logging.CRITICAL,
             'none':     logging.NOTSET}

def removeLogging ():
    while loggingActive ():
        root = logging.getLogger()
        h = root.handlers[0]
        logging.debug('removing handler %s' % str(h))
        root.removeHandler(h)

def loggingActive ():
    return len(logging.getLogger().handlers) > 0

def setLogging (logFilename, logLevel, logSize, logNum, multiFileLogging=False):
    class ColouredLogFormatter(logging.Formatter):
        RESET = '\x1B[0m'
        RED = '\x1B[31m'
        YELLOW = '\x1B[33m'
        BRGREEN = '\x1B[01;32m'  # grey in solarized for terminals
        def format(self, record):
            message  = logging.Formatter.format(self, record)
            level_no = record.levelno
            if level_no >= logging.CRITICAL:
                colour = self.RED
            elif level_no >= logging.ERROR:
                colour = self.RED
            elif level_no >= logging.WARNING:
                colour = self.YELLOW
            elif level_no >= logging.INFO:
                colour = self.RESET
            elif level_no >= logging.DEBUG:
                colour = self.BRGREEN
            else:
                colour = self.RESET

            message = colour + message + self.RESET
            return message
    # end class

    root = logging.getLogger()

    if ((multiFileLogging == False) and loggingActive()):
        logging.error ("HTTPDaemon.setLogging : cant append more than one log unless multiFileLogging is set, or call HTTPDaemon.removeLogging()")
        return

    root.setLevel(level=logLevel)

    # add stdout logging as well as file logging...
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(ColouredLogFormatter("%(asctime)s:%(levelname)s:%(message)s", datefmt='%H:%M:%S'))
    ch.setLevel(logLevel)
    root.addHandler(ch)

    try:
        rotloghand = logging.handlers.RotatingFileHandler(logFilename, maxBytes=logSize, backupCount=logNum)
        rotloghand.setFormatter(ColouredLogFormatter("%(asctime)s:%(levelname)s:%(message)s", datefmt='%H:%M:%S'))
        root.addHandler(rotloghand)
    except Exception as e:
        logging.error(f"Failed setting file logging for {logFilename}")
        logging.error(f"Error {str(e)}")


# ------------------ Web Session Authentication ----------------------------

# Var set as part of initGlobalFuncs()
AuthSessionCOOKIEID      = None
AuthAdminSessionCOOKIEID = None

def IsAdminUser (httpd):
    return AuthenticateValidateAdminSession(httpd, False)

def AuthenticateAnySession (httpd):
    if not AuthenticateValidateSession (httpd, False):  # if normal login is not valid
        return AuthenticateValidateAdminSession (httpd) # check if admin login is valid, if not, send 401 password login req
    return True

def AuthenticateGetUsers (usrCfgID):
    usrpwDict = {}
    for usr in Config.getSettingStr(usrCfgID).split(","):
        try:
            usrpw               = usr.split(":", 1)
            usrpwDict[usrpw[0]] = usrpw[1]
        except:
            pass
    return usrpwDict

def AuthenticateValidateSession (httpd, sendHTTPLoginHeaderReq = True):
    # Check if there is a cookie session, if so update it ...
    tstCookie = False
    if httpd.sessionCookieJar and AuthSessionCOOKIEID in httpd.sessionCookieJar.keys():
        tstCookie = httpd.sessionCheckUpdate (httpd.sessionCookieJar[AuthSessionCOOKIEID].value)

    if not tstCookie:
        user_pass = httpd.authBASIC_getUserPasswd ()
        if not user_pass:
            if sendHTTPLoginHeaderReq:
                httpd.do_HEAD(statusCode=401, turnOffCache=True, otherHeaderDict={'WWW-Authenticate':'Basic'})
            return False

        authOK = False
        for usr, pw in AuthenticateGetUsers ('AUTH_USERS').items():
            if ((usr == "") or (pw == "")):
                continue

            if ((usr == user_pass['username']) and  (pw == user_pass['password'])):
                authOK = True
                break

        if not authOK:
            if sendHTTPLoginHeaderReq:
                httpd.do_HEAD(statusCode=401, turnOffCache=True, otherHeaderDict={'WWW-Authenticate':'Basic'})
            return False

        # Create a new cookie session
        sessID = httpd.sessionCreate (timeout=60*5)
        httpd.redirect(httpd.path, True, otherHeaderDict={'Set-Cookie': AuthSessionCOOKIEID + '=' + sessID})
        return False
    return True

def AuthenticateValidateAdminSession (httpd, sendHTTPLoginHeaderReq = True):
    # Check if there is a cookie session, if so update it ...
    tstCookie = False
    if httpd.sessionCookieJar and AuthAdminSessionCOOKIEID in httpd.sessionCookieJar.keys():
        tstCookie = httpd.sessionCheckUpdate (httpd.sessionCookieJar[AuthAdminSessionCOOKIEID].value)

    if not tstCookie:
        user_pass = httpd.authBASIC_getUserPasswd ()
        if not user_pass:
            if sendHTTPLoginHeaderReq:
                httpd.do_HEAD(statusCode=401, turnOffCache=True, otherHeaderDict={'WWW-Authenticate':'Basic'})
            return False

        authOK = False
        for usr, pw in AuthenticateGetUsers ('AUTH_ADMIN_USERS').items():
            if ((usr == "") or (pw == "")):
                continue

            if ((usr == user_pass['username']) and (pw == user_pass['password'])):
                authOK = True
                break

        if not authOK:
            if sendHTTPLoginHeaderReq:
                httpd.do_HEAD(statusCode=401, turnOffCache=True, otherHeaderDict={'WWW-Authenticate': 'Basic'})
            return False

        # Create a new cookie session
        sessID = httpd.sessionCreate (timeout=60*5)
        httpd.redirect(httpd.path, True, otherHeaderDict={'Set-Cookie': AuthAdminSessionCOOKIEID + '=' + sessID})
        return False
    return True

def AuthenticateLogoutUser (httpd):
    if httpd.sessionCookieJar and AuthAdminSessionCOOKIEID in httpd.sessionCookieJar.keys():
        httpd.sessionRemoveItem (httpd.sessionCookieJar[AuthAdminSessionCOOKIEID].value)
        httpd.do_HEAD(turnOffCache=True, otherHeaderDict={'Set-Cookie': AuthAdminSessionCOOKIEID + '='}, closeHeader=False)
    elif httpd.sessionCookieJar and AuthSessionCOOKIEID in httpd.sessionCookieJar.keys():
        httpd.sessionRemoveItem (httpd.sessionCookieJar[AuthSessionCOOKIEID].value)
        httpd.do_HEAD(turnOffCache=True, otherHeaderDict={'Set-Cookie': AuthSessionCOOKIEID + '='}, closeHeader=False)
    return True

def AuthenticateGetUsername (httpd):
    if (AuthenticateAnySession(httpd)):
        return httpd.authBASIC_getUserPasswd()['username']

# ------------------ Shutdown/Restart ----------------------------

DAEMON_RUNMODE_RUN, DAEMON_RUNMODE_STOPEXIT, DAEMON_RUNMODE_RESTART = range(3)
DaemonRunningState = None
DaemonServerIpAddrs = ''

def shutdownDaemon():
    global DaemonRunningState
    DaemonRunningState = DAEMON_RUNMODE_STOPEXIT
    HTTPDaemon.stopDaemon()


def restartDaemon():
    global DaemonRunningState
    DaemonRunningState = DAEMON_RUNMODE_RESTART
    HTTPDaemon.stopDaemon()

# ------------------ Init Logging/Config/DB Objects ----------------------------

Config = None

def initGlobalFuncs (configFilename):
    global Config, DB, AuthSessionCOOKIEID, AuthAdminSessionCOOKIEID
    Config = ConfigLoader.ConfigLoader (configFilename)

    setLogging(logFilename = Config.getSettingStr('LOGGING_DIR', './logs') + '/' + Config.getSettingStr('HTTP_LOGNAME', 'httpdaemon.log'),
               logLevel    = LOGLEVELS[Config.getSettingStr('LOGGING_LEVEL', 'debug').lower()],
               logSize     = Config.getSettingValue('LOGGING_SIZE', '((1024 * 100) * 100)'),
               logNum      = Config.getSettingValue('LOGGING_NO',   '10'))

    # Cookie/Session Authentication
    AuthSessionCOOKIEID      = Config.getSettingStr('AUTH_USER_COOKIEID',  'UserAuthID')
    AuthAdminSessionCOOKIEID = Config.getSettingStr('AUTH_ADMIN_COOKIEID', 'AdminAuthID')

def shutdownGlobalFuncs ():
    pass