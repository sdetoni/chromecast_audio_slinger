import daemon.GlobalFuncs         as GF
import slinger.SlingerGlobalFuncs as SGF
import os
import pychromecast
from   smb.SMBConnection import SMBConnection
from hashlib import sha256

# https://github.com/home-assistant-libs/pychromecast/blob/master/examples

self = eval('self'); output = self.output # this code is cosmetic to remove the red syntax highlight error from the pycharm ide

chromecasts = SGF.getCachedChromeCast()

output ("""
<html>
<head>
	<title>Chromecast Audio Slinger for Local and Network CIFS Content</title>
	<meta name="viewport" content="width=device-width, initial-scale=1.0" charset="utf-8" />	
    <link rel="stylesheet" href="jquery-ui/jquery-ui.css">     
    <script src="jquery-ui/jquery-3.7.1.js"></script>
    <script src="jquery-ui/jquery-ui.js"></script>
           
    <script src="jquery-contextMenu/jquery.contextMenu.min.js"></script>
    <link rel="stylesheet" href="jquery-contextMenu/jquery.contextMenu.css"/>
    
    <script type="text/javascript" src="jquery-toast/jquery.toast.js"></script>
    <link rel="stylesheet" href="jquery-toast/jquery.toast.css">
    
    <link rel="stylesheet" href="slider/slider.css">    
    <script type="text/javascript" src="slider/slider.js"></script>

    <script src='js/sha256.js'></script>

	<link rel="stylesheet" href="fontawesome/css/all.css" />
	<link rel="stylesheet" href="css/player_styles.css" />
	<link rel="stylesheet" href="css/gear.css" />	
    <link rel="stylesheet" href="css/vfd-spinner.css">				
</head>
""")

