from http import server as BaseHTTPServer
from http.server import HTTPServer
from http import cookies
from socketserver import ThreadingMixIn
import urllib
from urllib.parse import urlparse
import re
import traceback
import cgi
import logging
import socket
import hashlib
import random
import time
import html
import ssl
import base64
import sys
import os
import datetime
import tempfile
import io

# HTTPDaemon instances created
SERVERS = []

# -------------------------------------------------------------------

class FieldStorage (cgi.FieldStorage):

    def make_file(self):
        return tempfile.TemporaryFile("wb+")


# -------------------------------------------------------------------

def nvl (param, ifNone=''):
    if not param:
        return ifNone
    return param

def strSubtract (a, b):
    return re.sub('^' + re.escape(nvl(b)), '', nvl(a, ''))

# -------------------------------------------------------------------

class TemplateLoad ():
    class LexItem:
        owner   = None
        type    = None
        data    = None
        lineNo  = -1
        charPos = -1

        def __init__(self, owner, type, data, lineNo, charPos):
            self.owner = owner; self.type = type; self.data = data; self.lineNo = lineNo; self.charPos = charPos

        def typeStr(self):
            return self.owner.tokens[self.type]["tok"]

        def cleanDataStr (self):
            return self.data.strip().replace(self.owner.NLdumb, ' ').replace(self.owner.NLdumber, ' ').replace(self.owner.NL, ' ')

        codeBlockParentLexItem = None

    # ------------------------------------------------------------

    # Newline string terminator types
    NL = "\n"; NLdumb = "\r\n"; NLdumber = "\r"

    # Tokens ID
    T_STRING,          T_BLOCK_CODE,         T_PYBLOCK_CODE,      T_COMMENTBLOCK_CODE,  T_VERBATIMBLOCK_CODE, T_OPEN_CMDBLOCK, T_CLOSE_CMDBLOCK, T_OPEN_VARBLOCK, T_CLOSE_VARBLOCK, \
    T_OPEN_PYBLOCK,    T_CLOSE_PYBLOCK,      T_OPEN_COMMENTBLOCK, T_CLOSE_COMMENTBLOCK, T_OPEN_VERBATIMBLOCK, T_CLOSE_VERBATIMBLOCK, \
    T_OPER_IF,         T_OPER_ELIF,          T_OPER_ELSE,         T_OPER_ENDIF,         T_OPER_BLOCK,         T_OPER_ENDBLOCK,  T_OPER_INCLUDE,  T_OPER_EXTENDS, \
    T_OPER_AUTOESCAPE, T_OPER_ENDAUTOESCAPE, T_OPER_AUTOTRIM,     T_OPER_ENDAUTOTRIM, \
    T_OPER_FOR,        T_OPER_ENDFOR,        T_OPER_WHILE,        T_OPER_ENDWHILE, \
    T_OPER_CYCLE,      T_OPER_CYCLERESET,    T_OPER_TAG,          T_OPER_RELFILENAME, T_OPER_FILENAME = range (36)

    # Token info
    tokens = {T_STRING:               {"tok":"[HTML_CODE]",         "match":None,                     "depd":None},
              T_BLOCK_CODE:           {"tok":"[BLOCK_CODE]",        "match":None,                     "depd":None},
              T_PYBLOCK_CODE:         {"tok":"[PYBLOCK_CODE]",      "match":None,                     "depd":None},
              T_COMMENTBLOCK_CODE:    {"tok":"[COMMENTBLOCK_CODE]", "match":None,                     "depd":None},
              T_VERBATIMBLOCK_CODE:   {"tok":"[VERBATIMBLOCK_CODE]","match":None,                     "depd":None},

              T_OPEN_CMDBLOCK:        {"tok":"{%",                  "match":None,                     "depd":(T_CLOSE_CMDBLOCK,)},
              T_CLOSE_CMDBLOCK:       {"tok":"%}",                  "match":None,                     "depd":None},
              T_OPEN_VARBLOCK:        {"tok":"{{",                  "match":None,                     "depd":(T_CLOSE_VARBLOCK,)},
              T_CLOSE_VARBLOCK:       {"tok":"}}",                  "match":None,                     "depd":None},
              T_OPEN_PYBLOCK:         {"tok":"{$",                  "match":None,                     "depd":(T_CLOSE_PYBLOCK,)},
              T_CLOSE_PYBLOCK:        {"tok":"$}",                  "match":None,                     "depd":None},
              T_OPEN_COMMENTBLOCK:    {"tok":"{#",                  "match":None,                     "depd":(T_CLOSE_COMMENTBLOCK,)},
              T_CLOSE_COMMENTBLOCK:   {"tok":"#}",                  "match":None,                     "depd":None},
              T_OPEN_VERBATIMBLOCK:   {"tok":"{*",                  "match":None,                     "depd":(T_CLOSE_VERBATIMBLOCK,)},
              T_CLOSE_VERBATIMBLOCK:  {"tok":"*}",                  "match":None,                     "depd": None},

              T_OPER_IF:              {"tok":"if",                  "match":(T_BLOCK_CODE,),          "depd":(T_OPER_ELIF, T_OPER_ELSE, T_OPER_ENDIF)},
              T_OPER_ELIF:            {"tok":"elif",                "match":(T_BLOCK_CODE,),          "depd":(T_OPER_ELIF, T_OPER_ELSE, T_OPER_ENDIF)},
              T_OPER_ELSE:            {"tok":"else",                "match":None,                     "depd":(T_OPER_ENDIF,)},
              T_OPER_ENDIF:           {"tok":"endif",               "match":None,                     "depd":None},
              T_OPER_BLOCK:           {"tok":"block",               "match":(T_CLOSE_CMDBLOCK,),      "depd":(T_OPER_ENDBLOCK,)},
              T_OPER_ENDBLOCK:        {"tok":"endblock",            "match":None,                     "depd":None},
              T_OPER_INCLUDE:         {"tok":"include",             "match":(T_BLOCK_CODE,),          "depd":None},
              T_OPER_EXTENDS:         {"tok":"extends",             "match":(T_BLOCK_CODE,),          "depd":None},
              T_OPER_RELFILENAME:     {"tok":"rel_filename",        "match": None,                    "depd":None},
              T_OPER_FILENAME:        {"tok":"filename",            "match": None,                    "depd":None},

              T_OPER_AUTOTRIM:        {"tok":"autotrim",            "match":(T_BLOCK_CODE,),          "depd":(T_OPER_ENDAUTOTRIM,)},
              T_OPER_ENDAUTOTRIM:     {"tok":"endautotrim",         "match":(T_BLOCK_CODE,),          "depd":None},
              T_OPER_AUTOESCAPE:      {"tok":"autoescape",          "match":(T_BLOCK_CODE,),          "depd":(T_OPER_ENDAUTOESCAPE,)},

              T_OPER_ENDAUTOESCAPE:   {"tok":"endautoescape",       "match":None,                     "depd":None},
              T_OPER_FOR:             {"tok":"for",                 "match":(T_BLOCK_CODE,),          "depd":(T_OPER_ENDFOR,)},
              T_OPER_ENDFOR:          {"tok":"endfor",              "match":None,                     "depd":None},
              T_OPER_WHILE:           {"tok":"while",               "match":(T_BLOCK_CODE,),          "depd":(T_OPER_ENDWHILE,)},
              T_OPER_ENDWHILE:        {"tok":"endwhile",            "match":(T_BLOCK_CODE,),          "depd":None},

              T_OPER_CYCLE:           {"tok":"cycle",               "match":None,                     "depd":None},
              T_OPER_CYCLERESET:      {"tok":"cyclereset",          "match":None,                     "depd":None},
              T_OPER_TAG:             {"tok":"tag",                 "match":None,                     "depd":None}
              }
    tokenTags = {"OPEN_CMDBLOCK":tokens[T_OPEN_CMDBLOCK]["tok"],           "CLOSE_CMDBLOCK":tokens[T_CLOSE_CMDBLOCK]["tok"],
                 "OPEN_VARBLOCK":tokens[T_OPEN_VARBLOCK]["tok"],           "CLOSE_VARBLOCK":tokens[T_CLOSE_VARBLOCK]["tok"],
                 "OPEN_PYBLOCK":tokens[T_OPEN_PYBLOCK]["tok"],             "CLOSE_PYBLOCK":tokens[T_CLOSE_PYBLOCK]["tok"],
                 "OPEN_COMMENTBLOCK":tokens[T_OPEN_COMMENTBLOCK]["tok"],   "CLOSE_COMMENTBLOCK":tokens[T_CLOSE_COMMENTBLOCK]["tok"],
                 "OPEN_VERBATIMBLOCK":tokens[T_OPEN_VERBATIMBLOCK]["tok"], "CLOSE_VERBATIMBLOCK":tokens[T_CLOSE_VERBATIMBLOCK]["tok"]}

    filename  = ""
    incFiles  = None
    homeDir   = ""
    src       = None
    srcLen    = 0
    srcLexPos = 0
    srcStrPos = 0

    # Lexicon Scan modes and types
    LM_BLOCK_SCAN    = -1
    lexMode          = None
    lexOpenScan      = {T_OPEN_CMDBLOCK:     {"str":tokens[T_OPEN_CMDBLOCK]["tok"],        "next":T_CLOSE_CMDBLOCK},
                        T_OPEN_VARBLOCK:     {"str":tokens[T_OPEN_VARBLOCK]["tok"],        "next":T_CLOSE_VARBLOCK},
                        T_OPEN_PYBLOCK:      {"str":tokens[T_OPEN_PYBLOCK]["tok"],         "next":T_CLOSE_PYBLOCK},
                        T_OPEN_COMMENTBLOCK: {"str":tokens[T_OPEN_COMMENTBLOCK]["tok"],    "next":T_CLOSE_COMMENTBLOCK},
                        T_OPEN_VERBATIMBLOCK:{"str":tokens[T_OPEN_VERBATIMBLOCK]["tok"],   "next":T_CLOSE_VERBATIMBLOCK}
                        }

    lexCloseScan     = {T_CLOSE_CMDBLOCK:     {"str":tokens[T_CLOSE_CMDBLOCK]["tok"],      "next":LM_BLOCK_SCAN},
                        T_CLOSE_VARBLOCK:     {"str":tokens[T_CLOSE_VARBLOCK]["tok"],      "next":LM_BLOCK_SCAN},
                        T_CLOSE_PYBLOCK:      {"str":tokens[T_CLOSE_PYBLOCK]["tok"],       "next":LM_BLOCK_SCAN},
                        T_CLOSE_COMMENTBLOCK: {"str":tokens[T_CLOSE_COMMENTBLOCK]["tok"],  "next":LM_BLOCK_SCAN},
                        T_CLOSE_VERBATIMBLOCK:{"str":tokens[T_CLOSE_VERBATIMBLOCK]["tok"], "next":LM_BLOCK_SCAN},
                        }

    SECTION_LEX, SECTION_PARSE, SECTION_CODE, SECTION_EXEC = "LEX SCANNER", "PARSE TREE", "CODE GEN", "EXEC"
    STATUS_INIT, STATUS_OK,     STATUS_ERROR               = range (3)
    status           = STATUS_INIT
    statusMsg        = ""
    lexList          = None
    lexExtendList    = None

    # ------------------------

    lexToParseTreeIdx = 0
    parseTree         = None

    # ------------------------

    outputHandle         = None # output file handle to output to file/socket
    checkFileChangedSecs = None # Reduce parsing time check for file change every checkFileChangedSecs
    lastCheckFileChanged = None # Store last time check for file change
    lastFileChangedTime  = None # Store template file modified date/time

    # ======================================================

    # return String
    def _scanParamStr(self, lineList):
        ptypeS3Q, ptypeD3Q, ptypeS1Q, ptypeD1Q = range(4)
        pMatchAny                  = '(.*?)'
        pMatchEscape               = '\\'
        pMatchType                 = ["(''')", '(""")', "(')", '(")']
        smSTART, smEND, smCOMPLETE = range(3)

        scanType = None
        scanMode = smSTART
        rtnStr = ''
        lineCount = 0
        while 1:
            if len(lineList) > 0:
                line = lineList.pop(0)
            else:
                return rtnStr

            if scanMode == smSTART:
                matched = False
                for type, m in enumerate(pMatchType):
                    matched = re.search('^' + m + '(.*)', line.lstrip())
                    if matched:
                        rtnStr = matched.group(1)
                        lineList.insert(0, matched.group(2))
                        scanType = type
                        scanMode = smEND
                        break

                if scanMode == smEND:  # continue scanning/parsing parameter
                    continue
                return line  # return line as is, its not an escaped string type parameter
            elif scanMode == smEND:
                prsStr = ""
                while True:
                    matched = re.search(pMatchAny + pMatchType[scanType], line)
                    if matched:
                        m = matched.group(1)
                        if ((len(m) > 0) and (m[-1] == pMatchEscape)):  # continue scanning
                            prsStr += matched.group(1) + matched.group(2)[0]
                            line = line[len(matched.group(1)) + 1:]
                            continue
                        else:
                            prsStr += matched.group(1) + matched.group(2)
                            scanMode = smCOMPLETE
                            break
                    else:
                        prsStr = line
                        break
                # end scanning ...

                # no matched found, continue scanning
                if (lineCount > 0):
                    if ((scanType == ptypeS1Q) or (scanType == ptypeD1Q)):
                        rtnStr += '\\'  # add line continuation onto the single quote type string
                    rtnStr = rtnStr.rstrip(self.NL) + self.NL  # add return to multi quote type string

                rtnStr += prsStr
                if scanMode == smCOMPLETE:  # return completed parse param
                    return rtnStr
                lineCount += 1
        # end while

    # ======================================================

    def _scanBoolParam (self, s, default=False):
        try:
            if isinstance(s, list): # use the last entry for boolean testing ...
                s = s[-1]
            if s and (str(s).lower().strip() in ['true','t','y','1','yes', 'on']):
                return True
            if s and (str(s).lower().strip() in ['false','f','n','o','no', 'off']):
                return False
        except:
            pass
        return default

    # ======================================================

    def _escapeHTML (self, escapeOn, text):
        if not escapeOn:
            return text

        """escape strings for display in HTML"""
        return html.escape(text, quote=True). \
            replace(u'\t', u'&emsp;'). \
            replace(u'  ', u' &nbsp;')

    def _trimHTML (self, trimOn, text, trimAction ="both"):
        if not trimOn:
            return text

        trimAction = trimAction.lower()

        if trimAction == "left":
            return text.lstrip()
        elif trimAction == "right":
            return text.rstrip()
        elif trimAction == "compress":
            r = ""
            for s in text.split('\n'):
                r += s.strip()
            return r
        return text.strip()

    # ======================================================

    def _lexScanChkAddBlckItem (self, lineNo, charPos, tokenStartPos, lexCloseDict, curLexMode):
        scn = lexCloseDict["str"]
        lscn = len(scn)
        if self.src.startswith(scn, self.srcLexPos, self.srcLexPos + lscn):
            p = str(self.src[self.srcStrPos:self.srcLexPos]).strip()
            if curLexMode == self.T_CLOSE_CMDBLOCK:
                sp = p.split(' ', 1)
                sp1 = sp[0].lower()
                sp2 = sp[1] if len(sp) > 1 else ""
                tok = None
                for tk, tv in self.tokens.items():
                    if (sp1 == tv["tok"]):
                        tok = tk
                        break
                if tok:
                    # add the parse block command
                    if tok in (self.T_OPER_INCLUDE, self.T_OPER_EXTENDS):
                        param = self._scanParamStr(sp2.split(self.NL))
                        if not param:
                            self.status    = self.STATUS_ERROR
                            self.statusMsg = self.SECTION_LEX+ ":error parsing at line:" + str(lineNo) + " charPos:" + str(charPos) + " :: " + p + self.NL + \
                                             "Expected a Python style string parameter!"
                            logging.error("TemplateLoad._lexScanChkAddBlckItem : " + self.statusMsg)
                            return True
                        else:
                            # insert new include into src relative from this template file path
                            incFilename = self.getSafeTEMPLATEPath(os.path.dirname(self.filename) + os.path.sep + eval(param))
                            if tok == self.T_OPER_INCLUDE:
                                try:
                                    # everything before the {% tag +
                                    # new included src +
                                    # advance past the close %} tag so to replace the tag with the include src
                                    self.src = self.src[:tokenStartPos] + \
                                               open(incFilename).read() + \
                                               self.src[self.srcLexPos +len(lexCloseDict):]

                                    self.chkFileChanges[incFilename] = os.path.getmtime(incFilename)
                                except Exception as e:
                                    logging.error("TemplateLoad._lexScanChkAddBlckItem Failed include file >" + eval(param) + "< " + str(e))
                                    raise Exception ("Failed loading include file")

                                self.srcLen    = len(self.src)
                                self.srcLexPos = tokenStartPos
                                self.srcStrPos = self.srcLexPos
                                self.lexMode   = lexCloseDict["next"]
                                return True
                            elif  tok == self.T_OPER_EXTENDS: # Merge existing elements into current parse list
                                t = TemplateLoad(incFilename, self.homeDir)
                                self.lexExtendList.append(t)
                                # update the included (recursive) dependency file change list
                                self.chkFileChanges[incFilename] = os.path.getmtime(incFilename)
                                self.chkFileChanges = {**self.chkFileChanges, **t.chkFileChanges}
                    else:
                        self.lexList.append(self.LexItem(self, tok, sp2, lineNo, charPos))
                else:
                    self.status    = self.STATUS_ERROR
                    self.statusMsg = self.SECTION_LEX+ ":error parsing at line:" + str(lineNo) + " position:" + str(charPos-len(p)) + " unknown token ->" + p + "<-"
                    return True
                # endif
            elif curLexMode == self.T_CLOSE_VARBLOCK:
                # add the parse block command
                self.lexList.append(self.LexItem(self, self.T_BLOCK_CODE, p, lineNo, charPos))
            elif curLexMode == self.T_CLOSE_PYBLOCK:
                # add the python block command
                self.lexList.append(self.LexItem(self, self.T_PYBLOCK_CODE, p, lineNo, charPos))
            elif curLexMode == self.T_CLOSE_COMMENTBLOCK:
                # add the python block command
                self.lexList.append(self.LexItem(self, self.T_COMMENTBLOCK_CODE, p, lineNo, charPos))
            elif curLexMode == self.T_CLOSE_VERBATIMBLOCK:
                # add the python block command
                self.lexList.append(self.LexItem(self, self.T_VERBATIMBLOCK_CODE, p, lineNo, charPos))

            # Add the closing block item
            self.lexMode    = lexCloseDict["next"]
            self.srcLexPos += len(lexCloseDict)
            self.srcStrPos  = self.srcLexPos
        # endif

        if (self.lexMode != curLexMode):
            return True
        return False

    # ======================================================

    def _lexScanner (self):
        self.status    = self.STATUS_INIT
        self.lexMode   = self.LM_BLOCK_SCAN
        self.srcLen    = len(self.src)
        lineNo         = 1
        lineEndOfPos   = 0
        tokenStartPos  = 0
        lastLexS       = None

        while (self.srcLexPos < self.srcLen) and (self.status != self.STATUS_ERROR):
            if (self.lexMode == self.LM_BLOCK_SCAN):
                for lexK, lexS in self.lexOpenScan.items():
                    scn  = lexS["str"]
                    lscn = len(scn)
                    if self.src.startswith(scn, self.srcLexPos, self.srcLexPos+lscn):
                        # create a plain text/html object and place it into the lexList
                        self.lexList.append (self.LexItem (self, self.T_STRING, self.src[self.srcStrPos:self.srcLexPos], lineNo, self.srcLexPos-lineEndOfPos) )
                        self.lexMode    = lexS["next"]
                        tokenStartPos   = self.srcLexPos
                        self.srcLexPos += len(lexS)
                        self.srcStrPos  = self.srcLexPos
                        break
                if (self.lexMode != self.LM_BLOCK_SCAN):
                    continue
            elif (self.lexMode in self.lexCloseScan.keys()):
                if self._lexScanChkAddBlckItem(lineNo, self.srcLexPos - lineEndOfPos, tokenStartPos, self.lexCloseScan[self.lexMode], self.lexMode):
                    if self.status == self.STATUS_ERROR:
                        return False
                    continue
            # count the lines as we parse the template code
            if self.src[self.srcLexPos] == self.NL:
                lineNo += 1
                lineEndOfPos = self.srcLexPos + 1
            self.srcLexPos += 1
        # End while

        if self.status != self.STATUS_INIT:
            return False

        if self.lexMode == self.LM_BLOCK_SCAN:
            # Add final plain text/html object and place it into the lexTree
            self.lexList.append(self.LexItem(self, self.T_STRING, self.src[self.srcStrPos:self.srcLexPos], lineNo, self.srcLexPos - lineEndOfPos))
        else:
            self.status = self.STATUS_ERROR
            self.statusMsg =self.SECTION_LEX+ ":error, expected a close token " + self.tokens[self.lexMode]["tok"]
            logging.error ("TemplateLoad._lexScanner : " + self.statusMsg)
            return False

        self.status    = self.STATUS_OK
        self.statusMsg = self.SECTION_LEX + ":ok"
        return True

    # ======================================================

    # returns (parsed tree node, matchedType, status code)
    # recursive call to matchType list
    def _buildParseTree (self, matchType = None, parentBlock = None, initBuild=False):
        if initBuild:
            self.lexToParseTreeIdx = 0
            self.parseTree         = None

        ptreeList = []
        lexLen    = len(self.lexList)
        statCode  = self.STATUS_OK
        while (self.lexToParseTreeIdx < lexLen):
            itm = self.lexList[self.lexToParseTreeIdx]

            # match end type(s)
            if matchType:
                for t in matchType:
                    if (itm.type == t):
                        # if this is matching
                        if len(matchType) <= 1: # test if this is just a single terminating block
                            itm.codeBlockParentLexItem = parentBlock
                            ptreeList.append(itm)
                            self.lexToParseTreeIdx += 1
                        else:
                            # this is likely an if then elif else block of code/structure
                            pass
                        return ptreeList, t, self.STATUS_OK

            # check if statement has dependencies, if so then call recursive and join the result
            if (self.tokens[itm.type]["depd"]):
                if itm.type not in (self.T_COMMENTBLOCK_CODE,):
                    ptreeList.append(itm)
                self.lexToParseTreeIdx += 1

                ptRtn, mtype, statCode = self._buildParseTree(self.tokens[itm.type]["depd"], itm)
                if statCode == self.STATUS_OK:
                    if itm.type not in (self.T_COMMENTBLOCK_CODE,):
                        ptreeList.append(ptRtn)
                    #ptreeList.append(self.lexList[self.lexIdx])
                else:
                    return None, mtype, statCode
            else:
                ptreeList.append(itm)
                self.lexToParseTreeIdx += 1

        if matchType:
            self.statusMsg = self.SECTION_PARSE + ": missing closing block element"
            logging.error("TemplateLoad._buildParseTree : " + self.statusMsg)
            return None, matchType, self.STATUS_ERROR

        return ptreeList, None, statCode

    # ======================================================

    def _genCodeInitVars (self, httpObj=None):
        return {'_AUTOESCAPE'    : False,
                '_AUTOTRIM'      : False,
                '_AUTOTRIMACTION': 'both',
                '_CYCLE'         : 0,
                'self'           : httpObj,
                '_http'          : httpObj,
                '_tmpl'          : self,
                '_escapeHTML'    : self._escapeHTML,
                'output'         : self.output}

    def _genCodeComment (self, lexItem):
        return "# " + str(lexItem.lineNo) + "," + str(lexItem.charPos) + " : " + self.tokens[lexItem.type]["tok"] + self.NL

    def _genCode (self, lexList, codeVarDict=None, depth=0):
        # build dict variable list
        if codeVarDict is None:
            codeVarDict = self._genCodeInitVars()

        outStr = "output( _tmpl._escapeHTML(_AUTOESCAPE,  _tmpl._trimHTML(_AUTOTRIM, str(%s), _AUTOTRIMACTION) ) )"
        indent  = "    "
        dstr  = indent * depth
        code  = ""
        for l in lexList:
            if isinstance(l, list):
                c, codeVarDict = self._genCode(l, codeVarDict, depth + 1)
                code += c
            elif l.type == self.T_STRING:
                varName          = "s" + str(l.lineNo) + "_" + str(l.charPos)
                codeVarDict[varName] = l.data
                code            += dstr + (outStr % varName) + self._genCodeComment (l)
            elif l.type == self.T_BLOCK_CODE:
                code            += dstr + (outStr % l.data) + self._genCodeComment (l)
            elif l.type == self.T_PYBLOCK_CODE:
                for c in l.data.split(self.NL):
                    code += (indent * (depth)) + c + self.NL
            elif l.type in (self.T_OPER_FOR, self.T_OPER_WHILE):
                code += dstr + self.tokens[l.type]["tok"] + " " + l.cleanDataStr() + ":" + self._genCodeComment (l)
            elif l.type == self.T_OPER_ENDWHILE:
                code += dstr + l.cleanDataStr() + self._genCodeComment (l)
            elif l.type in (self.T_OPER_IF, self.T_OPER_ELIF,  self.T_OPER_ELSE):
                code += dstr + self.tokens[l.type]["tok"] + " " + l.data + ":" + self._genCodeComment (l)
            elif l.type == self.T_OPER_AUTOTRIM:
                defName = "autoTrim" + str(l.lineNo) + "_" + str(l.charPos)
                code +=  dstr + "def " + defName + "(_AUTOTRIM, _AUTOTRIMACTION):" + self._genCodeComment(l)
            elif l.type == self.T_OPER_ENDAUTOTRIM:
                 defName = "autoTrim" + str(l.codeBlockParentLexItem.lineNo) + "_" + str(l.codeBlockParentLexItem.charPos)
                 d = l.codeBlockParentLexItem.data.strip()
                 code += (indent * (depth-1)) + defName + "(True, " + (d if d else '""') + ")" + self._genCodeComment(l)
            elif l.type == self.T_OPER_AUTOESCAPE:
                defName = "autoEsc" + str(l.lineNo) + "_" + str(l.charPos)
                code +=  dstr + "def " + defName + "(_AUTOESCAPE):" + self._genCodeComment(l)
            elif l.type == self.T_OPER_ENDAUTOESCAPE:
                 defName = "autoEsc" + str(l.codeBlockParentLexItem.lineNo) + "_" + str(l.codeBlockParentLexItem.charPos)
                 code += (indent * (depth-1)) + defName + "(" + str(self._scanBoolParam(l.codeBlockParentLexItem.data.strip(), True)) + ")" + self._genCodeComment(l)
            elif l.type == self.T_OPER_BLOCK:
                code +=  dstr + "if ('" + l.data.strip() + "' in locals()) or ('" + l.data.strip() + "' in globals()):" + self._genCodeComment (l)
            elif l.type == self.T_OPER_FILENAME:
                code += dstr + "output(r'''" + self.filename + "''')" + self._genCodeComment (l)
            elif l.type == self.T_OPER_RELFILENAME:
                relPath = self.filename.split( os.path.abspath(self.homeDir) )
                if len(relPath) > 1:
                    relPath = relPath[1]
                else:
                    relPath = relPath[0]
                code += dstr + "output(r'''" +  relPath + "''')" + self._genCodeComment (l)
            elif l.type == self.T_OPER_CYCLE:
                code += dstr + "_CYCLE_LIST = ("+l.data.strip() + ")" + self._genCodeComment (l)
                code += dstr + (outStr % "_CYCLE_LIST[_CYCLE % len(_CYCLE_LIST)]") + self._genCodeComment(l)
                code += dstr + "_CYCLE += 1" + self._genCodeComment(l)
            elif l.type == self.T_OPER_CYCLERESET:
                code += dstr + "_CYCLE = 0" + self._genCodeComment(l)
            elif l.type == self.T_OPER_TAG:
                t = l.data.strip().upper()
                if (t in self.tokenTags):
                    code += dstr + (outStr % ('"'+self.tokenTags[t]+'"') ) + self._genCodeComment(l)
            elif l.type == self.T_VERBATIMBLOCK_CODE:
                varName = "s" + str(l.lineNo) + "_" + str(l.charPos)
                codeVarDict[varName] = l.data
                code += dstr + ('output(%s)' % varName) + self._genCodeComment (l)
            elif l.type == self.T_COMMENTBLOCK_CODE:
                pass
            else:
                code += (indent * (depth-1)) + self._genCodeComment (l)
        # end for
        return code, codeVarDict

    def _genCodeExec (self, code, varDict):
        if self.status != self.STATUS_OK:
            return False

        # output debug stuff
        #self.dumpGenCode (code, varDict)

        try:
            exec (code, varDict, varDict)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tbNext    = False
            errLineNo = -1
            if exc_traceback.tb_next:
                tbNext = True
                # print ("Error in generated code error line " + str(exc_traceback.tb_next.tb_lineno))
                errLineNo = exc_traceback.tb_next.tb_lineno
                epos      = code.split(self.NL)[exc_traceback.tb_next.tb_lineno-1].split ('#')[-1]
                try:
                    l = epos.split(',')[0].strip()
                    c = epos.split(':')[0].split(',')[1].strip()
                    b = epos.split(':')[1].strip()
                    self.statusMsg = self.SECTION_EXEC + ":Error in Template Source : '" + self.filename + "', line:" + l + ", char:" + c + ", block type:[" + b + "]"
                    self.statusMsg += self.NL + str(e)
                    self.statusMsg += self.NL + str(traceback.format_exc())
                except:
                    tbNext = False

            if not tbNext:
                self.statusMsg = self.SECTION_EXEC + ":Exception on " + str(e) +  ", Error Line:" + str(errLineNo) + self.NL
                ln = 1
                for c in code.split(self.NL):
                    self.statusMsg += "["+str(ln).rjust(4, '0')+"]" + c + self.NL
                    ln += 1

            self.status = self.STATUS_ERROR
            logging.error ("TemplateLoad._genCodeExec : " + self.statusMsg)
            return False

        self.statusMsg = self.SECTION_EXEC + ":ok"
        return True

    # ======================================================

    def _parseFile (self):
        if (self.parseTree and (self.status == self.STATUS_OK)):
            if ((datetime.datetime.now() - self.lastCheckFileChanged).total_seconds() >= self.checkFileChangedSecs):
                self.lastCheckFileChanged = datetime.datetime.now()
                noChange = True
                for key, lastChgTime in self.chkFileChanges.items():
                    if os.path.getmtime(key) > lastChgTime:
                        logging.info("TemplateLoad._parseFile : file ->" + key + "<- has changed!")
                        self.reset()
                        noChange = False
                        break
                if noChange:
                    return True
            else:
                return True
        else:
            self.reset()

        if not self.src:
            try:
                logging.info("TemplateLoad._parseFile : loading file ->" + self.filename + "<-")
                fn = self.getSafeTEMPLATEPath(self.filename)
                f  = open(fn, mode='r', encoding="utf-8")
                self.src = f.read()
                f.close()
                self.chkFileChanges[fn] = os.path.getmtime(fn)
                self.lastCheckFileChanged = datetime.datetime.now()
                logging.info("TemplateLoad._parseFile : parsing file ->" + self.filename + "<-")
            except Exception as err:
                logging.error('TemplateLoad._parseFile Exception loading file ->' + self.filename + '<- :: ' + str(err))
                raise Exception (str(err))

        if not self.src:
            return False

        self._lexScanner()
        if self.status != self.STATUS_OK:
            logging.error('TemplateLoad._parseFile Exception loading file ->' + self.filename + '<- Error Code ' + str(self.status) + ', ' + str(self.statusMsg))
            return False

        # output debug stuff
        #logging.info ("TemplateLoad._parseFile : --- Lex List Dump ---")
        #self.dumpLexList(self.lexList)

        self.parseTree, matchType, self.status = self._buildParseTree(initBuild=True)
        if self.status != self.STATUS_OK:
            self.statusMsg = self.SECTION_PARSE + ":ok"
            return False

        # output debug stuff
        #logging.info ("TemplateLoad._parseFile : --- Parse Tree Dump ---")
        #self.dumpLexList(self.parseTree)

        # merge extended templates included in this template
        if len(self.lexExtendList) > 0:
            # returns : lexListStartIdx, lexListEndIdx, lexList Matched block list
            def _extractExtendedBlock(lexList, blockName):
                # search the newLexList
                msIdx = meIdx = idx = -1
                commentActive = False
                for mbi in lexList:
                    idx += 1
                    if mbi.type in (self.T_OPEN_COMMENTBLOCK,):
                        commentActive = True; continue
                    elif mbi.type in (self.T_CLOSE_COMMENTBLOCK,):
                        commentActive = False; continue
                    elif (not commentActive) and (msIdx < 0) and (mbi.type == self.T_OPER_BLOCK) and (mbi.data == blockName):
                        msIdx = idx
                    elif (not commentActive) and (msIdx >= 0) and (mbi.type == self.T_OPER_ENDBLOCK) and (mbi.codeBlockParentLexItem == lexList[msIdx]):
                        meIdx = idx
                        break
                if (msIdx >= 0) and (meIdx >= 0):
                    return msIdx, meIdx, lexList[msIdx:meIdx + 1]
                return None, None, []
            # ------------------------------------------------------------
            newLexList = []
            self.lexExtendList.append(self)
            for mrgItem in self.lexExtendList:
                if not newLexList:
                    newLexList = mrgItem.lexList
                    continue
                commentActive = False
                liIdx         = 0
                prependList   = []
                while liIdx < len(mrgItem.lexList):
                    if mrgItem.lexList[liIdx].type in (self.T_OPEN_COMMENTBLOCK,):
                        commentActive = True
                    if mrgItem.lexList[liIdx].type in (self.T_CLOSE_COMMENTBLOCK,):
                        commentActive = False
                    if (commentActive == False) and (mrgItem.lexList[liIdx].type == self.T_OPER_BLOCK):
                        blockName = mrgItem.lexList[liIdx].data
                        # search the current lexList
                        omsIdx, omeIdx, olexBlk = _extractExtendedBlock(newLexList, blockName)
                        # matched list, replace it in lex List
                        if olexBlk:
                            # search this template block list
                            nmsIdx, nmeIdx, nlexBlk = _extractExtendedBlock(mrgItem.lexList[liIdx:], blockName)
                            if nlexBlk:
                                # remove old block code, and insert new block code
                                newLexList = newLexList[:omsIdx] + nlexBlk + newLexList[omeIdx+1:]
                                # skip to the next item after this block
                                liIdx += nmeIdx
                            # end if
                        # end if
                    else:
                        if mrgItem == self:
                            prependList.append(mrgItem.lexList[liIdx])
                        else:
                            # append any non block onto the end of the new merged list
                            newLexList.append(mrgItem.lexList[liIdx])
                    # end if
                    liIdx += 1
                # end while
                newLexList = prependList + newLexList
            # end for

            # assign new lex list
            if newLexList:
                self.lexList       = newLexList
                self.lexExtendList = []
                #self.dumpLexList(self.lexList)
                self.parseTree, matchType, self.status = self._buildParseTree(initBuild=True)
                if self.status != self.STATUS_OK:
                    self.statusMsg = self.SECTION_PARSE + ":ok"
                    return False

        return True

    def reset (self):
        self.chkFileChanges       = {}
        self.lexList              = []
        self.lexExtendList        = []
        self.src                  = None
        self.srcLen               = 0
        self.srcLexPos            = 0
        self.srcStrPos            = 0
        self.lexMode              = None
        self.lexToParseTreeIdx    = 0
        self.parseTree            = None
        self.lastCheckFileChanged = None
        self.statusMsg            = ""
        self.status               = self.STATUS_INIT

    def renderTemplate (self, userVarsDict, selfObj=None, outputHandle=None):
        self._parseFile()

        if (self.parseTree and (self.status == self.STATUS_OK)):
            self.outputHandle = outputHandle

            # vars = dict(self._genCodeInitVars().items() + userVarsDict.items())
            vars = {**self._genCodeInitVars(selfObj), **userVarsDict}
            code, varDict = self._genCode(self.parseTree, vars)

            return self._genCodeExec(code, varDict)

        return False

    def dumpLexList (self, lexList=None, depth=0, numStart=0):
        if not lexList:
            lexList = self.lexList
        idx = 0
        indent = "+"
        for i in range(0,depth):
            indent += "-"

        for l in lexList:
            if isinstance(l, list):
                numStart = self.dumpLexList (l, depth+1, numStart)
                pass
            else:
                s = str(l.data).replace(self.NL, '').replace('\r', '')
                o = indent+"[" + str(numStart).rjust(4, '0') + " @ " +str(l.lineNo).rjust(4,'0') + "," + str(l.charPos).rjust(3,'0') + "] Type: [" + str(l.type).rjust(2,'0') + "] "+ self.tokens[l.type]["tok"] + \
                      (" : "+s if l.type in (self.T_STRING, self.T_VERBATIMBLOCK_CODE) else " "+s[0:64] + ("..." if len(s) > 64 else ""))
                logging.info("TemplateLoad.dumpLexList : " + o)
            numStart += 1

        return numStart

    def dumpGenCode (self, code, varDict):
        ln = 1
        for c in code.split(self.NL):
            logging.info ("TemplateLoad.dumpGenCode : [" + str(ln).rjust(4, '0') + "]" + c)
            ln += 1
        logging.info ("TemplateLoad.dumpGenCode : --- Variables ---")
        for key, val in varDict.items():
            logging.info ("TemplateLoad.dumpGenCode : " + key + "," + str(val))

    def output(self, s):
        if self.outputHandle:
            if isinstance(self.outputHandle, io.StringIO):
                self.outputHandle.write(s)
            else:
                self.outputHandle.write (bytes(s, "utf-8"))
        else:
            sys.stdout.write (bytes(s, "utf-8"))

    # from a web request path, returns valid fullpath or None
    def getSafeTEMPLATEPath (self, filename):
        homeAccessPath   = os.path.abspath(self.homeDir)
        fullAccessPath   = os.path.abspath(filename)
        if not fullAccessPath.startswith(homeAccessPath + os.path.sep):
            logging.error('TemplateLoad.getSafeTEMPLATEPath failed access request at path: >' + filename +  '<  to file  >' + fullAccessPath + '<')
            return None
        return fullAccessPath

    def __init__(self, filename, homeDir, checkFileChangedSecs=10):
        self.reset()
        self.checkFileChangedSecs = checkFileChangedSecs
        self.filename             = filename
        self.homeDir              = homeDir
        self._parseFile()

