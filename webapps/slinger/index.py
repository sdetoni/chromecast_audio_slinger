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
    
    <script src='js/sha256.js'></script>

	<link rel="stylesheet" href="fontawesome/css/all.css" />
	<link rel="stylesheet" href="css/player_styles.css" />
	<link rel="stylesheet" href="css/gear.css" />			
</head>
""")

output (f"""
<script>
var G_OS_FileSeparator = "\\{os.sep}";
</script> 

<div id="playerView" class="rcorners1">
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
        <div style="display:none" class="playingInfo overlay-playinfo playerTxt" >
            <table border=0>
                <tr><td class="playerTxt">Song Title</td><td class="song-title playerTxt" id="songTitle"></td></tr>
                <tr><td class="playerTxt">Album Name</td><td class="song-title playerTxt" id="songAlbumName"></td></tr>
                <tr><td class="playerTxt">Artist</td>    <td class="song-title playerTxt" id="songArtist"></td></tr>
                <tr><td class="playerTxt">Filename</td>  <td class="song-title playerTxt" id="songFilename"></td></tr>
                <tr><td class="playerTxt">File Type</td> <td class="song-title playerTxt" id="songFileType"></td></tr>
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
                        <span style="width:30px;display:inline-block;">
                            <i id="playerControlsSmallBig" class="playerControls fa-solid fa-angles-up" onclick="changeViewSmallBig(! G_SmallBigViewMode)"></i>
                        </span><u style="white-space:nowrap">Chrome Cast Device</u>
                    </td>
                </tr>
                    <tr><td>
                        <select id="ccast_uuid">
                        </select>                    
                    </td>
                    <td style="text-align:center">
                        <i class="playerControls fa-solid fa-rotate-left" style="font-size: large;" onclick="GetChromeCastDevices(true);" title="Forced rescan of Chrome Cast Devices"><br><font style="display:none;white-space:nowrap" class="showHelpText controlsIconFont">Rescan</font></i>
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
                        <i class="playerControls fa-solid fa-rotate-left" style="font-size: xx-large;" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'seek', 0)" title="Restart Song"><br><font style="display:none" class="showHelpText controlsIconFont">Restart Song</font></i>
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
                <table style="min-width:50px;max-width:40px;float:right" border=0><tr>
                    <td style="padding-right:10px;white-space:nowrap;text-align:center">
                        <i id="plyrCntrlAddToPlayList" class="playerControls fa-solid fa-table-list hasContextMenu" style="font-size:large;" title="Add to Play List"><font style="display:none;" class="showHelpText controlsIconFont">Add to Play List</font></i>
                    </td>                
                    <td class="playerControls"><i id="volOnMute" class="fa-solid fa-volume-high" onclick="chromeCastMute($('#ccast_uuid').val())" title="Mute"></i></td>
                    <td class="playerTxt" style="width:100%;min-width:100px"><input type="range" min="1" max="100" value="50" id="volLevel" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'volume', ($(this).val()/100.0))"></td>
                    <td><i id="showHelpTextInfo" onclick="showHideIconInfo(! G_ShowHideIconInfo)" class="playerControls fa-solid fa-circle-info" style="font-size: larger;" title="Icon Info On/Off" onclick=""></td>                                                                  
                </table>
            </td>            
        </tr>
        <tr>
            <td colspan="100%">
                <table style="width:100%" border=0><tr>
                    <td class="playerTxt" id="songRangeHeader"></td>
                    <td class="playerTxt" style="width:100%"><input type="range" min="1" max="100" value="50" id="songRangePosition" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'seek', $(this).val())"></td>
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
            <li><a href="#tabFileBrowser">File Browser</a></li>
            <li><a href="#tabSearchBrowser">Search Browser</a></li>
            <li><a href="#tabMetaData">Meta Data</a></li>
        </ul>
        
        <div id="tabFileBrowser">
            <div>
                <table style="width:100%" border=0>
                <tr>
                    <td>
                        <span id="browserArt"><img src="img/folder.png"></span>
                    </td>
                    <td style="width:100%">       
                        <label for="shareLocs">File Locations</label>
                        <select name="shareLocs" id="share_locs"  onchange="OnChange_FileLocation(this)">
                        { shareLocs }
                        </select>
                    </td>
                    <td>
                        <table id="tabsLeftShrinkGrow" style="display:block !important"><tr>
                            <td style="padding-right:10px">
                                <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                            </td>                            
                            <td>
                                <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                            </td>   
                        </tr></table>                          
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
                          <fieldset style="padding:2px">
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
                                  <td style="width:100%">
                                      <table border=0 style="white-space:nowrap"><tr>
                                      <td>
                                          <label class="inlinePlayListControls" for="searchDBMetaData">DB MetaData</label>
                                          <input class="inlinePlayListControls" type="radio" name="searchScope" value="db_metadata" id="searchDBMetaData" checked="checked">                                                        
                                          <label class="inlinePlayListControls" for="searchFileLocations">File Locations</label>
                                          <input class="inlinePlayListControls" type="radio" name="searchScope" value="directories" id="searchFileLocations">
                                      </td>
                                      <td style="width:100%;text-align:right">                                      
                                          <span style="width:100%;text-align:right" id="searchResultsInfo"></span>
                                      </td>                                  
                                      </tr></table>
                                  </td>
                                  <td>
                                      <span class="loader-container search-running" style="display:none"><div class="gear"><img src="img/gear.png"/></div></span>                                  
                                  </td>                                     
                              </tr>
                              </table>
                          </fieldset>                    
                    </div>                    
                </td>
                <td>
                    <table id="tabsLeftShrinkGrow" style="display:block !important"><tr>
                        <td style="padding-right:10px">
                            <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                        </td>                            
                        <td>
                            <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                        </td>   
                    </tr></table>                          
                </td>
            </tr></table> 
            <div id="searchList" style="width:100%"></div>                         
        </div>
    
        <div id="tabMetaData">
            <table id="tableMetaData" style="width:100%" class="SongListFormat">
                <tr><th colspan="100%">Music Meta Data Options</th></tr>
                <tr><td><li><a href="#" onclick="confirm ('Clear all loaded DB Meta Data?') ? chromeCastBasicAction($('#ccast_uuid').val(), 'clear_metadata_cache') || setTimeout (metadataScraperInfo, 2000) : false;">Clear Metadata Cache</a></li></td></tr>
                <tr><td><li><a href="#" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'start_metadata_scraper'); setTimeout (metadataScraperInfo, 2000);">Start Metadata Scraper</a></li></td></tr>
                <tr><td><li><a href="#" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'stop_metadata_scraper');  setTimeout (metadataScraperInfo, 2000); ">Stop Metadata Scraper</a></li></td></tr>
                <tr><td>&nbsp;</td></tr>
                <tr><th>Meta Data Scraping Status<th></tr>
                <tr><td id="metadataScrapeStatus" colspan="100%"></td></tr>
                <tr>
                    <td>
                        <table id="tabsLeftShrinkGrow" style="display:block !important"><tr>
                            <td style="padding-right:10px">
                                <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                            </td>                            
                            <td>
                                <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
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
                                <i class="playerControls fa-solid fa-broom" style="font-size: larger;text-align:center;" title="Clear Queue" onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'queue_clear')"><br><font style="display:none" class="showHelpText controlsIconFont">Clear Queue</font></i>
                            </td>                            
                            <td style="width:100%">      
                                &nbsp;                     
                                <input type="text" placeholder="Enter new playlist name" id="playlist_name_field" style="color:black">
                                <i class="playerControls fa-solid fa-square-plus" style="font-size: larger;text-align:center;" title="Save Queue as Playlist" onclick="QueueListToPlaylist($('#playlist_name_field').val())"><br><font style="display:none" class="showHelpText controlsIconFont">Save Queue as Playlist</font></i>                                
                            </td>                  
                            <tr></table>
                        </td>                                                                  
                    </tr>
                </table>
            </div>         
            <div>
                <table id="tabsRightShrinkGrow" style="display:block !important"><tr>
                    <td style="padding-right:10px">
                        <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                    </td>                            
                    <td>
                        <i class=" fa-solid fa-angles-right selectItemHand" onclick="tabShrinkGrow('grow');"></i>
                    </td>   
                </tr></table>                          
            </div>
            <div id="queueBrowser"></div>
        </div>              
        <div id="tabPlaylistBrowser">            
            <div id="playlistBrowserControls" class="rcorners1">
                <table><tr>
                    <td>
                        <span>
                            <input type="text" placeholder="Enter new playlist name" id="newPlayListName" style="color:black">
                            <i class="playerControls fa-solid fa-square-plus" style="font-size: larger;text-align:center;" title="Create Playlist" onclick="CreatePlayList($('#newPlayListName').val())"><br><font class=" showHelpText  controlsIconFont">Create Playlist</font></i>                  
                        </span>
                    </td>                                            
                </tr></table>
            </div>           
            <div>
                <table id="tabsRightShrinkGrow" style="display:block !important"><tr>
                    <td style="padding-right:10px">
                        <i class=" fa-solid fa-angles-left selectItemHand" onclick="tabShrinkGrow('shrink');"></i>
                    </td>                            
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

""")
output ("""
</html>
""")