output (f"""
<script>
var G_OS_FileSeparator                = "\\{os.sep}";
var G_LoadFileFolderArt               = {str(GF.Config.getSettingBool('slinger/LOAD_FILE_LIST_FOLDER_ART_ICONS', 'true')).lower()};
var G_DisableSongSeek                 = {str(GF.Config.getSettingBool('slinger/DISABLE_SONG_SEEK', 'true')).lower()};
var G_Local_Player                    = "{SGF.LOCAL_PLAYER}";
var G_Local_Player_UniqueID           = "";
var G_Generated_Local_Player_UniqueID = "";
</script> 
<div id="audio-player-container" style="display:hidden">
  <audio id="LocalAudioPlayerDevice"       src="" playing_now="">
</div>
<div id="playerView" class="rcorners1">
    <div id="video-player-container" style="display:none; width:100%">
        <video id="LocalVideoPlayerDevice"  src="" controls  style="width:100%;height:calc((9 / 16) * 100vw);max-height:calc(100vh - 169px);">
    </div> 
    <div id="busy-transcoding" class="vfd-container"> 
        <div style="position: absolute; right: 59%; top:10%;">
                <div class="vfd-vfd-waveform vfd-wave2">
                  <!-- 18 vfd-bars -->
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                </div>
                <div class="vfd-vfd-waveform vfd-wave1">
                  <!-- 18 vfd-bars -->
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                  <div class="vfd-bar"></div><div class="vfd-bar"></div><div class="vfd-bar"></div>
                </div>
            </div>  
        <div class="vfd-label">      
            <div>TRANSCODING</div>
            <div id="vfd-transcode-location"></div>
        </div>
    </div>        
    <div class="overlay-containerSml" style="display:none">    
        <div style="display:none" class=" playingInfo overlay-playinfo playerTxt" >
            <table border=0>
                <tr><td class="playerTxt"><img id="albumArtURLSml" class="selectItemHand albumArtURLSml" onclick="ViewLargeArt(this);" src="img/folder.png" style="height: 32px;"></td><td style="width:100%" class="song-title playerTxt" id="songTitleSml"></td></tr>
            </table>
        </div>
    </div>
    <div class="overlay-containerBig">    
        <div id="playingAlbumArt" class="overlay-albumArt">
            <img id="albumArtURL" onclick="ViewLargeArt(this);" class="selectItemHand" src="img/folder.png" style="height: 200px;">
        </div>
        <div id="playingSongInfo" style="display:none" class="playingInfo overlay-playinfo playerTxt" >
            <table border=0>
                <tr><td class="playerTxt" style="white-space:nowrap">Song Title</td><td class="song-title playerTxt" id="songTitle"></td></tr>
                <tr><td class="playerTxt" style="white-space:nowrap">Album Name</td><td class="song-title playerTxt" id="songAlbumName"></td></tr>
                <tr><td class="playerTxt" style="white-space:nowrap">Artist</td>    <td class="song-title playerTxt" id="songArtist"></td></tr>
                <tr><td class="playerTxt" style="white-space:nowrap">File Name</td> <td class="song-title playerTxt" id="songFilename"></td></tr>
                <tr><td class="playerTxt" style="white-space:nowrap">File Type</td> <td class="song-title playerTxt" id="songFileType"></td></tr>
            </table>
        </div>
    </div>
         
    <div style="width:100%;height:7px"></div>    
    <div id="playerControls" class="rcorners1">
    <table border=0 style="width:100%">        
        <tr>
            <td style="">
                <table>
                <tr>
                    <td class="playerTxt">
                        <span style="display:inline-block;">
                            <i id="playerControlsSmallBig" class="playerControls fa-solid fa-angles-up" onclick="changeViewSmallBig(! G_SmallBigViewMode)"></i>
                        </span><u style="white-space:nowrap;padding-left: 10px;">Casting Device</u>
                    </td>
                </tr>
                    <tr><td>
                        <select id="ccast_uuid">
                        </select>                    
                    </td>
                    <td style="text-align:center">                    
                        <table border=0 class="playerControls" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'awaken_monitoring');">
                            <tr>
                                <td><i class="playerControls fa-solid fa-rotate-left" style="font-size: x-large;padding-left:5px" onclick="GetChromeCastDevices(true);" title="Forced rescan of Chrome Cast Devices"></i></td>
                            </tr>
                            <tr>
                                <td><font style="display:none;white-space:nowrap" class="showHelpText controlsIconFont">Rescan</font></td>
                            </tr>
                        </table>
                    </td>
                    <td id="ChromeCastAwakeMonitorTab" style="text-align:center">
                        <table border=0 class="playerControls" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'awaken_monitoring');">
                            <tr style="color:#eb9a43 !important">
                                <td><i class="playerControls fa-solid fa-bed" style="font-size:  x-large;padding-left:5px;padding-right:5px;color:#eb9a43 !important" title="Awake Monitoring"></i></td>
                                <td><font style="white-space:nowrap" class="controlsIconFont" title="Awake Monitoring">Slinger is Hibernating</font></td>
                            </tr>
                            <tr><td colspan="100%">
                                <font style="display:none;white-space:nowrap" class="showHelpText controlsIconFont">Awake Monitoring</font>
                            </td></tr>
                        </table>
                    </td>              
                    <td id="ChromeCastNetWrkSharedLocalPlayerTab" style="text-align:center;display:none">
                        <table border=0 class="playerControls">
                            <tr>
                                <td>
                                    <div>
                                        <label class="NetWrkSharedPlayerInstance" for="NetWrkSharedLocalPlayerCB">Network Shared</label>
                                        <input type="checkbox" class="jquery-ui-cb" name="unique_instance" id="NetWrkSharedLocalPlayerCB" title="Network Shared Instance" onclick="return SwitchUniqueLocalPlayer();"></td>
                                    </div>
                            </tr>
                            <tr><td colspan="100%">
                                <font style="display:none;white-space:nowrap" class="showHelpText controlsIconFont">Set/Unset Network Shared Local Player Instance</font>
                            </td></tr>
                        </table>
                    </td>                                              
                </tr>
                </table>            
            </td>
            <td style="width:100%">      
                <table border=0><tr>  
                <td style="width:50%"></td>                
                <td style="min-width:300px;">
                    <table border=0 style="max-width:300px;min-width:100px;width:100%;text-align:center"><tr>                
                    <td>
                        <i id="plyrCntrlShuffle" class="playerControls fa-solid fa-shuffle" style="font-size: xx-large;" title="Shuffle On/Off" onclick="chromeCastShuffle($('#ccast_uuid').val())"><br><font style="display:none" class="showHelpText controlsIconFont">Shuffle On/Off</font></i>
                    </td>
                    <td>
                        <i class="playerControls fa-regular fa-circle-stop" style="font-size: xx-large;" title="Stop Play" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'stop')"><br><font style="display:none" class="showHelpText controlsIconFont">Stop Play</font></i>
                    </td>
                    <td>
                        <i id="plyrCntrlPlay" class="playerControls fa-regular fa-circle-play" style="font-size: xxx-large;" title="Play/Pause" onclick="chromeCastPlay('', $('#ccast_uuid').val()), $('#share_locs').find('option:selected').attr('type')")><br><font style="display:none" class="showHelpText controlsIconFont">Play/Pause</font></i>
                    </td>                
                    <td>
                        <i class="playerControls fa-solid fa-rotate-left" style="font-size: xx-large;" onclick="OnClick_RestartSong()" title="Restart Song"><br><font style="display:none" class="showHelpText controlsIconFont">Restart Song</font></i>
                    </td>                                                                                    
                    <td>
                        <i class="playerControls fa-solid fa-forward-step" title="Next Song" style="font-size: xx-large;" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'queue_next')"><br><font style="display:none" class="showHelpText controlsIconFont">Next Song</font></i>
                    </td>
                    <tr></table>
                </td>
                <td style="width:50%"></td>
                </tr></table>                
            </td>                        
            <td style="">
                <table style="min-width:50px;max-width:40px;float:right;" border=0>
                <tr>
                    <td style="padding-right:10px;white-space:nowrap;text-align:center">
                        <i id="plyrCntrlAddToFavs" onclick="FavouriteAddRemove()" class="playerControls fa-solid fa-star" style="font-size:x-large;" title="Add/Remove Favourite"><font style="display:none;" class="showHelpText controlsIconFont">Add/Remove Favourite</font></i>
                    </td>                    
                    <td style="padding-right:10px;white-space:nowrap;text-align:center">
                        <i id="plyrCntrlAddToPlayList" class="playerControls fa-solid fa-table-list hasContextMenu" style="font-size:x-large;" title="Add to Play List"><font style="display:none;" class="showHelpText controlsIconFont">Add to Play List</font></i>
                    </td>                
                    <td class="playerControls"><i id="volOnMute" class="fa-solid fa-volume-high" onclick="chromeCastMute($('#ccast_uuid').val())" title="Mute"></i></td>
                    <td class="playerTxt" style="width:100%;min-width:100px"><input type="range" min="1" max="100" value="50" id="volLevel" oninput="chromeCastBasicAction($('#ccast_uuid').val(), 'volume', ($(this).val()/100.0))"></td>
                </tr>
                <tr><td style="height:5px"></td></tr>
                <tr>                    
                    <td colspan="100%" style="text-align:right">
                        <i id="showHelpTextInfo" onclick="showHideIconInfo(! G_ShowHideIconInfo)" class="playerControls fa-solid fa-circle-info" style="text-align:center" title="Icon Info On/Off">
                            <font style="display: none;" class="showHelpText controlsIconFont">This text info</font>
                        </i>                                                   
                        <i id="showAbout"        onclick="About()"                                class="playerControls fa-solid fa-at"          style="text-align:center" title="About the Author">
                            <font style="display: none;" class="showHelpText controlsIconFont">Author</font>
                        </i>                           
                        <i id="showCfgCog"       onclick="showConfigEditor()"                     class="playerControls fa-solid fa-cog"         style="text-align:center" title="Config Editor">
                            <font style="display: none;" class="showHelpText controlsIconFont">Config Editor</font>
                        </i>                           
                        <i id="showLogViewer"    onclick="window.open('logviewer.py', '_blank');"                        class="playerControls fa-solid fa-file-lines"  style="text-align:center" title="Server Log Viewer">
                            <font style="display: none;" class="showHelpText controlsIconFont">Server Log Viewer</font>
                        </i>    
                    </td>                                                                  
                </table>
            </td>            
        </tr>
        <tr>
            <td colspan="100%">
                <table style="width:100%" border=0><tr>
                    <td class="playerTxt" id="songRangeHeader"></td>
                    <td class="playerTxt" style="width:100%">
""")