# ------------------------------------------------------------

SessionList            = {}
SESSION_STATUS_LOGININIT = 'loginInit'
SESSION_STATUS_LOGIN     = 'loginOk'
SESSION_STATUS_LOGOUT    = 'loggedOut'
SESSION_MAXTIME          = 60 * 6  # 6 hours
SESSION_PURGE_INTERRUPT  = 60 * 15 # 15 mins call purge session
SESSION_PURGE_CALL       = None

def HTTPWebServerSessionPurge ():
    global SESSION_PURGE_CALL, SESSION_MAXTIME
    SESSION_PURGE_CALL = time.time()
    tstamp             = time.time()

    logging.info("HTTPWebServerSessionPurge : Session No : "+ str(len(SessionList)))
    delKeys = []
    for key in SessionList.keys():
        try:
            s = SessionList[key]
            if s:
                expires = s['expires']
                if expires and expires < tstamp:
                    delKeys.append(key)
                    logging.info("HTTPWebServerSessionPurge SessionID : " + key + " expired")
                elif (not expires) and (s['created'] + SESSION_MAXTIME < tstamp):
                    logging.info("HTTPWebServerSessionPurge MAXTIME SessionID : " + key + " expired")
                    delKeys.append(key)
            else:
                delKeys.append(key)
        except:
            pass

    for key in delKeys:
        try:
            del SessionList[key]
        except:
            pass

    logging.info("HTTPWebServerSessionPurge : Session No (After Purge) : " + str(len(SessionList)))

