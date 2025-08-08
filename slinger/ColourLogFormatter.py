import logging

from threading import Thread, Lock
ReviewBufferMUTEX = Lock()

class ColouredLogFormatter(logging.Formatter):
    RESET   = '\x1B[0m'
    RED     = '\x1B[31m'
    YELLOW  = '\x1B[33m'
    BLUE    = '\x1B[34m'
    BRGREEN = '\x1B[01;32m'  # grey in solarized for terminals

    # store 100 lines of log temporarily in memory
    lastMessage      = ''
    reviewBufferIdx  = 0
    reviewBufferSize = 1000
    reviewBuffer     = []
    RB_RTNTYPE_NONE, RB_RTNTYPE_NORM, RB_RTNTYPE_HTML  = list(range(3))

    redactionObjInst  = None
    redactionFunc     = None
    redactionRepl     = ""

    # set the function call [def stringRedaction (self, str, redaction="### REDACTED ###")]
    def setRedactionFunctionCall (self, funcMethodCall, objInstance=None, redaction="### REDACTED ###"):
        self.redactionObjInst = objInstance
        self.redactionFunc    = funcMethodCall
        self.redactionRepl    = redaction
        pass

    # return the most recent logs in the buffer
    def dumpLogReviewBuffer (self, rtnListType = RB_RTNTYPE_NONE, startIdx=0):
        if len(self.reviewBuffer) <= 0:
            return []

        ReviewBufferMUTEX.acquire()
        try:
            # calculate where to read from in the buffer list
            if startIdx > self.reviewBufferIdx:
                startIdx = self.reviewBufferIdx
            endIdx = len(self.reviewBuffer) - (self.reviewBufferIdx - startIdx)

            # check list/array boundaries
            if endIdx > len(self.reviewBuffer):
                endIdx = len(self.reviewBuffer)-1
            elif endIdx < 0:
                endIdx = 0

            if rtnListType == self.RB_RTNTYPE_NORM:
                return self.reviewBuffer[endIdx:]
            elif rtnListType == self.RB_RTNTYPE_HTML:
                l = self.reviewBuffer[endIdx:]
                hl = []
                for i in l:
                    # Replace html tags with &lt; and &gt;
                    i = i.replace ('<', '&lt;')
                    i = i.replace ('>', '&gt;')

                    if i.find(self.RED) >= 0:
                        i = i.replace (self.RED,     '<div style="color:#b30000">') + '</div>'
                    elif i.find(self.YELLOW) >= 0:
                        i = i.replace (self.YELLOW,  '<div style="color:#c18800">') + '</div>'
                    elif i.find(self.BRGREEN) >= 0:
                        i = i.replace (self.BRGREEN, '<div style="color:#009c00">') + '</div>'
                    elif i.find(self.BLUE) >= 0:
                        i = i.replace (self.BLUE,    '<div style="color:#0018ff">') + '</div>'
                    else:
                        i = '<div>' + i + '</div>'
                    i = i.replace (self.RESET, '')
                    hl.append(i)

                # if empty list, send last index in list with an empty line
                if len(hl) <= 0:
                    hl.append('[' +str(self.reviewBufferIdx-1) +']')
            return hl
        finally:
            ReviewBufferMUTEX.release()

    def format(self, record):
        message = logging.Formatter.format(self, record)

        # dynamically call logging redactions on output string
        if (self.redactionObjInst and self.redactionFunc):
            message = getattr(self.redactionObjInst, self.redactionFunc)(message, self.redactionRepl)
        elif (self.redactionFunc):
            message = getattr(globals(), self.redactionFunc)(message, self.redactionRepl)

        level_no = record.levelno
        if level_no >= logging.CRITICAL:
            colour = self.RED
        elif level_no >= logging.ERROR:
            colour = self.RED
        elif level_no >= logging.WARNING:
            colour = self.YELLOW
        elif level_no >= logging.INFO:
            colour = self.BLUE
        elif level_no >= logging.DEBUG:
            colour = self.BRGREEN
        else:
            colour = self.RESET

        message = colour + message + self.RESET

        if (message.encode("utf-8").hex() != self.lastMessage.encode("utf-8").hex()):
            self.lastMessage = message
            ReviewBufferMUTEX.acquire()
            try:
                self.reviewBuffer.append('['+str(self.reviewBufferIdx)+']' + message)
                self.reviewBufferIdx = self.reviewBufferIdx + 1
            finally:
                ReviewBufferMUTEX.release()
            if len(self.reviewBuffer) > self.reviewBufferSize:
                del self.reviewBuffer[0:len(self.reviewBuffer)-self.reviewBufferSize]
        return message