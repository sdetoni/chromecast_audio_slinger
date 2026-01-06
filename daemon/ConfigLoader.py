import logging
import traceback
import re
import subprocess
import random
import string

ConfigIncludeFile          = 'INCLUDE'
ConfigEndScopeGlobal       = 'END-SCOPE-GLOBAL'
ConfigEndScope             = 'END-SCOPE'

# password encoding/decoding identifiers
ConfigCredsIDList = ["AUTH_USERS", "AUTH_ADMIN_USERS"]

class ConfigLoader (object):
    secType_ID    = "SECTION_TYPE"
    secTypeGlobal = "GLOBAL"
    secTypeLevel0 = "LEVEL0"
    secTypeLevel1 = "LEVEL1"
    secTypeLevel3 = "LEVEL3"

    includedFiles = []
    filename      = None
    settings      = None
    def __init__(self, filename):
        try:
            self.includedFiles = []
            self.filename      = filename
            self.settings      = {self.secType_ID:self.secTypeGlobal}
            self._includeFiles (self.filename)
            self.settings = self._loadCfg (open (self.filename, mode='r', encoding='utf-8').readlines(), self.secTypeGlobal, self.settings, None)
        except Exception as inst:
            logging.error('Failed loading config file ' + str(self.filename) + ' ' + str(traceback.format_exc()))
            raise

    def _nvl (self, param, ifNone=''):
        if not param:
            return ifNone
        return param

    # ------------------------------------------------

    def _includeFiles (self, filename):
        if [x for x in self.includedFiles if x == filename]:
            return
        self.includedFiles.append(filename)

    # ------------------------------------------------

    # override access methods on data in class so they cannot be pickled/exported
    def __getstate__(self):
        return None
    def __setstate__(self, d):
        return

    # This is deprecated, no longer used
    def encryptString (self, s):
        if self._obfuscateACLTest ():
            return self._obfuscateString(s, self.__cryptkey)
        return ''

    # This is deprecated, no longer used
    decryptString = encryptString

    # ------------------------------------------------
    PTYPE_RS3Q, PTYPE_RD3Q, PTYPE_STR_RS1Q, PTYPE_STR_RD1Q, PTYPE_S3Q, PTYPE_D3Q, PTYPE_STR_S1Q, PTYPE_STR_D1Q = range (8)
    PMatchAny     = '(.*?)'
    PMatchEscape  = '\\'
    PMatchType    = [ "(r''')",  '(r""")',   "(r')",   '(r")',   "(''')",   '(""")',   "(')",   '(")']
    PMatchEndType = [ "(''')",   '(""")',    "(')",    '(")',    "(''')",   '(""")',   "(')",   '(")']
    PMatchNotType = ["(\\r''')", '(\\r""")', "(\\r')", '(\\r")', "(\\''')", '(\\""")', "(\\')", '(\\")', ]

    def _paramIsType (self, param):
        if param and (type(param) is str):
            for t, m in enumerate(self.PMatchType):
                matched = re.match('^' + m, param, re.MULTILINE)
                if matched:
                    return t

        return None

    # return String
    def _scanParam (self, lineList):
        SM_START, SM_END, SM_COMPLETE = range(3)
        scanType  = None
        scanMode  = SM_START
        rtnStr    = ''
        lineCount = 0
        while 1:
            if len(lineList) > 0:
                line = lineList.pop(0)
            else:
                return rtnStr

            if scanMode == SM_START:
                matched = False
                for type, m in enumerate(self.PMatchType):
                    matched = re.search ('^' + m + '(.*)', line.lstrip())
                    if matched:
                        rtnStr   = matched.group(1)
                        lineList.insert (0, matched.group(2))
                        scanType = type
                        scanMode = SM_END
                        break

                if scanMode == SM_END: # continue scanning/parsing parameter
                    continue
                return line # return line as is, its not an escaped string type parameter
            elif scanMode == SM_END:
                prsStr = ""
                while True:
                    matched = re.search(self.PMatchAny + self.PMatchEndType[scanType], line)
                    if matched:
                        m = matched.group(1)
                        if ((len(m) > 0) and  (m[-1] == self.PMatchEscape)): # continue scanning
                            prsStr += matched.group(1) + matched.group(2)[0]
                            line = line [len(matched.group(1))+1:]
                            continue
                        else:
                            prsStr += matched.group(1) + matched.group(2)
                            scanMode = SM_COMPLETE
                            break
                    else:
                        prsStr = line
                        break
                # end scanning ...

                # no matched found, continue scanning
                if (lineCount > 0):
                   if (scanType in (self.PTYPE_STR_S1Q, self.PTYPE_STR_D1Q, self.PTYPE_STR_RS1Q, self.PTYPE_STR_RD1Q)):
                       rtnStr += '\\' # add line continuation onto the single quote type string
                   rtnStr = rtnStr.rstrip ('\n') + '\n' # add return to multi quote type string

                rtnStr += prsStr
                if scanMode == SM_COMPLETE: # return completed parse param
                    return rtnStr
                lineCount += 1
        # end while

    def _assignParameter (self, key, param, configList):
        # Assign parameter to config store
        if key in configList.keys():
            if isinstance(configList[key], list):
                configList[key].append (param)
            else:
                configList[key] = [configList[key], param]
        else:
            configList[key] = param

        return configList

    def _loadCfg (self, lineList, sectionType, configListScope, thisGroupID):
        MODE_NORM, MODE_COMMENT = range (2)
        serviceName = None
        serviceCFG  = None

        scanMode    = MODE_NORM
        while 1:
            if len(lineList) > 0:
                line = lineList.pop(0).strip()
            else:
                return configListScope

            # ignore comment lines
            if scanMode == MODE_COMMENT:
                endComment = re.search (r'\*\/(.*)', line)
                if endComment:
                    scanMode = MODE_NORM
                    line = endComment.group(1)
                    lineList.insert (0, line) # remove command part and reprocess line.
                continue

            if scanMode == MODE_NORM:
                # ignore single line comment
                if line.lstrip() == "" or line.lstrip()[0] == "#":
                    continue
                # start multi line parsing of comments
                elif re.search (r'^\/\*', line):
                    scanMode = MODE_COMMENT
                    continue

                # include file
                incMatched = re.search (r'^\<(.*?)\>$', line)
                if incMatched:
                    param = incMatched.group(1).strip()
                    param = self._envVarExpand(param)
                    self._includeFiles(param)
                    try:
                        incFileList = open(param, mode='r', encoding='utf-8').readlines()

                        #insert lines at the start of this list and continue parsing ...
                        for line in reversed (incFileList):
                            lineList.insert (0, line)
                        continue
                    except Exception as e:
                        logging.error( __name__ + " : Include file error :  " + str(e) + traceback.format_exc())

                # scan for sub levels
                grpMatched = re.search (r'^\[\[\[(.*?)\]\]\]$', line)   # scan [[[sub page server/multiple page]]] loading
                if not grpMatched:
                    grpMatched = re.search (r'^\[\[(.*?)\]\]$', line)       # scan [[service page]] loading
                if not grpMatched:
                    grpMatched = re.search (r'^\[(.*?)\]$', line)            # scan [group of services] loading

                # If in a new sub/node section   e.g. ServiceName:
                if grpMatched:
                    groupID = grpMatched.group(1).upper().replace('/','\\') # replace pathing forward slash char with black slash

                    # matched TEST_SERVICE_STEPS type
                    if (re.compile(r'^\[\[\[(.*?)\]\]\]$').search(line)):
                        # test if we need return from this section and re-test line for next section
                        if sectionType.upper() == self.secTypeLevel3:  # deeper level, depth > 1
                            lineList.insert(0, line)
                            return configListScope
                        else:
                            configListScope[groupID] = self._loadCfg(lineList, self.secTypeLevel3, {self.secType_ID: self.secTypeLevel3}, self._envVarExpand(groupID))

                    # matched TEST_SERVICE type
                    elif (re.compile (r'^\[\[(.*?)\]\]$').search(line)):
                        # test if we need return from this section and re-test line for next section
                        if ((sectionType.upper() == self.secTypeLevel1) or
                            (sectionType.upper() == self.secTypeLevel3)): # deeper level, depth > 0
                            lineList.insert (0, line)
                            return configListScope
                        else:
                            configListScope[self._envVarExpand(groupID)] = self._loadCfg (lineList, self.secTypeLevel1, {self.secType_ID : self.secTypeLevel1}, self._envVarExpand(groupID))

                    # matched TEST_SERVGRPID type
                    elif (re.compile (r'^\[(.*?)\]$').search(line)):
                        # test if we need return from this section and re-test line for next section
                        if sectionType.upper() != self.secTypeGlobal: # base level, depth 0
                            lineList.insert (0, line)
                            return configListScope
                        else:
                            configListScope[self._envVarExpand(groupID)] = self._loadCfg (lineList, self.secTypeLevel0, {self.secType_ID : self.secTypeLevel0}, self._envVarExpand(groupID))
                    continue
                # --- end if ---

                ### No section detected, load config items ###
                s = line.split('=', 1)

                if len(s) > 1:
                    if len(s[0]) < 1:
                        continue
                    # Remove any spaces between '+' '|' '!' opers and param name
                    if s[0][0] == '+':
                        m = re.search (r'\+( *)(.*)', s[0])
                        s[0] = '+' + m.group(2)
                    elif s[0][0] == '|':
                        m = re.search (r'\|( *)(.*)', s[0])
                        s[0] = '|' + m.group(2)
                    elif s[0][0] == '!':
                        m = re.search (r'\!( *)(.*)', s[0])
                        s[0] = '!' + m.group(2)
                    elif s[0][0] == '*':
                        m = re.search (r'\*( *)(.*)', s[0])
                        s[0] = '*' + m.group(2)

                    key   = s[0]
                    param = s[1].strip()
                    lineList.insert (0, param)
                    param = self._scanParam (lineList)

                    # Assign parameter to config store
                    if s[0].upper() == ConfigIncludeFile:
                        param = self._envVarExpand(param)
                        self._includeFiles(param)
                        try:
                            incFileList = open(param, mode='r', encoding='utf-8').readlines()

                            #insert lines at the start of this list and continue parsing ...
                            for line in reversed (incFileList):
                                lineList.insert (0, line)
                        except Exception as e:
                            logging.error( __name__ + " : Include file error :  " + str(e) + traceback.format_exc())
                    elif key[0] == '/':  # check if this is a pathed value action
                        self.setSetting(key, param)
                    elif key[0] == '*': # check if this is a replace value action
                        key = key[1:]
                        self.replaceSetting(key, param)
                    else:
                        s[0] = s[0].replace('/', '\\').strip().upper()
                        configListScope = self._assignParameter (s[0], param, configListScope)
                elif s[0].upper() == ConfigEndScopeGlobal: # end the current scope of this config file load, go back to global scope
                    if sectionType.upper() != self.secTypeGlobal:  # goto base level, depth 0
                        lineList.insert(0, line)
                        return configListScope
                    # else, already at the current level, so just eat this action as there is nothing to do.
                elif s[0].upper() == ConfigEndScope: # end the current scope of this config file load
                    if sectionType.upper() != self.secTypeGlobal:  # goto base level, depth 0
                        return configListScope
                    # else, already at the current level, so just eat this action as there is nothing to do.
                elif ((len(s) == 1) and (s[0][0] == '-')):
                    # Remove any spaces between '-' oper and param name
                    m = re.search (r'\-( *)(.*)', s[0])
                    s[0] = '-' + m.group(2)
                    configListScope = self._assignParameter (s[0], '', configListScope)
                else: # ignore malformed config settings
                    logging.warning ('ConfigLoader._loadCfg : Malformed parameter ignored : '+line)

        # --- end while ---

    def _envVarExpand (self, val, path=''):
        if isinstance(val, str):
            try:
                pat   = re.compile(r'\$\{(.*?)\}')
                match = re.search(pat, val)
                while match:
                    v = match.group(1)
                    # check if this a relative located identifier or an absoluted path using the
                    # '/' at position 0
                    if ((len(v) > 0) and (v[0] == '/')):
                        v = v[1:]  # chomp the first char
                        replVal = self.getSetting(v)
                    else:
                        replVal = self.getSetting(path + '/' + v)

                    val     = re.sub(pat, replVal, val, 1)
                    match   = re.search(pat, val)
            except Exception as e:
                logging.error ('ConfigLoader._envVarExpand : Failed to expand ' + val + ' : Likely not matched found in config file.' + str(e))
                return ''
        return val

    def _getPath (self, name):
        # split list name (path+item id) and ignore the last item id, then rejoin it to a path or '' if no path left
        return '/'.join (name.split ('/')[:-1])

    def _getSetting (self, name, default='', settings=None, path=''):
        name = name.upper()
        try:
            if settings == None:
                settings = self.settings

            serviceID = name.split('/', 1)
            if len(serviceID) > 1:
                try:    return self._getSetting (serviceID[1], default, settings[serviceID[0]], path + serviceID[0] + '/')
                except: return default
            else:
                # search and replace ${env_var} in parameter string
                try:
                    # check for encrypted/obfuscated password type parameters
                    if name in ConfigCredsIDList:
                        p = settings[name]
                        m = re.search(r'^\|\|(.*)\|\|$', p)
                        if m:  # obfuscated password detected in config file, convert to plain-text before obfuscating again using random key
                            return self._obfuscateString(m.group(1), key=self.__cryptkey, decode=True)

                    # Dynamic OS call
                    if re.search (r'^\!', name ):
                        try:
                            if name not in settings:
                                return ''
                            p = self._envVarExpand(settings[name], path)
                            if self._paramIsType(p) is not None and self._paramIsType(p) >= 0:
                                p = eval(p)
                            return subprocess.check_output(p, stderr=subprocess.STDOUT, shell=True)
                        except Exception as e:
                            logging.error ("ConfigLoader._getSetting : failed OS call : " + str(e))
                            return ''
                    # Dynamic Python call
                    elif re.search (r'^\|', name ):
                        try:
                            # implement safe access controlled identifiable function call, and safe local stack updating of code
                            _=''
                            lStack = {'_' : _}
                            p = self._envVarExpand(settings[name], path)
                            if self._paramIsType(p) is not None and self._paramIsType(p) >= 0:
                                p = eval(p)
                            exec (p, lStack, lStack)
                            _ = lStack['_']
                            return _
                        except Exception as e:
                            logging.error ("ConfigLoader._getSetting : failed python call : " + str(e))
                            return ''
                    # check if name is a concatenation parameter for previous settings
                    elif ('+' + name) in settings.keys():
                        #subtract a path element and get previous items list additions...
                        l = path.split ('/')
                        if len(l) > 1:
                            del l[-1]
                            del l[-1]
                        p = ''
                        for pi in l:
                            p = p + pi + '/'
                        if p:
                            p = p + name
                        else:
                            p = name
                        lowerPathList = self.getSettingList(p)
                        lowerPathList.append(self._envVarExpand (settings['+'+name], path))
                        return lowerPathList
                    # check if its an ignore lower values '-' operator in front of parameter
                    elif ('-' + name) in settings.keys():
                        return None
                    else:
                        return self._envVarExpand (settings[name], path)
                except Exception as e:
                    return default

        except Exception as inst:
            # if default setting, then return the value
            if default:
                self.settings[name] = default
                return self.getSetting(name)
            logging.error('Setting name not found/load from config file ' + self.filename + ' ' + str(inst))

    # ------------------------------------------------


    # encrypts string using dynamically generated crypt key
    def obfuscateStringExtern (self, data, ):
        return self._obfuscateString(data, self.__cryptkey, encode=True)

    # encrypts string using dynamically generated crypt key
    def obfuscateStringCfgFile (self, data):
        return self._obfuscateString(data, self.__cfgFileCryptkey, encode=True)

    # returns the config file (string) with detected passwords obfuscated
    # encode : if TRUE, obfuscate hard coded passwords in config file
    #        : if False, plain-text obfuscated hard coded passwords in config file
    def obfuscateHardCodedPasswords (self, encode=True, nameTstList = ConfigCredsIDList):
        if not self._obfuscateACLTest ():
            return None

        lineList = open (self.filename, mode='r', encoding='utf-8').readlines()

        MODE_NORM, MODE_COMMENT = range (2)
        scanMode    = MODE_NORM
        rtnList     = []
        while 1:
            if len(lineList) > 0:
                line = lineList.pop(0)
            else:
                break

            # find end of comment
            if scanMode == MODE_COMMENT:
                cidx = line.find("*/")
                if cidx >= 0:
                    scanMode = MODE_NORM
                    rtnList.append(line[:cidx+2])      # comment, add to output
                    lineList.insert (0, line[cidx+2:]) # code part to retest
                else:
                    rtnList.append(line)               # comment, add to output
                continue

            if scanMode == MODE_NORM:
                # ignore single line comment
                if line.strip() == "" or line.strip()[0] == "#":
                    rtnList.append(line)               # comment, add to output
                    continue
                # start multi line parsing of comments
                elif re.search (r'^\/\*', line.strip()):
                    scanMode = MODE_COMMENT
                    rtnList.append(line)               # comment, add to output
                    continue

            for id in ConfigCredsIDList:
                # match strings like <id> = <password> e.g PASSWORD = 123456
                m = re.search('(' + id + ')' + r'([ \t]*)=([ \t]*)(.*)', line, re.IGNORECASE)
                if m: # found a match for a key word
                    pw = m.group(4).strip()
                    if pw == "": continue
                    m  = re.search (r'\|\|(.*)\|\|', pw)
                    # do not encode existing password that is already encoded
                    if encode:
                        if not m:
                            # obfuscate password into binhex using standard password
                            epw = self._obfuscateString(pw, key=self.__cfgFileCryptkey, encode=True)
                            # remove any cr/lf from the binhex encoding
                            epw = epw.replace('\n', '').replace('\r', '')
                            # replace password in array list with encoded password
                            line = line.replace(pw, '||' + epw + '||')
                    else:
                        if m:
                            # obfuscate password into binhex using standard password
                            dpw = self._obfuscateString(m.group(1), key=self.__cfgFileCryptkey, decode=True)
                            # replace encoded password in array list with plain-text password
                            line = line.replace(pw, dpw)
                    break
                # if match found

            # end of for loop id scan
            rtnList.append(line)  # append processed line

        # end of while loop config scan
        return ''.join(x for x in rtnList)

    def exists (self, path):
        if self._getSetting (path):
            return True
        return False

    def existsInPath (self, searchPath):
        if self.getSetting (searchPath):
            return True
        return False

    def getSettingBool (self, name, default=False):
        try:
            s = self.getSetting(name, default)
            if isinstance(s, list): # use the last entry for boolean testing ...
                s = s[-1]
            if s and (str(s).lower().strip() in ['true','t','y','1','yes', 'on']):
                return True

            return False
        except:
            pass
        return default

    def getSettingValue (self, name, default=''):
        try:
            s = self.getSetting(name, default)
            if s:
                return eval (str(s))
        except:
            pass
        return default

    def getSettingList (self, name, default=''):
        s = self.getSetting(name, default)
        if isinstance(s, list):
            # build a new list
            expdS = []
            for item in s:
                # determine setting type (string or non-string and run it through python parser)
                if self._paramIsType(item) is not None and self._paramIsType(item) >= 0:
                    item = eval(item)
                expdS.append(self._envVarExpand (item, self._getPath (name)))
            return expdS
        elif s:
            return [s]
        return []

    def setSetting (self, name, value, settings=None):
        try:
            name = name.upper()
            if settings == None:
                settings = self.settings

            serviceID = name.split('/', 1)
            if len(serviceID) > 1:
                try:
                    if serviceID[0] == "": return self.setSetting(serviceID[1], value)
                    return self.setSetting (serviceID[1], value, settings[serviceID[0]])
                except: return None
            else:
                self._assignParameter(name, value, settings)
        except Exception as inst:
            pass

    def deleteSetting (self, name, settings=None):
        try:
            name = name.upper()
            if settings == None:
                settings = self.settings

            serviceID = name.split('/', 1)
            if len(serviceID) > 1:
                try:
                    if serviceID[0] == "": return self.deleteSetting(serviceID[1])
                    return self.deleteSetting (serviceID[1], settings[serviceID[0]])
                except: return None
            else:
                del settings[name.upper()]
        except Exception as inst:
            pass

    def replaceSetting(self, name, value, settings=None):
        self.deleteSetting (name, settings)
        self.setSetting    (name, value, settings)

    # access item based upon name : LOGGING_NO or service path BlahGroup/BlahService/USERNAME
    # searches recursively down through the servicePath
    def getSetting (self, servicePath, default=''):
        param = ''
        paths   = servicePath.split ('/')
        if len(paths) > 1:
            del paths[-2]
            newPath = None
            for p in paths:
                if not newPath:
                    newPath = p
                else:
                    newPath = newPath + '/' + p
            param = self._getSetting(servicePath, self.getSetting (newPath, default))
        else:
            param = self._getSetting(servicePath, default)

        # determine setting type (string or non-string and run it through python parser)
        if self._paramIsType(param) is not None and self._paramIsType(param) >= 0:
            param = eval(param)
        if not param:
            param = default
        return param

    getSettingStr = getSetting

    def getSectionType (self, name):
        return self.getSetting (name+'/'+self.secType_ID)

    # return the service names set in the config file, return as list
    def getServices (self, secType=None):
        services = []
        for key, value in self.settings.items():
            if isinstance(value, dict) and ((secType == None) or (value[self.secType_ID] == secType)):
                services.append(key)
        return services

    # return the service names set in the config file, return as CSV string
    def getServicesAsCSV (self):
        servicesStr = ''
        first = True
        for item in self.getServices():
            if first:
                first = False
            else:
                servicesStr += ','

            servicesStr += '"' + item + '"'

        return servicesStr

    def printSettings (self, settings=None, depth=0):
        if not settings:
            settings = self.settings
            print ("ConfigLoader.printSettings")

        for idname, value in settings.items():
            if isinstance(value, dict):
                print (('   '*depth) + '[' + idname + ']' )
                self.printSettings(value, depth+1)
            else:
                print (('   '*depth) + idname + "=" + str(value))