# ------------------------------------------------------------

class MappingRules():
    TYPE  = "type"; TYPE_RE = "regexp"; TYPE_REOPT = "regexp-opt"; TYPE_PYMATCH = "pymatch"; TYPE_DEBUG = "debug";
    TYPE_RE_REDIRT = "regexp-redirect";    TYPE_REOPT_REDIRT = "regexp-opt-redirect";    TYPE_PYMATCH_REDIRT = "pymatch-redirect";
    PYEVEL="pyeval"; REGEXP = "regexp"; SCRIPT = "script"; REGEXP_OPTS= "regexp_opts"; PYEVAL="eval"; HTTPCMD_RE= "httpcmd_re";

    commaESC = '~' + chr(7) + chr(7) + '~'
    filepath = ''
    rules    = []
    debug    = False

    checkFileChangedSecs = None # Reduce parsing time check for file change every checkFileChangedSecs
    lastCheckFileChanged = None # Store last time check for file change
    lastFileChangedTime  = None # Store template file modified date/time

    def __init__(self, filepath, checkFileChangedSecs=10):
        self.filepath             = filepath
        self.checkFileChangedSecs = checkFileChangedSecs
        self.checkCache()
    def checkCache (self):
        if self.lastCheckFileChanged:
            if ((datetime.datetime.now() - self.lastCheckFileChanged).total_seconds() >= self.checkFileChangedSecs):
                self.lastCheckFileChanged = datetime.datetime.now()
                if os.path.getmtime(self.filepath) > self.lastFileChangedTime:
                    logging.debug(f"MappingRules.checkCache : file ->{self.filepath}<- has changed!")
                else:
                    logging.debug(f"MappingRules.checkCache exiting file change : file ->{self.filepath}")
                    return
            else:
                logging.debug(f"MappingRules.checkCache exiting cache no-change : file ->{self.filepath}")
                return

        self.rules    = []
        self.debug    = False
        mrf           = open (self.filepath)
        try:
            for line in mrf.readlines():
                line = line.replace('\t', ' ').strip()
                # ignore comment lines
                if line == "" or line[0] == "#":
                    continue

                # escape, parse, unescape
                line = line.replace(',,', self.commaESC)
                s = line.split(',')
                for i in range(len(s)):
                    s[i] = s[i].replace(self.commaESC, ',')

                # basic parsing of parameters
                if len(s) > 1:
                    # url webpage mapping
                    if s[0].lower().strip() in (self.TYPE_RE):
                        if len(s) == 4:
                            self.rules.append({self.TYPE: self.TYPE_RE, self.HTTPCMD_RE: s[1].strip(), self.REGEXP : s[2].strip(), self.SCRIPT : s[3].strip()})
                            continue
                    if s[0].lower().strip() in (self.TYPE_REOPT):
                        if len(s) == 5:
                            self.rules.append({self.TYPE: self.TYPE_REOPT, self.HTTPCMD_RE: s[1].strip(), self.REGEXP : s[2].strip(), self.SCRIPT : s[3].strip(), self.REGEXP_OPTS : s[4].strip()})
                            continue
                    if s[0].lower().strip() in (self.TYPE_PYMATCH):
                        if len(s) == 4:
                            self.rules.append({self.TYPE: self.TYPE_PYMATCH, self.HTTPCMD_RE: s[1].strip(), self.PYEVAL: s[2].strip(), self.SCRIPT: s[3].strip()})
                            continue
                    # url redirection
                    if s[0].lower().strip() in (self.TYPE_RE_REDIRT):
                        if len(s) == 4:
                            self.rules.append({self.TYPE: self.TYPE_RE_REDIRT, self.HTTPCMD_RE: s[1].strip(), self.REGEXP : s[2].strip(), self.TYPE_PYMATCH_REDIRT : s[3].strip()})
                            continue
                    if s[0].lower().strip() in (self.TYPE_REOPT_REDIRT):
                        if len(s) == 5:
                            self.rules.append({self.TYPE: self.TYPE_REOPT_REDIRT, self.HTTPCMD_RE: s[1].strip(), self.REGEXP : s[2].strip(), self.TYPE_PYMATCH_REDIRT : s[3].strip(), self.REGEXP_OPTS : s[4].strip()})
                            continue
                    if s[0].lower().strip() in (self.TYPE_PYMATCH_REDIRT):
                        if len(s) == 4:
                            self.rules.append({self.TYPE: self.TYPE_PYMATCH_REDIRT, self.HTTPCMD_RE: s[1].strip(), self.PYEVAL: s[2].strip(), self.TYPE_PYMATCH_REDIRT: s[3].strip()})
                            continue

                    if s[0].lower().strip() in (self.TYPE_DEBUG):
                        if (s[1].lower().strip() in ['true', 't', 'y', '1', 'yes', 'on']):
                            self.debug = True
                            logging.info("MappingRules: Debug on")
                        else:
                            self.debug = False
                        continue
                logging.error("MappingRules: Malformed mapping rule : ->" + line + "<-")
            # end for
        except Exception as inst:
            logging.error('MappingRules: Failed loading mapping rules file ' + self.filepath + ' ' + str(traceback.format_exc()))

        if self.rules:
            self.lastFileChangedTime  = os.path.getmtime(self.filepath)
            self.lastCheckFileChanged = datetime.datetime.now()

    def replaceHTTPVars (self, httpd, replStr):
        cmds = { 'HOSTNAME_NAME' : httpd.host_name,
                 'PORT_NUMBER':    httpd.port_number,
                 'PROTOCOL':       httpd.protocol,
                 'COMMAND':        httpd.command,
                 'PATH':           httpd.path,
                 'BASEPATH' :      httpd.queryBasePath,
                 'QUERYSTRING':    httpd.queryString,
                 'QUERYBASEPATH':  re.sub(r'([^/]+)/?$', r'', httpd.path),
                 'QUERYNAME':      re.sub(r'(.*)(\?.*)', r"\1", strSubtract(httpd.path, re.sub(r'([^/]+)/?$', r'', httpd.path)))
                }
        for k in cmds.keys():
            replStr = re.sub(r'(\{\%\s*'+k+r'\s*\%\})', str(cmds[k]), replStr)
        return replStr

    def applyRules (self, httpd, osWebpageDir, basepath, querytomatch, defaultPath=''):
        #  basePath='/metadata/test/' querystring='program.py?param=123'
        if self.debug:
            logging.info ("Log Flush: Mapping Debug logging on")

        # logging.debug ("MappingRules.applyRules httpd='" + str(vars(httpd)) + "'")
        if self.debug:
            logging.info ("MappingRules.applyRules file = " + self.filepath)
            logging.info ("MappingRules.applyRules envs vars = " + self.replaceHTTPVars(httpd, r"\{\%BASEPATH\%\}:'{%BASEPATH%}', \{\%HOSTNAME_NAME\%\}:'{%HOSTNAME_NAME%}', \{\%PORT_NUMBER\%\}:'{%PORT_NUMBER%}', \{\%PROTOCOL\%\}:'{%PROTOCOL%}', \{\%COMMAND\%\}:'{%COMMAND%}',\{\%PATH\%\}:'{%PATH%}', \{\%QUERYSTRING\%\}:'{%QUERYSTRING%}', \{\%QUERYBASEPATH\%\}:'{%QUERYBASEPATH%}',\{\%QUERYNAME\%\}:'{%QUERYNAME%}'").replace(r'\{\%', r'{%').replace(r'\%\}',r'%}') )
            logging.info ("MappingRules.applyRules func vars = basepath:'" + basepath + "', querytomatch:'" + querytomatch + "'")

        if not osWebpageDir:
            logging.error("MappingRules.applyRules osWebpageDir is blank/none, internal error!")
            return defaultPath

        rtnScript = ''
        rtnRedirect = ''
        for rule in self.rules:
            try:
                # apply files based upon file path sent
                if (rule[self.TYPE] == self.TYPE_RE)        and re.match(rule[self.HTTPCMD_RE], httpd.command) and re.match(rule[self.REGEXP], querytomatch):
                    rtnScript = osWebpageDir + os.path.sep + rule[self.SCRIPT]
                elif (rule[self.TYPE] == self.TYPE_REOPT)   and re.match(rule[self.HTTPCMD_RE], httpd.command) and re.match(rule[self.REGEXP], querytomatch, eval(rule[self.REGEXP_OPTS])):
                    rtnScript = osWebpageDir + os.path.sep + rule[self.SCRIPT]
                elif (rule[self.TYPE] == self.TYPE_PYMATCH) and re.match(rule[self.HTTPCMD_RE], httpd.command) and eval(rule[self.PYEVAL]):
                    rtnScript = osWebpageDir + os.path.sep + rule[self.SCRIPT]
            except Exception as err:
                logging.error (f"Failed mapping rule evaluation : {str(rule)}" )
                logging.error(str(err))

            if rtnScript:
                logging.info("MappingRules.applyRules MATACHED rule : " + str(rule))
                logging.info("MappingRules.applyRules returning : " + rtnScript)
                return rtnScript # build return path for script

            # apply files based upon file path sent
            try:
                if (rule[self.TYPE] == self.TYPE_RE_REDIRT)        and re.match(rule[self.HTTPCMD_RE], httpd.command) and re.match(rule[self.REGEXP], querytomatch):
                    rtnRedirect = self.replaceHTTPVars (httpd, rule[self.TYPE_PYMATCH_REDIRT])
                elif (rule[self.TYPE] == self.TYPE_REOPT_REDIRT)   and re.match(rule[self.HTTPCMD_RE], httpd.command) and re.match(rule[self.REGEXP], querytomatch, eval(rule[self.REGEXP_OPTS])):
                    rtnRedirect = self.replaceHTTPVars (httpd, rule[self.TYPE_PYMATCH_REDIRT])
                elif (rule[self.TYPE] == self.TYPE_PYMATCH_REDIRT) and re.match(rule[self.HTTPCMD_RE], httpd.command) and eval(rule[self.PYEVAL]):
                    rtnRedirect = self.replaceHTTPVars (httpd, rule[self.TYPE_PYMATCH_REDIRT])
            except Exception as err:
                logging.error (f"Failed mapping redirect rule evaluation : {str(rule)}" )
                logging.error(str(err))

            if rtnRedirect:
                logging.info("MappingRules.applyRules MATACHED rule : " + str(rule))
                logging.info("MappingRules.applyRules redirecting to : " + rtnRedirect)
                httpd.redirect(rtnRedirect)
                return None

            if self.debug:
                logging.info("MappingRules.applyRules failed matching on rule : " + str(rule))

        return defaultPath

