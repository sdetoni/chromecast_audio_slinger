import daemon.GlobalFuncs as GF
import slinger.SlingerGlobalFuncs as SGF
import json

self = eval('self'); output = self.output
postData = self.getCGIParametersFormData ()

if not "action"         in postData: postData["action"]       = ''
if not "scope"          in postData: postData["scope"]        = ''
if not "query"          in postData: postData["query"]        = ''
if not "result_limit"   in postData: postData["result_limit"] = GF.Config.getSettingValue('slinger/SEARCH_RESULT_LIMIT')

if postData['action'] == 'start' and postData["scope"] == 'db_metadata':
    results = SGF.DB.SearchMetaData( regex=postData["query"], maxResultsLen=int(postData["result_limit"]))
    output(json.dumps(results, indent=4))
    exit(0)
if postData['action'] == 'start' and postData["scope"] == 'directories':
    results = SGF.searchDirectoriesProcess(regex=postData["query"], maxResultsLen=int(postData["result_limit"]))
    if not results:
        exit(-1)

    output(json.dumps(results, indent=4))
    exit(0)
if postData['action'] == 'stop':
    SGF.AbortSearchDirectories()
    SGF.DB.AbortSearch()
    output ("ok")
    exit(0)
if postData['action'] == 'status':
    output(json.dumps(SGF.searchDirectoriesProcesState, indent=4))
    exit(0)

output ("nope")


