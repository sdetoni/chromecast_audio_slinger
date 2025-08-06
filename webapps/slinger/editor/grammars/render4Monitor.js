// 1. an almost complete python grammar in simple JSON format
var render4Monitor_grammarDefinition = {
    
    // prefix ID for regular expressions used in the grammar
    "RegExpID" : "RegExp::",

    //
    // Style model
    "Style" : {
        // lang token type  -> Editor (style) tag
        "decorator":    "constant.support",
        "comment":      "comment",
        "keyword":      "keyword",
        "builtin":      "constant.support",
        "variable":     "variable",
        "operator":     "constant",
        "identifier":   "identifier",
        "number":       "constant.numeric",
        "heredoc":      "string",
        "ViewService":  "string.regexp",
        "TstServer":    "string.regexp" ,
        "TstService" :  "string.regexp"
    },

    
    //
    // Lexical model
    "Lex" : {
    
        // comments
        "comment" : {
            "type" : "comment",
            "tokens" : [
                // null delimiter, matches end-of-line
                ["#",  null],
                ["/*",  "*/"]
            ]
        },
               
        // View External Service
        "ViewService" : [ 
                       "RegExp::/\\<(.*?\>)\>*/"
                    ],

        // test sub service
        "TstService" : [ 
                       "RegExp::/\\[\\[(.*\\]?)\\]\\]*/"
                    ],              

        "TstServer" : [ 
                       "RegExp::/\\[(.*\\]?)\\]*/"
                    ],              
                            
        
        // php variables
        "variable" :  [ 
                       "RegExp::/\\$\\{(.*?\\})\\}*/",
                       "RegExp::/\\|[_A-Za-z][_A-Za-z0-9]*/",
                       "RegExp::/\\![_A-Za-z][_A-Za-z0-9]*/"
                      ],

        
        // blocks, in this case heredocs
        "heredoc" : {
            "type" : "escaped-block",
            "escape" : "\\",
            "tokens" : [ 
                // begin and end of heredocs
                // if no end given, end is same as start of block                
                [ "RegExp::/\"\"\"/",], // """ string \" pattern"""
                [ "RegExp::/\'\'\'/",], // ''' string \' pattern'''
                [ "RegExp::/\"/",],     // ' string \' pattern'
                [ "RegExp::/\'/",],     // " string \" pattern"
                ["||"],    // config obfuscated password colour
                [ "RegExp::/([rubRUB]|(ur)|(br)|(UR)|(BR))?('{3}|\"{3})/", 6 ] 
            ]
        },
        
        // general identifiers
        "identifier" : "RegExp::/[_A-Za-z][_A-Za-z0-9]*/",

        // numbers, in order of matching
        "number" : [
            // floats
            "RegExp::/\\d*\\.\\d+(e[\\+\\-]?\\d+)?[jJ]?/",
            "RegExp::/\\d+\\.\\d*[jJ]?/",
            "RegExp::/\\.\\d+[jJ]?/",
            // integers
            // hex
            "RegExp::/0x[0-9a-fA-F]+[lL]?/",
            // binary
            "RegExp::/0b[01]+[lL]?/",
            // octal
            "RegExp::/0o[0-7]+[lL]?/",
            // decimal
            "RegExp::/[1-9]\\d*(e[\\+\\-]?\\d+)?[lL]?[jJ]?/",
            // just zero
            "RegExp::/0(?![\\dx])/"
        ],

        // strings
        "string" : {
            "type" : "escaped-block",
            "escape" : "",
            "tokens" : [ 
                // start, end of string (can be the matched regex group ie. 1 )
                [ "RegExp::/(['\"])/", 1 ], 
                [ "RegExp::/([rubRUB]|(ur)|(br)|(UR)|(BR))?(['\"])/", 6 ] 
            ]
        },
        
        // operators
        "operator" : {
            "combine" : true,
            "tokens" : [
                "*", "=", "+", "-", "==", ":" 
            ]
        },
        
        // delimiters
        "delimiter" : {
            "combine" : true,
            "tokens" : [ 
                "(", ")", "[", "]", "<", ">", "${", "}"
            ]
        },

        // decorators
        "decorator" : "RegExp::/@[_A-Za-z][_A-Za-z0-9]*/",

        // keywords
        "keyword" : {
            // enable autocompletion for these tokens, with their associated token ID
            "autocomplete" : true,
            "tokens" : [
                "RegExp::/INCLUDE/i",
                "RegExp::/END-SCOPE-GLOBAL/i",
                "RegExp::/END-SCOPE/i",

                "RegExp::/_HOUSE_KEEPING_/i",
                
                "RegExp::/LOGGING_DIR/i",
                "RegExp::/LOGGING_LEVEL/i",
                "RegExp::/LOGGING_SIZE/i",
                "RegExp::/LOGGING_NO/i",

                "RegExp::/WS_SERVERNAME/i",
                "RegExp::/WS_HTTP_PORT/i",
                "RegExp::/WS_HTTPS_PORT/i",
                "RegExp::/WS_SSL_SERVER_PEM/i",
                "RegExp::/WS_SSL_CA-BUNDLE-CRT/i",
                
                "RegExp::/WS_VIEWER_AUTH_USERNAME/i",
                "RegExp::/WS_VIEWER_AUTH_PASSWORD/i",
                "RegExp::/WS_ADMIN_AUTH_USERNAME/i",
                "RegExp::/WS_ADMIN_AUTH_PASSWORD/i",
                "RegExp::/WS_FILTER_NETWORK/i",

                "RegExp::/MONITOR_REFRESH_DELAY/i",
                "RegExp::/MANUAL/i",

                "RegExp::/NOTIFY_SERVICE_DRIVER/i",
                "RegExp::/NOTIFY_EMAIL_SMTP_SERVER/i",
                "RegExp::/NOTIFY_EMAIL_TO/i",
                "RegExp::/NOTIFY_EMAIL_FROM/i",
                "RegExp::/NOTIFY_EMAIL_SUBJ_STUB/i",
                "RegExp::/NOTIFY_DELIVERY_PERIOD/i",
                "RegExp::/NOTIFY_ON_FAILURE_LIMIT/i",

                "RegExp::/EVENT_PROCESSOR_DELAY/i",
                "RegExp::/EVENT_PROCESSOR_SINGLE_THREAD/i",

                "RegExp::/SELENIUM_DRIVER_LOC/i",
                "RegExp::/SELENIUM_EXEC_LOC/i",
                
                "RegExp::/PHANTOMJS_EXEC_LOC/i"
            ]
        },
                              
        // builtin functions, constructs, etc..
        "builtin" : {
            // enable autocompletion for these tokens, with their associated token ID
            "autocomplete" : true,
            "tokens" : [
            
                "RegExp::/MAX_KEEP_DATAHISTORY_DAYS/i",
            
                "RegExp::/USERNAME/i",
                "RegExp::/PASSWORD/i",
                "RegExp::/VISIBLE_IN_MONITOR/i",
                "RegExp::/SCRAPER_CACHE_ON/i",
                "RegExp::/SCRAPER_CACHE_DIR/i",
                "RegExp::/SCRAPER_CACHE_DLTIMEOUT/i",
                "RegExp::/SCRAPER_CACHE_KEEPAGE/i",

                "RegExp::/SCRAPER_CACHE_OUTPUT_KEEPAGE/i",

                "RegExp::/SERVICE_PAGE_DRIVER/i",
                "RegExp::/BEFORE_LOAD_URL_PYCODE/i",
                "RegExp::/LOAD_URL/i",
                "RegExp::/NAVIGATE_URL_PYCODE/i",
                "RegExp::/AFTER_LOAD_URL_PYCODE/i",
                "RegExp::/AUTHENTICATE_ON/i",
                "RegExp::/SEND_BASIC_AUTHENTICATE/i",
                "RegExp::/DISABLE_ANCHORS/i",
                "RegExp::/REFRESH_TIME/i",
                "RegExp::/DEBUG_URL/i",
                "RegExp::/HEADER_PARAM/i",
                "RegExp::/POST_PARAM/i",
                "RegExp::/POST_CONTENT/i",
                "RegExp::/PYCODE_MATCH_TEST/i",
                "RegExp::/VALID_MATCH_TEST/i",
                "RegExp::/FAILED_MATCH_TEST/i",
                "RegExp::/HTML_TITLE/i",
                "RegExp::/WARN_SSL_CERT_TEST/i",
                "RegExp::/WARN_SSL_CERT_DAYS_BEFORE_EXPIRE/i",

                "RegExp::/CRON_NO_TESTING_PERIOD/i",
                "RegExp::/CRON_TEST_ONLY_PERIOD/i",

                "RegExp::/ON_EXCEPTION_PYCODE/i",
                "RegExp::/BEFORE_DBSTORE_PYCODE/i",

                "RegExp::/SOCKET_DEBUG/i",
                "RegExp::/SOCKET_ADDRESS/i",
                "RegExp::/SOCKET_SEND/i",
                "RegExp::/SOCKET_TIMEOUT/i",
                
                "RegExp::/LOCALPROC_DEBUG/i",
                "RegExp::/LOCALPROC_RUN/i",  

                "RegExp::/SELENIUM_BASIC_AUTH_ON/i",
                "RegExp::/SELENIUM_OUTPUT_TYPE/i",
                "RegExp::/SELENIUM_RENDER_AUTOSIZE/i",
                "RegExp::/SELENIUM_RENDER_CROP/i",
                "RegExp::/SELENIUM_RENDER_DELAY/i",
                "RegExp::/SELENIUM_TIMEOUT/i",
                "RegExp::/SELENIUM_NAVIGATE_DELAY/i",
                "RegExp::/SELENIUM_DRIVER_CFG_PYCODE/i",
                "RegExp::/SELENIUM_INIT_PYCODE/i",
                "RegExp::/SELENIUM_NAVIGATE_PYCODE/i",
                "RegExp::/SELENIUM_END_PYCODE/i",
                "RegExp::/SELENIUM_ONEXIT_PYCODE/i",               
                
                "RegExp::/SELENIUM_SNAP_OUTPUT/i",
                "RegExp::/SELENIUM_SNAP_MAX_HISTORY/i",
                
                "RegExp::/PHANTOMJS_OUTPUT_TYPE/i",
                "RegExp::/PHANTOMJS_RENDER_DELAY/i",
                "RegExp::/PHANTOMJS_TIMEOUT/i",
                "RegExp::/PHANTOMJS_RENDER_TIMED_OUT_OUTPUT/i",
                "RegExp::/PHANTOMJS_NAVIGATE_DELAY/i",
                "RegExp::/PHANTOMJS_INIT_JSCODE/i",
                "RegExp::/PHANTOMJS_NAVIGATE_JSCODE/i",
                "RegExp::/PHANTOMJS_END_JSCODE/i",
                "RegExp::/PHANTOMJS_ONEXIT_JSCODE/i",

                "RegExp::/PHANTOMJS_SNAP_OUTPUT/i",
                "RegExp::/PHANTOMJS_SNAP_MAX_HISTORY/i"
            ]
        }
    },

    //
    // Syntax model (optional)
    //"Syntax" : null,
    
    // what to parse and in what order
    "Parser" : [
        "variable",
        "heredoc",
        "comment", 
        "ViewService", 
        "TstService",              
        "TstServer",  
        "number",
        "decorator",
        "operator",
        "delimiter",
        "keyword",
        "builtin",
        "identifier",       
    ]
};