# ----------------------------------------------------------------------------------------------------

class HTTPWebServer (BaseHTTPServer.BaseHTTPRequestHandler):
    host_name     = None
    port_number   = None
    protocol      = None
    serve_via_ssl = False

    classInit         = False
    homeDir           = None
    homeScriptName    = None
    mimeTypeFilename  = None
    mimeDict          = {}
    templateCacheDict = {}

    cgiFormDataLoaded   = False
    cgiFormDataPostFull = {}
    cgiFormData         = {}

    headerCalled        = False
    headerClosed        = False

    sessionCookieJar    = None

    defaultRunFiles     = ('index.py', 'index.ty')
    mappingRulesFile    = '_mapping_rules_'
    noInternetAccess    = ('_hidden_', '_templates_', mappingRulesFile)
    mappingCacheDict    = {}
    mappingRules        = None

    # basic parsing of the self.path url path
    queryBasePath       = ''
    queryScript         = ''
    queryString         = ''

    # create our own custom constructor
    def __init__(self, host_name, port_number, serve_via_ssl, ssl_server_pem, appHome, homeScriptName, mimeTypeFilename, *args):
        if (HTTPWebServer.classInit == False):
            logging.debug("HTTPWebServer.__init__ (first call)")
            HTTPWebServer.homeDir          = appHome
            HTTPWebServer.homeScriptName   = homeScriptName
            HTTPWebServer.mimeTypeFilename = mimeTypeFilename
            HTTPWebServer.mimeDict         = {}

            # Load the mimetypes
            try:
               file = open (HTTPWebServer.mimeTypeFilename)
               for line in file.readlines():
                    line = line.replace('\t', ' ')
                    s = line.split(' ');
                    if (len(s) > 1):
                        HTTPWebServer.mimeDict[s[0].strip().lower()] = s[1].strip()
            except IOError:
                logging.error ('HTTPWebServer.__init__ Mime File ' + HTTPWebServer.mimeTypeFilename + ' not found!')
            HTTPWebServer.classInit = True
        else:
            logging.debug("Bypass HTTPWebServer.__init__ MyHTTPWebServer")

        self.cgiFormDataLoaded   = False
        self.cgiFormDataPostFull = {}
        self.cgiFormData         = {}
        self.sessionCookieJar    = cookies.SimpleCookie()
        self.host_name           = host_name
        self.port_number         = port_number
        self.serve_via_ssl       = serve_via_ssl
        self.ssl_server_pem      = ssl_server_pem
        self.headerCalled        = False
        self.headerClosed        = False
        self.mappingRules        = None
        self.queryBasePath       = ''
        self.queryScript         = ''
        self.queryString         = ''

        if self.serve_via_ssl:
            self.protocol = 'https'
        else:
            self.protocol = 'http'

        # call base class constructor as well
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
        except Exception as e:
            if not 'certificate unknown' in str(e).lower():
                logging.error ('HTTPWebServer.__init__ ' + str(e) + ' ' + str(traceback.format_exc()))

    def createRandomHash (self):
        r = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        s = str(time.time())
        for x  in range (10):
            s = s + r[random.randint(0, len(r)-1)]
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    # ################################################################

    def sessionPurge (self):
        global SESSION_PURGE_CALL, SESSION_PURGE_INTERRUPT
        if not SESSION_PURGE_CALL or (SESSION_PURGE_CALL + SESSION_PURGE_INTERRUPT < time.time()):
            HTTPWebServerSessionPurge ()

    # timeout : in seconds, or -1 for infinite
    # returns unique session ID
    def sessionCreate (self, timeout=None, loginState=SESSION_STATUS_LOGIN):
        global SessionList
        self.sessionPurge()

        s = self.createRandomHash ()

        if s in SessionList.keys():
            return self.sessionCreate (timeout)

        t  = time.time()
        e = None
        if timeout > 0:
            e = t + timeout

        sessionInfo = {'created'   : t,
                       'loginState': loginState,
                       'expires'   : e,
                       'noUpdated' : 0,
                       'timeout'   : timeout}

        SessionList[s] = sessionInfo
        self.log_message("sessionCreate SessionID : " + s + " created")
        return s

    # changes the state of a login session
    def sessionUpdateItem (self, key, timeout=None, loginState=None):
        global SessionList
        self.sessionPurge()
        try:
            s = SessionList[key]
            if s and timeout:
                s['timeout'] = timeout
                if timeout > 0:
                    s['expires'] = time.time() + timeout
                elif s['timeout'] <= 0:
                    s['expires'] = None
            if s and loginState:
                s['loginState'] = loginState
        except:
            pass

    # Remove a login session
    def sessionRemoveItem(self, key):
        global SessionList
        try:
            if key:
                del SessionList[key]

        except:
            pass

    # Returns True for valid and existing session, False for timeout, non existing session
    def sessionCheckUpdate (self, key):
        global SessionList
        self.sessionPurge()
        tstamp = time.time()
        try:
            s = SessionList[key]
            if s:
                expires = s['expires']
                if expires and expires < tstamp:
                    del SessionList[key]
                    self.log_message("sessionCheckUpdate SessionID : " + key + " expired")
                    return False
                elif expires:
                    SessionList[key]['noUpdated'] += 1
                    SessionList[key]['expires']    = tstamp + SessionList[key]['timeout']
                    self.dbg_message ("sessionCheckUpdate SessionID : " + key + " o.k")

                # check login status, if in init mode, not logged in, but don't delete session either
                if s['loginState'] == SESSION_STATUS_LOGININIT:
                    self.log_message("sessionCheckUpdate SessionID : " + key + " status " + s['loginState'])
                    return False

                # if logout, then session removed.
                if s['loginState'] != SESSION_STATUS_LOGIN:
                    del SessionList[key]
                    self.log_message("sessionCheckUpdate SessionID : " + key + " status " + s['loginState'] + " session removed")
                    return False

                return True
        except:
            pass
        return False

    # Parse headers for basic auth, returns dict, username/password, none if nothing found
    def authBASIC_getUserPasswd (self):
        if 'authorization' in self.headers:
            parts = self.headers['authorization']
            parts = parts.split (' ')
            userpass    =  base64.b64decode (parts[1]).decode('UTF-8')
            userpassStr = str(userpass).split(":")

            self.log_message("authBASIC_getUserPasswd : " + userpassStr[0])

            return {'username':userpassStr[0], 'password':userpassStr[1]}
        else:
            return None

    # ################################################################

    # overload the base class logging function
    def log_message(self, format, *args):
        logging.info ("[%s] : %s" % (str(self.client_address[0]), str(format%args)))

    def dbg_message(self, format, *args):
        logging.debug ("[%s] : %s" % (str(self.client_address[0]), str(format%args)))

    def getBaseURLAddress (self):
        return self.protocol + '://' + self.host_name + ":" + str(self.port_number)

    def getFullRequestAddress (self):
        return self.getBaseURLAddress() + self.path

    def getCookiesFromHeader(self):
        self.sessionCookieJar = cookies.SimpleCookie()
        try:
            for key, value in self.headers.items():
                if key.lower() == 'cookie':
                    self.sessionCookieJar.load(value) # Parse/Load the cookie into the cookie object from the passed in header
        except:
            pass
        return self.sessionCookieJar

    def getCGIParametersFormData(self):
        # Parse the form data posted
        if self.cgiFormDataLoaded ==  False:
            self.cgiFormData = {}
            if self.command.upper() == "POST":
                self.cgiFormDataPostFull = FieldStorage(fp=self.rfile,
                                                        headers=self.headers,
                                                        keep_blank_values=1,
                                                        environ={'REQUEST_METHOD': 'POST',
                                                                 'CONTENT_TYPE': self.headers['Content-Type'],
                                                                }
                                                        )

                # convert from field storage to normal dictionary list
                try:
                    for item in self.cgiFormDataPostFull.keys():
                        if re.match(r'.*\[\]$',item):
                            arry     = []
                            itemArry = item.rstrip('[]')
                            if isinstance(self.cgiFormDataPostFull[item], list):
                                for itema in self.cgiFormDataPostFull[item]:
                                    arry.append(itema.value)
                            else:
                                arry.append(self.cgiFormDataPostFull[item].value)
                            self.cgiFormData[itemArry] = arry
                        else:
                            self.cgiFormData[item] = self.cgiFormDataPostFull[item].value
                except:
                    pass

            # convert url (get) params
            parsed_path = urlparse(self.path)
            try:
                # convert parameters to unquote values
                p = dict([p.split('=') for p in parsed_path[4].split('&')])
                for key in p.keys():
                    self.cgiFormData[key] = urllib.parse.unquote_plus(p[key])
            except:
                pass

            self.cgiFormDataLoaded = True
        return self.cgiFormData

    def dumpSubmitFormData(self, fileHandle):
        self.getCGIParametersFormData()

        fileHandle.write (bytes('Headers\n'))
        for key, value in self.headers.items():
            fileHandle.write(bytes('  %s: %s\n' % (key, value)))

        fileHandle.write(bytes('Client: %s\n' % str(self.client_address)))
        fileHandle.write(bytes('User-agent: %s\n' % str(self.headers['user-agent'])))
        fileHandle.write(bytes('Path: %s\n' % self.path))

        fileHandle.write(bytes('Form data:\n'))

        # Echo back information about what was posted in the form
        try:
            for field in self.cgiFormDataPostFull.keys():
                field_item = self.cgiFormDataPostFull[field]
                if field_item.filename:
                    # The field contains an uploaded file
                    file_data = field_item.file.read()
                    file_len = len(file_data)
                    del file_data
                    fileHandle.write(bytes('\tUploaded %s as "%s" (%d bytes)\n' % (field, field_item.filename, file_len)))
                else:
                    # Regular form value
                    fileHandle.write(bytes('\t%s=%s\n' % (field, self.cgiFormDataPostFull[field].value)))
        except:
            pass

        fileHandle.write(bytes('Content Data:\n'))
        try:
            fileHandle.write(bytes(self.cgiFormDataPostFull.file.read()))
        except:
            pass

    def redirect(self, url, inclHTMLRedirect=False, otherHeaderDict=None):
        if not url:
            return

        self.send_response(302)
        self.send_header('Location', url)

        if otherHeaderDict:
            for name, value in otherHeaderDict.items():
                self.send_header(name, value)
        self.end_headers()

        if (inclHTMLRedirect):
            self.wfile.write (bytes('''
<META http-equiv="refresh" content="0;URL=''' + url + '''">
<script type="text/javascript">window.location = "''' + url + '''"</script>
''', "utf-8"))

    # otherHeaderDict is a dictionary with name, value pair
    def do_HEAD(self, mimetype='text/html; charset=UTF-8', turnOffCache=False, statusCode=200, otherHeaderDict=None, closeHeader=True):
        self.headerCalled = True
        self.send_response(statusCode)
        self.send_header("Content-type", mimetype)

        if turnOffCache:
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate') # HTTP 1.1.
            self.send_header('Pragma',        'no-cache')                            # HTTP 1.0.
            self.send_header('Expires',       '0')                                   # Proxies.

        if otherHeaderDict:
            for name, value in otherHeaderDict.items():
                self.send_header(name, value)

        if closeHeader and (self.headerClosed == False):
            self.headerClosed = True
            self.end_headers()

    # return None on failure, of String on valid translation
    def templateStr (self, templateFilename, userVarsDict, checkFileChangedSecs=10):
        t = None

        # check if its already cached
        if templateFilename in self.templateCacheDict:
             t = self.templateCacheDict[templateFilename]
        else:
            # reuse the previous loaded version
             t = TemplateLoad(templateFilename, self.homeDir, checkFileChangedSecs)
             self.templateCacheDict[templateFilename] = t

        outputStr = io.StringIO()
        if not t.renderTemplate(userVarsDict, self, outputStr):
            #logging.error('HTTPWebServer.templateStr (' + templateFilename + ') failed template render! [' + str(t.status) + '] ' + t.statusMsg)
            return None
        return outputStr.getvalue()

    def templateRunAbsPath (self, fullpathTemplateFilename, userVarsDict={}, checkFileChangedSecs=10, rtnStr=False):
        s = self.templateStr (fullpathTemplateFilename, userVarsDict, checkFileChangedSecs)
        if s != None:
            if rtnStr:
                return s
            self.output(s)
            return True
        return False

    # returns true/false if successful output, runs via relative directory within the self.path
    # access request
    def templateRunRelPath (self, templateName, userVarsDict={}, checkFileChangedSecs=10, rtnStr=False):
        filePath = self.path.split('?')
        filePath = urllib.parse.unquote_plus(filePath[0])
        fullAccessPath  = os.path.abspath(self.homeDir + filePath)
        fp              = os.path.dirname(fullAccessPath) + os.path.sep + templateName
        if not fp.startswith(os.path.abspath(self.homeDir)+ os.path.sep):
            logging.error('HTTPWebServer.templateRunRelPath (' + self.command + ') failed access request at path: >' + filePath +  '<  to file  >' + fp + '<')
            return None
        return self.templateRunAbsPath (fp, userVarsDict, checkFileChangedSecs, rtnStr)

    # returns true/false if successful output, runs via _templates_ directory within the self.path
    # access request
    def templateRun (self, templateName, userVarsDict={}, checkFileChangedSecs=10, rtnStr=False):
        filePath = self.path.split('?')
        filePath = urllib.parse.unquote_plus(filePath[0])
        fullAccessPath = os.path.abspath(self.homeDir + filePath) + os.path.sep
        if filePath.endswith('/'):
            fp = os.path.abspath(fullAccessPath) + os.path.sep + '_templates_' + os.path.sep + templateName
        else:
            fp = os.path.dirname(os.path.abspath(fullAccessPath)) + os.path.sep + '_templates_' + os.path.sep + templateName
        if not fp.startswith(os.path.abspath(self.homeDir)+ os.path.sep):
            logging.error('HTTPWebServer.templateRun (' + self.command + ') failed access request at path: >' + filePath +  '<  to file  >' + fp + '<')
            return None
        return self.templateRunAbsPath (fp, userVarsDict, checkFileChangedSecs, rtnStr)

    def output(self, s):
        if not self.headerCalled:
            self.do_HEAD(turnOffCache=True)
        elif (not self.headerClosed):
            self.end_headers()

        if type(s) == type(str()):
            self.outputRaw (bytes(s, "utf-8"))
        else:
            self.outputRaw (s)

    def outputRaw(self, r):
        try:
            self.wfile.write(r)
        except Exception as e:
            logging.error('HTTPWebServer.outputRaw failed outputRaw() at path: >' + self.path + '< ' + str(e))
            raise e

    def isMimeType (self, filePath):
        # extract file extension so as to send the correct mime-type
        fileExt = '.' + filePath.split('.')[-1]
        if (fileExt == '.'):
            fileExt = '.txt'

        # match mime type based up extension
        try:
            type = self.mimeDict[fileExt.lower()]
        except:
            type = 'application/octet-stream'
        return type

    # from a web request path, returns valid fullpath or None
    def getSafeHTMLPath (self, filePath, defaultHomePage=None):
        if  (defaultHomePage) and ((filePath == None) or (filePath == '') or (filePath == '/')):
            filePath = filePath + os.path.sep + self.homeScriptName

        homeAccessPath   = os.path.abspath(self.homeDir)
        fullAccessPath   = os.path.abspath(self.homeDir + os.path.sep + (filePath if filePath else ''))

        if not (fullAccessPath + os.path.sep).startswith(homeAccessPath + os.path.sep):
            return None

        hiddenAccessPath = fullAccessPath[len(homeAccessPath):].lower()
        for noAccess in self.noInternetAccess:
            if ((re.search(noAccess+"$", hiddenAccessPath)) or (os.path.sep + noAccess + os.path.sep in hiddenAccessPath)):
                return None

        return fullAccessPath

    # returns tuple: (mapping file dir, mapping file name)
    def getLocalMappingRulesFile (self, filePath):
        fp       =  nvl(self.getSafeHTMLPath(filePath), os.path.abspath(self.homeDir))
        basePath = ''

        # without path manipulation e.g https://blah.com/someapp/somewebpage.py -> <install path>/someapp/somewebpage.py
        # or                            https://blah.com/someapp                -> <install path>/someapp
        if os.path.isdir(fp):
            basePath = fp
            if os.path.exists(fp + os.path.sep + self.mappingRulesFile):
                return (basePath, fp + os.path.sep + self.mappingRulesFile)

        # with path manipulation e.g https://blah.com/someapp/somewebpage.py to <install path>/someapp
        fp = nvl(self.getSafeHTMLPath(nvl(os.path.dirname(filePath)).rstrip(os.path.sep)), os.path.abspath(self.homeDir))

        if os.path.isdir(fp):
            basePath = fp
            if os.path.exists(fp + os.path.sep + self.mappingRulesFile):
                return (basePath, fp + os.path.sep + self.mappingRulesFile)

        return basePath, None

    def execfile(self, filepath, globals=None, locals=None):
        if globals is None:
            globals = {}
        globals.update({
            "self"    : self,
            "__file__": filepath,
            "__name__": "__main__",
        })
        with open(filepath, 'rb') as file:
            exec(compile(file.read(), filepath, 'exec'), globals, locals)

    def loadMappingRules (self, mprFile):
        if mprFile:
            # determine if mapping in the cache dict
            if mprFile in self.mappingCacheDict:
                logging.debug("HTTPWebServer.do_GET cached load mapping rules file '" + mprFile + "'")
                self.mappingCacheDict[mprFile].checkCache()
                return self.mappingCacheDict[mprFile]
            else:
                # reuse the previous loaded version
                logging.info("HTTPWebServer.do_GET loading mapping rules file '" + mprFile + "'")
                mr = MappingRules (mprFile)
                self.mappingCacheDict[mprFile] = mr
                return mr
        return None

    def makeQueryBasePath (self, mprDir):
        # subtract home path from webpage filesystem path, and convert it to url path current path
        self.queryBasePath = strSubtract(mprDir, os.path.abspath(self.homeDir)).replace(os.path.sep, '/').strip('/')
        if self.queryBasePath:
            self.queryBasePath = '/' + self.queryBasePath + '/'
    def processHTTPCommand(self):
        try:
            """Respond to a GET request."""
            filePath = self.path.split('?')
            self.queryString = ''
            if (len(filePath) > 1):
                self.queryString = filePath[1]

            filePath = urllib.parse.unquote_plus(filePath[0])
            # fullAccessPath = self.getSafeHTMLPath(filePath, self.homeScriptName)
            fullAccessPath = self.getSafeHTMLPath(filePath, '')

            if not fullAccessPath:
                logging.error('HTTPWebServer.do_GET (' + self.command + ') failed access request at path: >' + filePath +  '<  to file  >' + os.path.abspath(self.homeDir + os.path.sep + filePath) + '<')
                self.send_response(404)
                self.output("<html><h1>Access Denied: 404</h1></html>")
                return

            # load get CGI parameters the same structure as post parameters
            self.getCGIParametersFormData()

            # load get Cookies from header
            self.getCookiesFromHeader()

            # ----------------- Start Mapping files processor -------------------
            # load directory mapping rules file, returns tuple: (mapping file dir, mapping file name) from current path
            mprDir, mprFile = self.getLocalMappingRulesFile (filePath)
            if not mprFile: # if no mapping file found in current path, then apply default mappings from root path to allow global mappings, if it exists
                mprDir, mprFile = self.getLocalMappingRulesFile('')

            self.makeQueryBasePath (mprDir)

            self.mappingRules = self.loadMappingRules (mprFile)

            if self.mappingRules:
                # apply mapping rules to  current url path and convert to script name to execute
                fullAccessPath = self.mappingRules.applyRules (self, mprDir, self.queryBasePath, strSubtract(self.path, self.queryBasePath), fullAccessPath)
                if fullAccessPath:
                    self.makeQueryBasePath(os.path.dirname(fullAccessPath))

            # if fullAccessPath is None (redirect from mappingRules), then leave web page rending now...
            if not fullAccessPath:
                return

            # ----------------- End Mapping files processor -------------------

            # setup default processing based upon empty directory paths e.g. https://blah.com/blah or https://blah.com/blah/
            defaultsAccessPath = fullAccessPath
            defaultsIdx        = -1
            while (True):
                defaultsRetry = False
                if (re.search('.py$', fullAccessPath)): # run python *.py files
                    try:
                        self.execfile(fullAccessPath)
                    except SystemExit as se:
                        if se.code != 0:
                            logging.error ('HTTPWebServer.do_GET (.py) (' + self.command + ') Abnormal page exit ' + str(se))
                    except IOError:
                        if (defaultsIdx < len(self.defaultRunFiles)-1) and os.path.isdir(defaultsAccessPath):
                            defaultsRetry  = True
                            defaultsIdx   += 1
                            fullAccessPath = defaultsAccessPath + os.path.sep + self.defaultRunFiles[defaultsIdx]
                        else:
                            logging.error ('HTTPWebServer.do_GET (.py) (' + self.command + ') Render page ' + filePath + ' not found! Accessing : ' + fullAccessPath)
                            self.send_response(404)
                            self.output("<html><h1>I/O Error: 404</h1></html>")
                    except (ConnectionAbortedError, ConnectionResetError):
                        pass
                    except Exception as err:
                        if ( (not re.search("'ConnectionAbortedError'$", str(err))) and
                             (not re.search("'ConnectionResetError'$", str(err))) ):
                            logging.error ('HTTPWebServer.do_GET (.py) (' + self.command + ') Exception in ' + filePath + ' :: ' + str(traceback.format_exc()))
                            self    .send_response(500)
                            self.output("<html><h1>Internal Error: 500</h1></html>")
                elif (re.search('.ty$', fullAccessPath)): # run template *.ty files
                    try:
                        self.templateRunAbsPath(fullAccessPath, {})
                    except SystemExit as se:
                        if se.code != 0:
                            logging.error ('HTTPWebServer.do_GET (.ty) (' + self.command + ') Abnormal page exit ' + str(se))
                    except IOError:
                        logging.error ('HTTPWebServer.do_GET (.ty) (' + self.command + ') Render page ' + filePath + ' not found! Accessing : ' + fullAccessPath)
                        self.send_response(404)
                        self.output("<html><h1>I/O Error: 404</h1></html>")
                    except Exception as err:
                        logging.error ('HTTPWebServer.do_GET (.ty)(' + self.command + ') Exception in ' + filePath + ' :: ' + str(traceback.format_exc()))
                        self.send_response(500)
                        self.output("<html><h1>Internal Error: 500</h1></html>")
                else:
                    # -------- Default File/Scripts to run ---------
                    # test if file is of type directory, if so then process default files to run
                    if (defaultsIdx < len(self.defaultRunFiles) - 1) and os.path.isdir(defaultsAccessPath):
                        defaultsRetry = True
                        defaultsIdx += 1
                        fullAccessPath = defaultsAccessPath + os.path.sep + self.defaultRunFiles[defaultsIdx]
                        continue

                    file = None
                    try:
                        scode        = 200
                        fileStartPos = 0
                        fileEndPos   = -1
                        # parse file position header: Range : bytes=131072-
                        if 'Range' in self.headers:
                            scode = 206
                            pos   = self.headers['Range']
                            parms = pos.split('=')
                            if (len(parms) == 2) and (parms[0].lower() == 'bytes'):
                                bpos = parms[1].split('-')
                                try:
                                    fileStartPos = int(bpos[0])
                                    if len(bpos) == 2 and bpos[1].strip() != '':
                                        fileEndPos = int(bpos[1].strip())
                                except:
                                    pass

                        # determine if fullAccessPath is pointing to a standard file, if so, load it and send it out...
                        try:
                            file = open(fullAccessPath, 'rb')
                        except IOError:
                            if defaultsRetry:
                                continue
                            logging.error('HTTPWebServer.do_GET (' + self.command + ') File ' + filePath + ' not found/access denied! Accessing : ' + fullAccessPath)
                            self.send_response(404)
                            self.output("<html><h1>I/O Error: 404</h1></html>")
                            break

                        if scode == 200:
                            # if no Range header, then send as a normal file ...
                            self.send_response(scode)
                            self.send_header('Content-type', self.isMimeType (fullAccessPath))
                            self.end_headers()
                            self.wfile.write(file.read())
                        else:
                            # Send as http1.1 partial file 206 status
                            file.seek(0, io.SEEK_END)
                            fileSize = file.tell()
                            readLen = fileSize - 1
                            if fileEndPos > 0:
                                readLen = (fileEndPos - fileStartPos) - 1
                            elif fileEndPos < 0 and fileStartPos > 0:
                                readLen = (fileSize - fileStartPos) - 1
                            file.seek(fileStartPos)

                            self.protocol_version = "HTTP/1.1"
                            self.do_HEAD(mimetype=self.isMimeType(fullAccessPath), statusCode=scode, turnOffCache=False, closeHeader=True,
                                         otherHeaderDict={'Content-Range': f'bytes {fileStartPos}-{fileStartPos+readLen}/{fileSize}',
                                                          'Connection': 'close',
                                                          'Content-Length': str(readLen + 1)})
                            logging.debug(f"HTTPWebServer.do_GET file @ :: fileStartPos {fileStartPos} - {fileStartPos + readLen}, readLen {readLen} : filesize {fileSize}")
                            # write output
                            chunkSize = 65536
                            actualReadLen = readLen + 1
                            while True:
                                if chunkSize > actualReadLen:
                                    chunkSize = actualReadLen
                                chunk = file.read(chunkSize)
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                actualReadLen -= len(chunk)
                                if actualReadLen <= 0:
                                    break

                            self.send_response(scode)
                            self.send_header('Content-type', self.isMimeType (fullAccessPath));
                            self.end_headers()
                            self.wfile.write(file.read())
                        file.close()
                        file = None
                    finally:
                        try:
                            if file:
                                file.close()
                        except:
                            pass

                        # retry file execution for default files...
                if defaultsRetry:
                    continue

                break # exit loop
        except (ConnectionAbortedError, ConnectionResetError):
            pass
        except IOError as ioerr:
            logging.error(f"HTTPWebServer.do_GET Unknown IO Error: {ioerr}")
            logging.error(f"HTTPWebServer.do_GET @ file {fullAccessPath}")
        finally:
            self.rfile.flush()
            self.wfile.flush()

    # Alias post operations as the same as get operations
    do_GET      = processHTTPCommand
    do_POST     = processHTTPCommand
    do_PUT      = processHTTPCommand
    do_PATCH    = processHTTPCommand
    do_DELETE   = processHTTPCommand

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