if GF.Config.getSettingBool('slinger/DISABLE_SONG_SEEK', True):
    output ("""<progress min="1" max="100" value="50" id="songRangePosition" style="cursor: default;"></progress>""")
else:
    output ("""<input type="range" min="1" max="100" value="50" id="songRangePosition" onchange="OnClick_SeekSong(this)">""")

output (f"""                        
                    </td>
                    <td class="playerTxt" id="songRangeFooter"></td>
                </tr></table>
            </td>
        </tr>
    </table>
    </div>
</div>
""")

############## Load the available data sources ################

shareLocs = ""
for fileInfo in GF.Config.getSettingList ('slinger/FILE_MUSIC_PATH'):
    shareLocs += f"<option type='file' value='{ fileInfo.rstrip(os.sep) }'>{fileInfo.rstrip(os.sep)}</option>\n"

for shareInfo in GF.Config.getSettingList ('slinger/SMB_MUSIC_UNCPATH'):
    un, pw, serv, sName, fp = SGF.parseSMBConfigString (shareInfo)
    val = ('\\\\' + serv + '\\' + sName + '\\' + fp).rstrip('\\')
    shareLocs += f"<option type='smb' value='{ val }'>{val}</option>\n"

output (f"""
<table style="width:100%"><tr>               
<td id="tabsLeftSize" style="width:50%;vertical-align:top">
    <div id="tabsLeft">
        <ul>
            <li><a id="tabFileBrowserSelect" href="#tabFileBrowser">File Browser</a></li>
            <li><a href="#tabSearchBrowser">Search Browser</a></li>
            <li><a href="#tabMetaData">Meta Data</a></li>
        </ul>
        
        <div id="tabFileBrowser">
            <div>
                <table style="width:100%" border=0>
                <tr>
                    <td style="width:100%">       
                        <label for="shareLocs">File Locations</label>
                        <select name="shareLocs" id="share_locs"  onchange="OnChange_FileLocation(this)">
                        { shareLocs }
                        </select>
                    </td>
                    <td>
                        <table class="tabsLeftShrinkGrowHideShow tabsLeftShrinkGrow"><tr>
                            <td>
                                <i class="fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                            </td>     
                            <td class="shrinkgrow_pos"></td>                       
                            <td>
                                <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                            </td>   
                        </tr></table>                          
                    </td>
                    <td>
                        <span id="browserArt"><img src="img/folder.png"></span>
                    </td>                    
                </tr>
                </table>
            </div>
            <div id="fileBrowser"></div>        
        </div>
        
        <div id="tabSearchBrowser">
            <table class="SongListFormat" style="width:100%"><tr>
                <td>                             
                    <div>
                          <fieldset style="padding:2px;width:100%">
                              <legend>Search Query: </legend>
                              <table border=0>
                              <tr style="vertical-align:top">
                                  <td style="width:100%">
                                      <input class="" type="input" id="searchQuery"  placeholder="Enter regex queries" style="width:100%" >                                                                            
                                  </td>                                                            
                                  <td style="padding-left: 5px;text-align: center;">                                       
                                      <i id="searchBut" class="fa-solid fa-angles-right inlinePlayListControls" onclick="runSearchQuery();"></i>
                                      <br><font style="display:none; white-space:nowrap" class="showHelpText controlsIconFont">Run Query</font>
                                  </td>
                              </tr>
                              <tr>                              
                                  <td style="width:100%" colspan="100%">
                                      <table border=0 style="white-space:nowrap"><tr>
                                      <td>
                                          <label class="" for="searchDBMetaData">DB MetaData</label>
                                          <input class="" type="radio" name="searchScope" value="db_metadata" id="searchDBMetaData" checked="checked">                                                        
                                          <label class="" for="searchFileLocations">File Locations</label>
                                          <input class="" type="radio" name="searchScope" value="directories" id="searchFileLocations">
                                      </td>
                                      <td id="searchResultsInfo"></td>                                  
                                      </tr></table>
                                  </td>                                  
                              </tr>
                              </table>
                          </fieldset>                    
                    </div>                    
                </td>
                <td>
                    <table class="tabsLeftShrinkGrowHideShow tabsLeftShrinkGrow"><tr>
                        <td>
                            <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                        </td>                    
                        <td class="shrinkgrow_pos"></td>         
                        <td>
                            <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                        </td>   
                    </tr></table>                          
                </td>
            </tr></table> 
            <div id="searchList" style="width:100%"></div>                         
        </div>
    
        <div id="tabMetaData">
            <table id="tableMetaData" style="width:100%" class="SongListFormat" border=0>
                <tr><th colspan="100%">Music Meta Data Options</th></tr>
                <tr style="white-space:nowrap">
                    <td>
                        <a href="#" onclick="confirm ('Clear all loaded DB Meta Data?') ? chromeCastBasicAction($('#ccast_uuid').val(), 'clear_metadata_cache') || setTimeout (metadataScraperInfo, 2000) : false;">
                            <button style="cursor:pointer">Clear Metadata Cache</button>
                        </a>
                    </td>
                    
                    <td>
                        <a href="#" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'start_metadata_scraper'); setTimeout (metadataScraperInfo, 2000);">
                            <button style="cursor:pointer">Start Metadata Scraper</button>
                        </a>
                    </td>
                    
                    <td>
                        <a href="#" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'validate_metadata');  setTimeout (metadataScraperInfo, 2000); ">
                        <button style="cursor:pointer">Validate Metadata</button>
                        </a>
                    </td>                    
                    <td>
                        <a href="#" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'stop_metadata_scraper');  setTimeout (metadataScraperInfo, 2000); ">
                        <button style="cursor:pointer">Stop Metadata Scraper</button>
                        </a>
                    </td>
                        
                    <td style="width:100%">
                    </td>                                                                
                </tr>

                <tr><td>&nbsp;</td></tr>
                               
                <tr><th colspan="100%">Meta Data Scraping Status</th></tr>
                <tr><td id="metadataScrapeStatus" colspan="100%"></td></tr>
                <tr>
                    <td>
                        <table class="tabsLeftShrinkGrowHideShow tabsLeftShrinkGrow" border=0><tr>
                            <td>
                                <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                            </td>
                            <td class="shrinkgrow_pos"></td>                             
                            <td>
                                <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                            </td>   
                        </tr></table>                          
                    </td>
                </tr>               
                
                <tr><td>&nbsp;</td></tr>
                
                <tr><th colspan="100%">Spotify Playlist Importer</th></tr>
                <tr id="ImportSpotifyPlayListID">             
                    <td colspan="100%" style="white-space:nowrap">
                        <table class="SongListFormat"><tr>
                            <td style="width:100%">
                                <input placeholder="https://open.spotify.com/playlist/..." type="text" style="width:100%" id="spotify_playlist_url">
                            </td>
                            <td style="white-space:nowrap">
                                <a href="#" onclick="ImportSpotifyPlayList($('#spotify_playlist_url').val(), $('#ImportSpotifyPlayListID')); setTimeout (metadataScraperInfo, 2000);">
                                    <button style="cursor:pointer">Import &amp; Match</button>
                                </a>
                            </td>
                        </tr></table>
                    </td>                    
                </tr>                                
                <tr><td colspan="100%" style="height:100%"></td></tr>  
            </table>        
        </div>      
    </div>    
</td>
<td id="tabsRightSize" style="width:50%;vertical-align:top">
    <div id="tabsRight">
        <ul>
            <li><a id="tabQueueBrowserSelect"    href="#tabQueueBrowser">Queue Browser</a></li>
            <li><a id="tabPlaylistBrowserSelect" href="#tabPlaylistBrowser">Play List Browser</a></li>
        </ul>
        <div id="tabQueueBrowser">        
            <div id="queueBrowserControls" class="rcorners1">
                <table border=0 style="width:100%">        
                    <tr>                    
                        <td style="width:100%">        
                            <table border=0 style="text-align:left"><tr>
                            <td>
                                <i class="inlinePlayListControls fa-solid fa-broom" style="text-align:center;" title="Clear Queue" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'queue_clear')"><br><font style="display:none" class="showHelpText controlsIconFont">Clear Queue</font></i>
                            </td>                            
                            <td style="width:100%;text-align:right">      
                                &nbsp;                     
                                <input type="text" placeholder="Enter new playlist name" id="playlist_name_field" style="color:black;vertical-align:middle">
                                <i class="inlinePlayListControls fa-solid fa-square-plus" style="text-align:center;" title="Save Queue as Playlist" onclick="QueueListToPlaylist($('#playlist_name_field').val())"><br><font style="display:none" class="showHelpText controlsIconFont">Save Queue as Playlist</font></i>                                
                            </td>                  
                            <tr></table>
                        </td>                                                                  
                    </tr>
                </table>
            </div>         
            <div>
                <table class="tabsRightShrinkGrowHideShow tabsRightShrinkGrow"><tr>
                    <td>
                        <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                    </td>
                    <td class="shrinkgrow_pos"></td>                             
                    <td>
                        <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                    </td>   
                </tr></table>                          
            </div>
            <div id="queueBrowser"></div>
        </div>              
        <div id="tabPlaylistBrowser">            
            <div id="playlistBrowserControls" class="rcorners1">
                <table style="width:100%;text-align:right"><tr>
                    <td>
                            <input type="text" placeholder="Enter new playlist name" id="newPlayListName" style="color:black;vertical-align:middle">
                            <i class="inlinePlayListControls  fa-solid fa-square-plus" style="text-align:center;" title="Create Playlist" onclick="CreatePlayList($('#newPlayListName').val())"><br><font class=" showHelpText  controlsIconFont">Create Playlist</font></i>
                    </td>                                            
                </tr></table>
            </div>           
            <div>
                <table class="tabsRightShrinkGrowHideShow tabsRightShrinkGrow"><tr>
                    <td>
                        <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                    </td>
                    <td class="shrinkgrow_pos"></td>                             
                    <td>
                        <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                    </td>   
                </tr></table>                          
            </div>                            
            <div id="playlistBrowser"></div>      
        </div>
</td>    
</tr></table>

<ul id="#playListContextMenu"></ul>
<script src="js/player.js"></script>

<!-- configuration Editor container -->
<div id="configEditorDialog" title="Configuration Editor" style="display:none;"></div>

""")
output ("""
</html>
""")


