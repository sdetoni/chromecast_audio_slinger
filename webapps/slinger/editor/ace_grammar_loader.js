function ace_grammar_loader(acePath, _editor, grammar)
{
    ace.config.set("basePath", acePath);
    ace.config.set("modePath", acePath);
    ace.config.set("themePath", acePath);
    ace.config.set("workerPath", acePath);
    var editor       = ace.edit(_editor);

    // 2. parse the grammar into an ACE syntax-highlight mode
    var mode = AceGrammar.getMode( grammar );
    var Editor = ace.require("ace/editor").Editor;

    // editor commands
    var commands = {
        
        defaults : {
            toggleCommentLines : {win: "Ctrl-L", mac: "Command-L"},
            toggleCommentBlock : {win: "Alt-L", mac: "Alt-L"}
        },
        
        toggleCommentLines : {
            name: "toggleCommentLines",
            exec: function(editor) {
                editor.toggleCommentLines();
            },
            bindKey: null
        },
        
        toggleCommentBlock : {
            name: "toggleCommentBlock",
            exec: function(editor) {
                editor.toggleBlockComment();
            },
            bindKey: null
        }
    };
    commands.toggleCommentLines.bindKey = commands.defaults.toggleCommentLines;
    commands.toggleCommentBlock.bindKey = commands.defaults.toggleCommentBlock;

    // editor options
    var options = {
        toggleCommentLinesKey: {
            set: function(val) {
                if (val) 
                    commands.toggleCommentLines.bindKey = val;
                else 
                    commands.toggleCommentLines.bindKey = commands.defaults.toggleCommentLines;
            },
            value: commands.defaults.toggleCommentLines
        },
        toggleCommentBlockKey: {
            set: function(val) {
                if (val) 
                    commands.toggleCommentBlock.bindKey = val;
                else 
                    commands.toggleCommentBlock.bindKey = commands.defaults.toggleCommentBlock;
            },
            value: commands.defaults.toggleCommentBlock
        },
        enableToggleCommentLines: {
            set: function(val) {
                if (val) 
                    this.commands.addCommand(commands.toggleCommentLines);
                else 
                    this.commands.removeCommand(commands.toggleCommentLines);
            },
            value: false
        },
        enableToggleCommentBlock: {
            set: function(val) {
                if (val) 
                    this.commands.addCommand(commands.toggleCommentBlock);
                else 
                    this.commands.removeCommand(commands.toggleCommentBlock);
            },
            value: false
        },
        onlyKeywordsAutoComplete: {
            set: function(val) {
                if ( this.getOption('enableBasicAutocompletion') )
                {
                    if (val) 
                    {
                        this._completers = this._completers || this.completers.slice();
                        // keyword completer taken from the grammar mode
                        this.completers = [ this.completers[2] ];
                    }
                    else if ( this._completers )
                    {
                        // default completers
                        this.completers = this._completers;
                        this._completers = null;
                    }
                }
            },
            value: false
        }
    };
    ace.config.defineOptions(Editor.prototype, "editor", options);
    
    // enable syntax validation
    mode.supportGrammarAnnotations = true;
    
    // 3. use it with ACE
    ace.config.loadModule("ace/ext/language_tools", function() {
        
        editor.setOptions({ 
            enableBasicAutocompletion: true,
            //enableSnippets: true,
            enableToggleCommentLines: true,
            enableToggleCommentBlock: true
        });
        editor.setOptions({ 
            onlyKeywordsAutoComplete: true
        });
        editor.getSession().setMode( mode );
        //editor.clearSelection();
    });
    
    return editor;
}