import threading
import errno
from socket import error as socket_error
class HTTPInstances (threading.Thread):
    handler            = None
    host_name          = None
    port_number        = None
    serve_via_ssl      = None
    ssl_server_pem     = None
    HTTPDaemon         = None
    protocol           = None

    def __init__(self,host_name, port_number, serve_via_ssl, ssl_server_pem, home_dir, home_scriptname, mimetypes_filename):
        self.host_name      = host_name
        self.port_number    = port_number
        self.serve_via_ssl  = serve_via_ssl
        self.ssl_server_pem = ssl_server_pem
        super(HTTPInstances, self).__init__()

        def httpdConstructorLoader (host_name, port_number, serve_via_ssl, ssl_server_pem, homeDir, homeScriptName, mimeTypeFilename):
            return lambda *args: HTTPWebServer(host_name, port_number, serve_via_ssl, ssl_server_pem, homeDir, homeScriptName, mimeTypeFilename, *args)

        handler = httpdConstructorLoader (host_name, port_number, serve_via_ssl, ssl_server_pem, home_dir, home_scriptname, mimetypes_filename)

        logging.info ('HTTPInstances.init port:' + str(port_number));

        gotSocketCount = 30
        while (gotSocketCount > 0):
            try:
                self.HTTPDaemon = ThreadedHTTPServer ((self.host_name, self.port_number), handler)
                gotSocketCount = 0
            except socket_error as serr:
                gotSocketCount -= 1
                if ((serr.errno != errno.EADDRINUSE) or (gotSocketCount <= 0)):
                    raise serr
                else:
                    logging.error('HTTPInstances.__init__  Address ' + str(self.port_number) + ' already in use. Retry count down ' + str(gotSocketCount))
                    time.sleep(1)

        # if this service is going to be encrypted ...
        if serve_via_ssl:
            self.protocol   = 'https'
            self.sslContext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.sslContext.load_cert_chain(certfile=ssl_server_pem)
            self.HTTPDaemon.socket = self.sslContext.wrap_socket(self.HTTPDaemon.socket, server_side=True,  do_handshake_on_connect=False)
            self.HTTPDaemon.socket.setblocking(0)
        else:
            self.protocol     = 'http'

    def run(self):
        logging.info ('HTTPInstances.run Starts - ' + self.protocol + '://' + (self.host_name if self.host_name != '0.0.0.0' else socket.gethostname()) + ':' + str(self.port_number))
        try:
            self.HTTPDaemon.serve_forever()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logging.info ('HTTPInstances.run Exception with ' + str(e))
        self.HTTPDaemon.server_close()
        logging.info ('HTTPInstances.run Stops - %s:%s' % (self.host_name, self.port_number))


# #######################################################################################

def startDaemon (host_name = socket.gethostname(), port_number = 80, serve_via_ssl = False, ssl_server_pem = None, homeDir ='./webapp', homeScriptName = 'index.py', mimeTypeFilename ='./config/mimetypes.txt', threaded = False):
    logging.debug ('HTTPDaemon.startDaemon ')

    inst = HTTPInstances (host_name, port_number, serve_via_ssl, ssl_server_pem, homeDir, homeScriptName, mimeTypeFilename)

    SERVERS.append(inst)
    inst.start()
    if not threaded:
        inst.join()

def stopDaemon ():
    global SERVERS
    for inst in SERVERS:
        try:
            inst.HTTPDaemon.shutdown()
            inst.HTTPDaemon.server_close()
        except Exception as e:
            pass
        logging.info ('HTTPDaemon.stopDaemon Server Stops - %s:%s' % (inst.host_name, inst.port_number))

    # Empty SERVERS instances
    SERVERS = []

