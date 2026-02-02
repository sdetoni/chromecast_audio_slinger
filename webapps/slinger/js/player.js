
class TableSelection
{
    constructor (id, ignoreTopRowNum=0)
    {
        this.id = id;
        this.ignoreTopRowNum = ignoreTopRowNum;

        this.selectionPivot = null;
        this.LEFT_MOUSE_BUTTON = 1; // 1 for left button, 2 for middle, and 3 for right.
        this.trs    = $(id + ' tbody tr'); // get the table list of data
        this.idTds  = $(id + ' .dataRow'); // table row columns.

        // embed the this reference in the idTds objs so it can be referenced via mouse events.
        // otherwise the this references the table row object which is not what you totally want!
        for (let idx = 0; idx <this.idTds.length; idx++)
        {
            this.idTds[idx]['EmbeddedThis'] = this;
            this.idTds[idx].onselectstart = function() { return false; };
            $(this.idTds[idx]).mousedown (this.processMouseEvent);
        }
    }

    processMouseEvent (event)
    {
        if(event.which != this.EmbeddedThis.LEFT_MOUSE_BUTTON)
        {
            return;
        }

        var row = this;
        if (!event.ctrlKey && !event.shiftKey)
        {
            this.EmbeddedThis.clearAll();
            this.EmbeddedThis.toggleRow(row);
            this.EmbeddedThis.selectionPivot = row;
            return;
        }
        if (event.ctrlKey && event.shiftKey)
        {
            this.EmbeddedThis.selectRowsBetweenIndexes (this.EmbeddedThis.selectionPivot.rowIndex, row.rowIndex);
            return;
        }
        if (event.ctrlKey)
        {
            this.EmbeddedThis.toggleRow(row);
            this.EmbeddedThis.selectionPivot = row;
        }
        if (event.shiftKey)
        {
            this.EmbeddedThis.clearAll();
            this.EmbeddedThis.selectRowsBetweenIndexes( this.EmbeddedThis.selectionPivot.rowIndex, row.rowIndex);
        }
    }

    toggleRow(row)
    {
        if ($(row).hasClass('selected'))
            $(row).removeClass('selected');
        else
            $(row).addClass('selected');
    }

    selectRowsBetweenIndexes(ia, ib)
    {
        var bot = Math.min(ia, ib);
        var top = Math.max(ia, ib);
        for (var i = bot; i <= top; i++)
        {
            $(this.trs[i-(this.ignoreTopRowNum)]).addClass('selected');
        }
    }

    clearAll()
    {
        for (var i = 0; i < this.trs.length; i++)
        {
            $(this.trs[i-(this.ignoreTopRowNum)]).removeClass('selected');
        }
    }
}
function generateUUID()
{ // Public Domain/MIT
    var d = new Date().getTime();//Timestamp
    var d2 = ((typeof performance !== 'undefined') && performance.now && (performance.now()*1000)) || 0;//Time in microseconds since page-load or 0 if unsupported
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16;//random number between 0 and 16
        if(d > 0){//Use timestamp until depleted
            r = (d + r)%16 | 0;
            d = Math.floor(d/16);
        } else {//Use microseconds since page-load if supported
            r = (d2 + r)%16 | 0;
            d2 = Math.floor(d2/16);
        }
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

function nvl (str, val="")
{
    if (str == null)
        return val
    return str
}
function escapeRegExp(text)
{
  return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
}

function humanFileSize(bytes, si=false, dp=1)
{
    const thresh = si ? 1000 : 1024;
    if (Math.abs(bytes) < thresh)
    {
        return bytes + ' B';
    }
    const units = si ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'] : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
    let u = -1;
    const r = 10**dp;
    do
    {
        bytes /= thresh;
        ++u;
    } while (Math.round(Math.abs(bytes) * r) / r >= thresh && u < units.length - 1);
    return bytes.toFixed(dp) + ' ' + units[u];
}

function ModalWindowLargeArt (picHTML)
{
    $('#ViewLargeArt').remove();
    $('<div id="ViewLargeArt" />').html(picHTML).dialog
    ({
        height:'auto',
        width:'50%',
        modal:true,
        show: {
            effect: "fade",
            duration: 350
        },
        hide: {
            effect: "fade",
            duration: 350
        },
        position: {
            my: "top",
            at: "top+10"
        },
        open: function (event, ui) {
            $(this).css('overflow', 'hidden');
            $(this).parent().addClass ("custom-no-titlebar");

             $('.ui-widget-overlay').bind('click', function()
             {
                 $("#ViewLargeArt").dialog('close');
             });
        },
        close:function (event, ui) {
        }
    });
}

function FolderLoadLargeArt (location, type)
{
  if (location != "" && type != "")
  {
        $.ajax ({url: `artwork.py`,
                 type: "POST",
                 data: {
                     "location" : location,
                     "type"     : type
                 },
                 dataType: "json",
                 success: function(data)
                 {
                    // console.log(data);

                    picHTML = `
<div class="slider-container">
`;
                    for (idx = 0; idx < data.length; idx++)
                    {
                        picHTML += `
<div class="AlbumArtWork slider-fade" style="overflow:auto">
  <div class="slider-numbertext playerTxt">${idx+1} / ${data.length}</div>
  <img id="AlbumArtWork_Img_${idx+1}" onclick="\$(this).parent().parent().parent().dialog('close');" style="transform-origin: top left; width: -webkit-fill-available;" src="${data[idx]['src']}" style="width:100%">
  <div class="text selectItemHand slider-title playerTxt" onclick="ArtworkGotoFolder('${  (data[idx]['full_path']).replaceAll('\\', '\\\\') }', '${ data[idx]['type'] }' ); $(this).parent().parent().parent().dialog('close');">${data[idx]['filename']}</div>
</div>
`;
                    }

                    picHTML += `
<a class="slider-prev playerTxt" onclick="G_ArtWorkSlider.incDecSlide(-1)">❮</a>
<a class="slider-next playerTxt" onclick="G_ArtWorkSlider.incDecSlide(1)">❯</a>
</div>

<div style="text-align:center; position:relative;">
    <input class="slider-zoom" style="width:100%; outline: none;" type="range" id="zoomSlider" min="0.1" max="5" step="0.1" value="1" oninput="$('#AlbumArtWork_Img_'+G_ArtWorkSlider.slideIndex).css('transform', 'scale(' + this.value + ')')">
</div>

<div style="text-align:center; position:relative">
`;
                    for (idx = 0; idx < data.length; idx++)
                    {
                        picHTML += `<span class="slider-dot" onclick="G_ArtWorkSlider.thisSlide(${idx+1})"></span>`;
                    }

                    picHTML += `
</div>
<script>
    var G_ArtWorkSlider = new Slider ('AlbumArtWork', 1)
    G_ArtWorkSlider.show(1);
</script>
`;
                     ModalWindowLargeArt (picHTML);
                 }
                });
    }
}

function ViewLargeArt (imgObj)
{
    console.log ($(imgObj).attr('src'));

    let picHTML = `<img onclick="\$(this).parent().dialog('close');" style="width:100%" src=${$(imgObj).attr('src')}>`;

    let loc = type = ""
    try
    {
        let u = new URL ($(imgObj).attr('src'));
        loc  = u.searchParams.get('location');
        type = u.searchParams.get('type');
    }
    catch
    {
        loc = type = ""
    }

    if (loc != "" && type != "")
    {
        FolderLoadLargeArt (loc, type)
    }
    else
    {
        ModalWindowLargeArt (picHTML);
    }
}

function resizeFilePanels ()
{
    // calculate viewing height for fileList
    try{ $('#fileList').css('height',      `${$(window).innerHeight() - $('#fileList').offset().top      - 10}px`)  } catch {}
    try{ $('#searchList').css('height',    `${$(window).innerHeight() - $('#searchList').offset().top    - 10}px`)  } catch {}
    try{ $('#tableMetaData').css('height', `${$(window).innerHeight() - $('#tableMetaData').offset().top - 10}px`)  } catch {}


    try{ $('#playlistBrowser').css('height', `${$(window).innerHeight() - $('#playlistBrowser').offset().top - 10}px`) } catch {}
    try{ $('#queueBrowser').css('height',    `${$(window).innerHeight() - $('#queueBrowser').offset().top    - 10}px`) } catch {}
    // console.log (`{$(window).innerHeight()}  playlistBrowser:${$('#playlistBrowser').offset().top}`)
}

var TabPos  = 3;
function tabShrinkGrow (action)
{
    let leftChar = "&#9500;";
    let indexChar = "&#9579;";
    let dashChar = "&#9472";
    let rightChar = "&#9508;";

    if (action == 'grow')
    {
        TabPos++;
        if (TabPos >= 5)
            TabPos = 5;
    }
    else if (action == 'shrink')
    {
        TabPos--;
        if (TabPos <= 1)
            TabPos = 1;
    }

    switch (TabPos)
    {
        case 3: // [--|--]
            $('#tabsLeftSize').css('display', '');
            $('#tabsLeftSize').css('width', '50%');
            $('#tabsRightSize').css('display', '');
            $('#tabsRightSize').css('width', '50%');
            $('.tabsLeftShrinkGrowHideShow').css('display', '');
            $('.tabsRightShrinkGrowHideShow').css('display', 'none');
            $('.shrinkgrow_pos').html(`${leftChar}${dashChar}${dashChar}<b class="shrinkgrow_posidx">${indexChar}</b>${dashChar}${dashChar}${rightChar}`);
            break;

        case 2: // [-|---]
            $('#tabsLeftSize').css('display', '');
            $('#tabsLeftSize').css('width', '25%');
            $('#tabsRightSize').css('display', '');
            $('#tabsRightSize').css('width', '75%');
            $('.tabsLeftShrinkGrowHideShow').css('display', '');
            $('.tabsRightShrinkGrowHideShow').css('display', 'none');
            $('.shrinkgrow_pos').html(`${leftChar}${dashChar}<b class="shrinkgrow_posidx">${indexChar}</b>${dashChar}${dashChar}${dashChar}${rightChar}`);
            break;

        case 1: // [|----]
            $('#tabsLeftSize').css('display', 'None');
            $('#tabsLeftSize').css('width', '0%');
            $('#tabsRightSize').css('display', '');
            $('#tabsRightSize').css('width', '100%');
            $('.tabsLeftShrinkGrowHideShow').css('display', 'none');
            $('.tabsRightShrinkGrowHideShow').css('display', '');
            $('.shrinkgrow_pos').html(`${leftChar}<b class="shrinkgrow_posidx">${indexChar}</b>${dashChar}${dashChar}${dashChar}${dashChar}${rightChar}`);
            break;

        case 4: // [---|-]
            $('#tabsLeftSize').css('display', '');
            $('#tabsLeftSize').css('width', '75%');
            $('#tabsRightSize').css('display', '');
            $('#tabsRightSize').css('width', '25%');
            $('.tabsLeftShrinkGrowHideShow').css('display', '');
            $('.tabsRightShrinkGrowHideShow').css('display', 'none');
            $('.shrinkgrow_pos').html(`${leftChar}${dashChar}${dashChar}${dashChar}<b class="shrinkgrow_posidx">${indexChar}</b>${dashChar}${rightChar}`);
            break;

        case 5: // [----|]
            $('#tabsLeftSize').css('display', '');
            $('#tabsLeftSize').css('width', '100%');
            $('#tabsRightSize').css('display', 'None');
            $('#tabsRightSize').css('width', '0%');
            $('.tabsLeftShrinkGrowHideShow').css('display', '');
            $('.tabsRightShrinkGrowHideShow').css('display', 'none');
            $('.shrinkgrow_pos').html(`${leftChar}${dashChar}${dashChar}${dashChar}${dashChar}<b class="shrinkgrow_posidx">${indexChar}</b>${rightChar}`);
            break;
    }
}
$( document ).ready(function()
{
    tabShrinkGrow ('init');
});

var G_LastChromeCastInfo          = null;
var G_LastChromeCastQueueChangeNo = -1;
var G_DefaultCoverArt = 'img/folder.png';
var G_DefaultCoverAudioArt = 'img/folder_audio.png';
var G_DefaultCoverVideoArt = 'img/folder_video.png';

// #######################################################################################################

function isVideo (mimeType)
{
    if ((typeof(mimeType) == "string") &&  (mimeType != "") && (mimeType.split("/")[0].trim().toLowerCase() == "video"))
        return true;
    return false
}

function isAudio (mimeType)
{
    if ((typeof(mimeType) == "string")  && (mimeType != "") && (mimeType.split("/")[0].trim().toLowerCase() == "audio"))
        return true;
    return false
}

function getDefaultCoverArt (mimeType=null)
{   
    if (mimeType && isVideo (mimeType))
        return G_DefaultCoverVideoArt;
    else if (mimeType && isAudio (mimeType))
        return G_DefaultCoverAudioArt;
    else
        return G_DefaultCoverArt;
}

function metadataScraperInfo ()
{
    ccast_uuid = $('#ccast_uuid').val();

    $.ajax ({url: `castcontroller.py`,
             type: "POST",
             data: {
                "ccast_uuid" : ccast_uuid,
                "action"     : "status_metadata_scraper"
             },
             dataType: "json",
             success: function(data)
             {
                 // console.log (data);

                 let fpath = data['file_path'];
                 if (data['processing_filename'] != '')
                    fpath += data['processing_filename'];

                 var tabStatus = `
<table style="width:100%" border=0>
<tr>
    <td style="white-space:nowrap;width:100%">Active:</td>
    <td style="white-space:nowrap;text-align:right">${data['active']}</td>
</tr>
<tr>
    <td style="white-space:nowrap;width:100%">Meta Data File Num Loaded:</td>
    <td style="white-space:nowrap;text-align:right">${data['metadata_num']}</td>
</tr>
<tr>
    <td style="white-space:nowrap">Processing:</td>
</tr>
<tr>
    <td colspan="100%">${fpath}</td>
</tr>
<tr><td colspan="100%">&nbsp;</td></tr>
<tr>
    <td style="white-space:nowrap;width:100%">Next Scraping Event:</td>
    <td style="white-space:nowrap;text-align:right">${data['next_process_event']}</td>
</tr>
</table>
`
                 $('#metadataScrapeStatus').html(tabStatus);

                 if (data['active'])
                    setTimeout(metadataScraperInfo, 1000);
                 else
                    setTimeout(metadataScraperInfo, 10000);
             },
             error: function(jqXHR, textStatus, errorThrown)
             {
                 // On error, log the error to console
                 console.error(`Error: ${textStatus}, ${errorThrown}`);
                 setTimeout(metadataScraperInfo, 10000);
             }
           });
}

function BaseLocalPlayerID ()
{
    return G_Local_Player.split('::')[0];
}
function isLocalPlayer (ccast_uuid)
{
    return (ccast_uuid.split('::')[0] == BaseLocalPlayerID());
}

// gather chromecast current status on selected device
$( document ).ready(function()
{

function VideoEventHandler(e)
{
    if ( ((e.type === "pause") && (G_LastChromeCastInfo.playback_state == 'PLAYING'))  ||
         ((e.type === "play") && (G_LastChromeCastInfo.playback_state == 'PAUSED')) )
    {
        chromeCastPlay('', $('#ccast_uuid').val()), $('#share_locs').find('option:selected').attr('type')
    }
}

$('#LocalVideoPlayerDevice').on ("pause", VideoEventHandler);
$('#LocalVideoPlayerDevice').on ("play", VideoEventHandler);

setTimeout(metadataScraperInfo, 1000);

var cciIntvalID = setInterval(chromeCastInfo, 1000);
var ccReqNum    = 0
function chromeCastInfo ()
{
    ccast_uuid = $('#ccast_uuid').val();

    function clearSongTitleInfo ()
    {
         $('#songAlbumName').html('');
         $('#songArtist').html('');
         $('#songTitle').html('');
         $('#songTitleSml').html('');
         $('#songFilename').html('');
         $('#songFileType').html('');
         $('#albumArtURL').prop('src', getDefaultCoverArt());
         $('#albumArtURLSml').prop('src', getDefaultCoverArt());
         $('.playingInfo').css('display', 'none');

         $('#plyrCntrlPlay').css('color', '');
         $('#plyrCntrlAddToFavs').removeClass ('SongIsFavourite');
    }

    ccReqNum++;
    $.ajax ({url: `castinfo.py`,
             type: "POST",
             data: {
                "ccast_uuid" : ccast_uuid,
                "type"       : "player_status"
             },
             dataType: "json",
             success: function(data)
                     {
                         const zeroPad = (num, places) => String(num).padStart(places, '0');

                         if ((! data) || (data.playback_state.toLowerCase() == 'unknown'))
                         {
                             clearSongTitleInfo ();
                         }

                         if (! data)
                         {
                            return;
                         }

                         // -------- Local Player Driver/Actions --------
                         if (data && isLocalPlayer(ccast_uuid) && (data.playback_state != 'IDLE'))
                         {
                             let audio = $("#LocalAudioPlayerDevice");
                             let video = $("#LocalVideoPlayerDevice");
                             let thisAVID  = ""
                             let thisAVDev = null;

                             if (isVideo (data.content_type))
                             {
                                 thisAVDev = video
                                 thisAVID  = "#LocalVideoPlayerDevice";
                                 $("#video-player-container").show(500, function() {
                                     resizeFilePanels();
                                 });
                             }
                             else
                             {
                                 thisAVDev = audio
                                 thisAVID  = "#LocalAudioPlayerDevice";
                                 $("#video-player-container").css("display","None");
                             }

                             if (data.slinger_current_media.location && (data.playback_state.toLowerCase() == 'playing') )
                             {
                                 if ($(thisAVDev).attr('playing_now') != data.slinger_current_media.location)
                                 {
                                     thisAVDev.attr('src', `accessfile.py?type=${data.slinger_current_media.type}&location=${encodeURI(data.slinger_current_media.location)}&ccast_uuid=${encodeURI(ccast_uuid)}`)
                                     thisAVDev.attr('playing_now', data.slinger_current_media.location)
                                     thisAVDev[0].pause();
                                     thisAVDev[0].load();
                                     thisAVDev[0].play();
                                     thisAVDev[0].loop = false;
                                     thisAVDev[0].volume = data.volume_level;
                                     thisAVDev[0].muted  = data.volume_muted;

                                     if (thisAVID == "#LocalVideoPlayerDevice")
                                         audio[0].pause();
                                     else
                                         video[0].pause();
                                 }
                                 else if (thisAVDev[0].paused)
                                 {
                                     // song completed, next song ...
                                     if (thisAVDev[0].ended)
                                     {
                                         chromeCastBasicAction(ccast_uuid, 'queue_next')
                                     }
                                     else
                                     {
                                         // if not already playing, then load track then play/unpause
                                         if (thisAVDev[0].currentTime <= 0)
                                         {
                                             thisAVDev[0].pause();
                                             thisAVDev[0].load();
                                             thisAVDev[0].loop = false;
                                         }

                                         thisAVDev[0].play();
                                         thisAVDev[0].volume = data.volume_level;
                                         thisAVDev[0].muted  = data.volume_muted;
                                     }
                                 }
                             }
                             else if ((data.playback_state.toLowerCase() == 'paused') && (! thisAVDev[0].paused && thisAVDev[0].duration > 0))
                             {
                                thisAVDev[0].pause()
                             }
                             else if ((data.playback_state.toLowerCase() == 'idle') && (! thisAVDev[0].paused &&  thisAVDev[0].duration > 0))
                             {
                                 thisAVDev[0].pause()
                                 thisAVDev[0].currentTime = 0;
                                 $(thisAVID).attr('src', '');
                                 $(thisAVID).attr('playing_now', '');
                             }

                             data.duration     = thisAVDev[0].duration;
                             data.current_time = thisAVDev[0].currentTime;

                             if (G_LastChromeCastInfo && G_LastChromeCastInfo.volume_level != data.volume_level)
                             {
                                thisAVDev[0].volume = data.volume_level;
                             }

                             if (G_LastChromeCastInfo && G_LastChromeCastInfo.volume_muted != data.volume_muted)
                             {
                                thisAVDev[0].muted  = data.volume_muted;
                             }
                         }
                         // --------------------------------------------

                         if ((! G_LastChromeCastInfo) || (data && G_LastChromeCastInfo.slinger_shuffle != data.slinger_shuffle))
                         {
                             if (data.slinger_shuffle)
                             {
                                 $('#plyrCntrlShuffle').removeClass('cntrlInactive').addClass('cntrlActive');
                             }
                             else if (! data.slinger_shuffle)
                             {
                                 $('#plyrCntrlShuffle').removeClass('cntrlActive').addClass('cntrlInactive');
                             }
                         }

                         if ((! G_LastChromeCastInfo) || data)
                         {
                             let currentFileListPath = decodeURIComponent($('#fileListCurrentLocation').attr('filelocationparent')).toLocaleLowerCase();

                             if (data.slinger_metadata_shuffle_location != '' && data.slinger_metadata_shuffle_location.toLocaleLowerCase() != currentFileListPath)
                             {
                                 if ($('#metaDataShuffle').hasClass('cntrlActive'))
                                 {
                                     $('#metaDataShuffle').removeClass('cntrlActive').addClass('cntrlInactive');
                                     $('#shuffleMetaFileType').selectmenu( "enable");
                                     $('#shuffleMetaFileType').prop("selectedIndex", 0).change();
                                     $('#shuffleMetaFileType').selectmenu('refresh');
                                 }
                             }
                             else
                             {
                                 if (data.slinger_metadata_shuffle && (! $('#metaDataShuffle').hasClass('cntrlActive')) )
                                 {
                                      $('#metaDataShuffle').removeClass('cntrlInactive').addClass('cntrlActive');
                                      $('#shuffleMetaFileType').val(data.slinger_metadata_shuffle_type).change();
                                      $('#shuffleMetaFileType').selectmenu( "disable");
                                      $('#shuffleMetaFileType').selectmenu('refresh');
                                 }
                                 else if ((! data.slinger_metadata_shuffle) && (! $('#metaDataShuffle').hasClass('cntrlInactive')) )
                                 {
                                     $('#metaDataShuffle').removeClass('cntrlActive').addClass('cntrlInactive');
                                     $('#shuffleMetaFileType').selectmenu( "enable");
                                 }
                             }

                             // show/update the current metadata shuffle info/path
                             if ((data.slinger_metadata_shuffle+"" != $('#metaDataShuffleActiveDot').attr('shuffle_active')) ||
                                 ($('#metaDataShuffleActivePath').attr('shuffle_fullpath') != data.slinger_metadata_shuffle_location))
                             {
                                 let d = data.slinger_metadata_shuffle_location.substring(0, 28);
                                 if (data.slinger_metadata_shuffle_location.length > 28)
                                 {
                                    d += '...';
                                 }

                                 $('#metaDataShuffleActivePath').html(d);
                                 $('#metaDataShuffleActivePath').attr('shuffle_fullpath', data.slinger_metadata_shuffle_location);

                                 if (data.slinger_metadata_shuffle)
                                 {
                                     $('#metaDataShuffleActiveDot').css ('display', '');
                                     $('#metaDataShuffleActiveDot').attr('title', `${data.slinger_metadata_shuffle_location}\nClick to stop metadata shuffle!`);
                                 }
                                 else
                                 {
                                     $('#metaDataShuffleActiveDot').css ('display', 'none');
                                 }
                                 $('#metaDataShuffleActiveDot').attr('shuffle_active', data.slinger_metadata_shuffle)
                             }
                         }

                         // --------------------------------------------
                         if (data.volume_muted && $('#volOnMute').hasClass('fa-volume-high'))
                         {
                             $('#volOnMute').removeClass('fa-volume-high')
                             $('#volOnMute').addClass('fa-volume-xmark')
                             $('#volOnMute').prop('title', 'Unmute')
                         }
                         else if ((! data.volume_muted) && $('#volOnMute').hasClass('fa-volume-xmark'))
                         {
                             $('#volOnMute').removeClass('fa-volume-xmark')
                             $('#volOnMute').addClass('fa-volume-high')
                             $('#volOnMute').prop('title', 'Mute')
                         }

                         if (Math.floor(data.volume_level * 100) != $('#volLevel').val())
                         {
                             $('#volLevel').val(Math.floor(data.volume_level * 100))
                         }

                         // --------------------------------------------

                         // console.log("JSON Data:", data);
                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.album_name != data.album_name))
                             $('#songAlbumName').html(data.album_name);

                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.artist != data.artist))
                             $('#songArtist').html(data.artist);

                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.title != data.title))
                         {
                             $('#songTitle').html(data.title);
                             $('#songTitleSml').html(data.title);

                             // determine if this in Favourites
                             ShowIsFavourite(data);
                         }

                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.filename != data.filename))
                             $('#songFilename').html(data.filename);

                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.content_type != data.content_type))
                             $('#songFileType').html(`${data.content_type} ${ data.media_metadata.bitrate ? ':: ' + data.media_metadata.bitrate : ''}`);

                         if (($('.playingInfo').css('display') == 'none') && (data.playback_state.toLowerCase() != 'unknown'))
                             $('.playingInfo').css('display', '');

                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.playback_state != data.playback_state))
                         {
                             if (data.playback_state.toLowerCase() == 'playing')
                             {
                                 $('#plyrCntrlPlay').removeClass('cntrlActive').removeClass('cntrlInactive').addClass('cntrlPaused');
                                 $('#plyrCntrlPlay').removeClass('fa-circle-play');
                                 $('#plyrCntrlPlay').addClass('fa-circle-pause');
                             }
                             else if ((data.playback_state.toLowerCase() == 'idle') || (data.playback_state.toLowerCase() == 'paused'))
                             {
                                 $('#plyrCntrlPlay').removeClass('cntrlPaused').removeClass('cntrlInactive').addClass('cntrlActive');
                                 $('#plyrCntrlPlay').addClass('cntrlActivated');
                                 $('#plyrCntrlPlay').removeClass('fa-circle-pause');
                                 $('#plyrCntrlPlay').addClass('fa-circle-play');
                             }
                             else if (data.playback_state.toLowerCase() == 'unknown')
                             {
                                 $('#plyrCntrlPlay').removeClass('cntrlActive').removeClass('cntrlPaused').addClass('cntrlInactive');
                                 $('#plyrCntrlPlay').removeClass('fa-circle-pause');
                                 $('#plyrCntrlPlay').addClass('fa-circle-play');
                             }
                         }

                         // --------------------------------------------
                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.slinger_current_media.transcoding != data.slinger_current_media.transcoding ||
                                                          G_LastChromeCastInfo.slinger_current_media.location    != data.slinger_current_media.location) )
                         {
                              if (data.slinger_current_media.transcoding)
                              {
                                  $('#playingSongInfo').css('display', 'none');
                                  $('#busy-transcoding').css('display', 'flex');
                                  $('#vfd-transcode-location').html(data.slinger_current_media.location);
                              }
                              else
                              {
                                  $('#playingSongInfo').css('display', 'block');
                                  $('#busy-transcoding').css('display', 'none');
                              }
                         }
                         if ((! G_LastChromeCastInfo) || (G_LastChromeCastInfo.current_time != data.current_time) )
                         {
                             // some tracks do not have the full duration encoded in the mp3 files, in these cases, only show current time.
                             if ((data.current_time > 0) && (! data.duration))
                             {
                                 let ct  = zeroPad(parseInt(data.current_time/60), 2) + ':' + zeroPad ((parseInt(data.current_time)%60), 2);

                                 $('#songRangePosition').prop('min', 0);
                                 $('#songRangePosition').prop('max', data.current_time);
                                 $('#songRangePosition').val(data.current_time);

                                 $('#songRangeHeader').html(ct);
                                 $('#songRangeFooter').html('&infin;');
                             }
                             else if (data.duration)
                             {
                                 let ct  = zeroPad(parseInt(data.current_time/60), 2) + ':' + zeroPad ((parseInt(data.current_time)%60), 2);
                                 let tt  = zeroPad(parseInt(data.duration/60), 2) + ':' + zeroPad ((parseInt(data.duration)%60), 2);
                                 let pct = ((100.0 / data.duration) * data.current_time).toFixed(0);

                                 $('#songRangePosition').prop('min', 0);
                                 $('#songRangePosition').prop('max', data.duration);
                                 $('#songRangePosition').val(data.current_time);
                                 $('#songRangeHeader').html(ct);
                                 $('#songRangeFooter').html(tt);
                             }
                             else
                             {
                                 $('#songPosition').html('');
                                 $('#songRangePosition').prop('min', 0);
                                 $('#songRangePosition').prop('max', 0);
                                 $('#songRangePosition').val(0);
                                 $('#songRangeHeader').html('00:00');
                                 $('#songRangeFooter').html('00:00');
                             }

                             // update song position
                             $('#songPosition').attr("min", 0);
                             $('#songPosition').attr("max", data.duration);
                             $('#songPosition').val(data.current_time);
                         }

                         // --------------------------------------------

                         if ((! G_LastChromeCastInfo) ||
                             (G_LastChromeCastInfo.media_metadata.album_art_url != data.media_metadata.album_art_url) ||
                             (isVideo (data.content_type) != isVideo(G_LastChromeCastInfo.content_type))
                             )
                         {
                             if (data.media_metadata.album_art_url)
                             {
                                 let safeURLPath = new URL (data.media_metadata.album_art_url);
                                 artURLPath = safeURLPath.pathname + safeURLPath.search;
                                 $('#albumArtURL').prop('src', artURLPath);
                                 $('#albumArtURLSml').prop('src', artURLPath);
                             }
                             else
                             {
                                 $('#albumArtURL').prop('src', getDefaultCoverArt (data.content_type));
                                 $('#albumArtURLSml').prop('src', getDefaultCoverArt (data.content_type));
                             }
                         }

                         // --------------------------------------------

                         // Display if queue/player monitoring is in sleep mode...
                         if ((data.slinger_sleeping_sec > 4) && ($('#ChromeCastAwakeMonitorTab').css('display') == 'none'))
                         {
                             $('#ChromeCastAwakeMonitorTab').css('display', 'block');
                         }
                         else if ((data.slinger_sleeping_sec < 4) && ($('#ChromeCastAwakeMonitorTab').css('display') != 'None'))
                         {
                            $('#ChromeCastAwakeMonitorTab').css('display', 'none');
                         }

                         if (isLocalPlayer(ccast_uuid))
                         {
                             $('#ChromeCastNetWrkSharedLocalPlayerTab').css('display', 'block');
                         }
                         else
                         {
                            $('#ChromeCastNetWrkSharedLocalPlayerTab').css('display', 'none');
                         }

                         // console.log (data.slinger_sleeping_sec + ' ' + $('#ChromeCastAwakeMonitorTab').css('display'));
                         // console.log ("data.slinger_queue_changeno :: " + data.slinger_queue_changeno);
                         // --------------------------------------------
                         if (G_LastChromeCastQueueChangeNo != data.slinger_queue_changeno)
                         {
                             G_LastChromeCastQueueChangeNo = data.slinger_queue_changeno;
                             $.ajax ({url: `castinfo.py`,
                                      type: "POST",
                                      data : {
                                          "ccast_uuid" : ccast_uuid,
                                          "type"       : "queue_list"
                                      },
                                      dataType: "json",
                                      success: function(queue)
                                      {
                                          let qbTable  = `
<table id="queueBrowserTable" border=0 class='TableSelection SongListFormat' style="width:100%">
<thead>
<tr><th></th><th>Song Title(s) : ${queue.length}</th><th>Album Name</th><th>Artist</th></tr>
</thead>
`;
                                          if (queue)
                                          {
                                              for (idx = 0; idx < queue.length; idx++)
                                              {
                                                  qbTable += `
<tr class="dataRow selectItemHand" rowid="${idx}">
    <td><img onclick="ViewLargeArt(this);" class="albumArtURLSml" content_type="${queue[idx].metadata["content_type"]}" src="${queue[idx].metadata["album_art_url"] ? queue[idx].metadata["album_art_url"] : getDefaultCoverArt (queue[idx].metadata["content_type"]) }" style="height: 32px;"></td>
    <td onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'play_queued_item_at_index', ${idx});">${queue[idx].metadata["title"]}</td>
    <td onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'play_queued_item_at_index', ${idx});">${queue[idx].metadata["albumName"]}</td>
    <td onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'play_queued_item_at_index', ${idx});">${queue[idx].metadata["artist"]}</td>
    <td onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'del_queued_item_at_index',  ${idx});"><i class="inlinePlayListControls fa-solid fa-square-minus" style="text-align:center;" title="Remove Item" onclick=""></td>
</tr>`;
                                              }
                                          }
                                          qbTable += "</table>";

                                          $('#queueBrowser').html(qbTable);
                                          let l = new TableSelection("#queueBrowser", 2);
                                      },
                                      error: function(jqXHR, textStatus, errorThrown)
                                      {
                                          console.error(`Error: ${textStatus}, ${errorThrown}`);
                                      }
                                    });
                         }
                         G_LastChromeCastInfo = data;
                     },
             error: function(jqXHR, textStatus, errorThrown)
             {
                 // On error, log the error to console
                 // console.error(`Error: ${textStatus}, ${errorThrown}`);
                 if (ccReqNum % 2)
                    $('#ccast_uuid-button .ui-selectmenu-text').css ("color", "red");
                 else
                    $('#ccast_uuid-button .ui-selectmenu-text').css ("color", "");

             }
           });
    return false;
}

});

// #######################################################################################################

function loadPlayList (thisObj, name)
{
    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                 "action" : "playlist_list",
                 "name"   : name
             },
             dataType: "json",
             success: function(data)
             {
                 //console.log (data);
                 //console.log (JSON.stringify(data, null, 4));
                 let refID    = G_PlayListRefs[name];
                 let qbTable  = `<div>`;

                 for (const [key, value] of Object.entries(data))
                 {
                     queue = data[key];
                     qbTable += `
<table class="inlinePlaylistBrowserControls" style="width:100%;height:auto">
<tr>
    <td style="white-space:nowrap">
        <span style="padding-right: 10px;">
            <i class="inlinePlayListControls fa-solid fa-circle-play" style="padding-left: 10px;font-size: x-large;text-align:center;vertical-align: middle;" title="Playlist to Queue" onclick="$('#tabQueueBrowserSelect').click(); queuePlayPlaylist ($('#ccast_uuid').val(), $('#playlistBrowser .ui-accordion-content-active select').val(), $('#playlistBrowser .ui-accordion-header-active').attr('name')); "><br><font style="display:none" class="controlsIconFont showHelpText">Playlist to Queue</font></i>
        </span>
        <span>
            <select class="inlinePlayMode" name="PlayMode">
                <option value="play_playlist_replace">Replace</opion>
                <option value="play_playlist_append">Append</opion>
            </select>
        </span>
    </td>

    <td style="width:100%; text-align:right">
        <span style="padding-right: 10px;">
            <i class="inlinePlayListControls fa-solid fa-user-pen" style="text-align:center;" title="Rename Playlist" onclick="RenamePlayList(this, $('#playlistBrowser .ui-accordion-header-active').attr('name'))"><br><font style="display:none" class=" showHelpText controlsIconFont">Rename Playlist</font></i>
        </span>

        <span style="padding-right: 10px;">
            <i class="inlinePlayListControls fa-solid fa-right-left" style="text-align:center;" title="Invert Selection" onclick="InvertPlayListSelection ()"><br><font style="display:none" class="showHelpText controlsIconFont">Invert Selection</font></i>
        </span>

        <span style="padding-right: 10px;">
            <i class="inlinePlayListControls fa-solid fa-broom" style="text-align:center;" title="Clear Selection" onclick="ClearPlayListSelection ()"><br><font style="display:none" class="showHelpText controlsIconFont">Clear Selection</font></i>
        </span>

        <span style="padding-right: 10px;">
            <i class="inlinePlayListControls fa-solid fa-square-minus" style="text-align:center;" title="Delete Selection" onclick="DeletePlayListItems ()"><br><font style="display:none" class="showHelpText controlsIconFont">Delete Selection</font></i>
        </span>
        <span style="padding-right: 10px;">
            <i class="inlinePlayListControls fa-solid fa-trash-can" style="text-align:center;" title="Delete Playlist" onclick="confirm ('Delete Playlist?') ? DeletePlayList($('#playlistBrowser .ui-accordion-header-active').attr('name')) : false;"><br><font style="display:none" class="showHelpText controlsIconFont">Delete Playlist</font></i>
        </span>
    </td>
</tr>

</table>`;

                     qbTable += `
<table id="${refID}_tab" style="width:100%" border=0 class="TableSelection SongListFormat">
<thead>
    <tr><th></th><th>Song Title(s) : ${queue.length}</th><th>Album Name</th><th>Artist</th></tr>
</thead>`;
                     // console.log(key, value);
                     for (let idx=0; idx < queue.length; idx++)
                     {
                        qbTable += `
<tr class="dataRow selectItemHand" rowid="${queue[idx].seq}">
    <td><img onclick="ViewLargeArt(this);" class="albumArtURLSml"  content_type="${queue[idx].metadata["content_type"]}" src="${queue[idx].metadata["album_art_url"] ? queue[idx].metadata["album_art_url"] : getDefaultCoverArt(queue[idx].metadata["content_type"]) }" style="height: 32px;"></td>
    <td>${queue[idx].metadata["title"]}</td>
    <td>${queue[idx].metadata["albumName"]}</td>
    <td>${queue[idx].metadata["artist"]}</td>
    <td onclick="chromeCastBasicAction($('#ccast_uuid').val(), 'play_playlist_item_at_index', [ ${queue[idx].seq} ]);"><i class="inlinePlayListControls fa-solid fa-circle-play" style="text-align:center;" title="Play Item" onclick=""></i></td>
</tr>`;
                     }
                 }
                 qbTable += "</table></div>";

                 // render playlist table and controls.
                 $('#' + refID).html(qbTable);
                 showHideIconInfo();
                 $('.inlinePlayMode').selectmenu({ 'width' : '100px', 'vertical-align': 'sub'});
                 $('.inlinePlayMode').on('selectmenuchange', function() {
                     $(".inlinePlayMode").trigger("change");
                 });

                 let l = new TableSelection(`#${refID}_tab`, 1);
                 $('#' + refID).attr('playlistloaded', 'true');
             },
             error: function(jqXHR, textStatus, errorThrown)
             {
                 // On error, log the error to console
                 console.error(`Error: ${textStatus}, ${errorThrown}`);
             }
           });
}

function queuePlayPlaylist (ccast_uuid, playlistAction, playlistName)
{
    // check if there are selected items in the playlist, if so then only play/place those items into the Queue Browser
    let refID = G_PlayListRefs[playlistName];
    let allItems = $(`#${refID}_tab .dataRow`);
    let songRowIDs = [];
    for (let idx = 0; idx < allItems.length; idx++)
    {
        if ($(allItems[idx]).hasClass ('selected'))
            songRowIDs.push ($(allItems[idx]).attr('rowid'));
    }
    if (songRowIDs.length > 0)
    {
        if (playlistAction == 'play_playlist_replace')
            chromeCastBasicAction (ccast_uuid, 'play_playlist_replace_item_at_index', songRowIDs);
        else
            chromeCastBasicAction (ccast_uuid, 'play_playlist_append_item_at_index', songRowIDs);
    }
    else
        chromeCastBasicAction(ccast_uuid, playlistAction, playlistName); // If no items selected, then play/queue the whole play list
}



function showConfigEditor ()
{
    // Create and open the dialog with an iframe
    $("#configEditorDialog").html('<iframe src="configeditor.py" width="100%" height="100%" frameborder="0"></iframe>').dialog({
        modal: true,
        width: "80%",
        height: $(window).height() * 0.8,
        position: {
            my: "center top",
            at: "center top+10%",
            of: window
        },
        open: function ()
        {
            // Make sure the iframe fills the dialog
            $(this).css("overflow", "hidden");
            $(this).find("iframe").css({
            width: "100%",
            height: "100%",
            border: "0"
        });
      }
    });
}

function chromeCastPlay (file, ccast_uuid, type, queueDirectory=false, forcePlay=false)
{
    if (G_LastChromeCastInfo && (G_LastChromeCastInfo.playback_state.toLowerCase() == 'playing') && (file == ''))
    {
        chromeCastBasicAction (ccast_uuid, 'pause');
        return;
    }
    else if (G_LastChromeCastInfo && (file == ''))
    {
        chromeCastBasicAction (ccast_uuid, 'play');
        return;
    }

    // summit requested song to current play queue (Queue Browser)
    $.ajax ({url: 'castfile.py',
             type: "POST",
             data : {
                "ccast_uuid":      ccast_uuid,
                "type" :           type,
                "directory_load" : queueDirectory,
                "force_cast":      forcePlay,
                "location" :       file
             },
             success: function(result)
             {
                 $('#tabQueueBrowserSelect').click();
                 console.log(result);
                 if (! queueDirectory)
                 {
                     $.toast({
                         heading: 'Success',
                         text: `Song submitted to Chrome Cast Device`,
                         icon: 'success'
                     });
                 }
                 else
                 {
                     $.toast({
                         heading: 'Success',
                         text: `Songs submitted to Queue Browser`,
                         icon: 'success'
                     });
                 }
             }
           });
    return false;
}

function RenamePlayList(thisObj, playlistName)
{
    let renameHTML = `<input type="text" placeholder="Enter new playlist name" id="renamedPlayListName"  value="${playlistName}" style="color:black"  onclick="this.select()">`;
    $('#renamePlaylistDialog').remove();
    let d = $('<div id="renamePlaylistDialog" />').html(renameHTML).dialog
    ({
        height:'auto',
        width:'auto',
        modal:true,
        show: {
            effect: "fade",
            duration: 350
        },
        hide: {
            effect: "fade",
            duration: 350
        },
        position: {
            of: $('#playlistBrowser .ui-accordion-header-active'),
            my: "left top",
            at: "left top",
        },
        close:    function ()
        {
            $(this).dialog("close");
            action = "";
        },
        open: function (event, ui) {
            $(this).css('overflow', 'hidden');
            $(this).parent().addClass ("custom-no-titlebar");
        },
        buttons : [{   text: "Rename",
                       click: function ()
                       {
                            let newname = $('#renamedPlayListName').val().trim();
                            $.ajax ({url: 'playlistcontroller.py',
                                         type: "POST",
                                         data : {
                                            "action":         "rename_playlist",
                                            "name":           playlistName,
                                            "newname":        newname
                                         },
                                         success: function(result)
                                         {
                                             if (result == 'ok')
                                             {
                                                  AccordianRemovePlayList (playlistName);
                                                  AddPlayList(newname);
                                                  loadPlayList ($('#playlistBrowser'), newname);
                                                  $.toast({
                                                      heading: 'Success',
                                                      text: `Play List renamed from '${playlistName}' to '${newname}'`,
                                                      icon: 'success'
                                                  });
                                             }
                                             else
                                             {
                                                  $.toast({
                                                      heading: 'Error',
                                                      text: `Failed to rename '${playlistName}' because ${result}'`,
                                                      icon: 'error'
                                                  });
                                             }
                                             console.log(result);
                                         }
                                       });

                            $(this).dialog("close");
                       },
                       class:"",
                       style:"background-color:#0078a9;color:white"
                   },
                   {   text: "Cancel",
                       click: function ()
                       {
                            $(this).dialog("close");
                       },
                       class:"",
                       style:"background-color:red;color:white"
                   }]
    });
}
function AddLocationToPlayList (playlistName, location, type, isDirectory)
{
    $.ajax ({url: 'playlistcontroller.py',
         type: "POST",
         data : {
            "action":         "add_playlist_items",
            "name":           playlistName,
            "type":           type,
            "directory_load": isDirectory,
            "location":       location
         },
         success: function(result)
         {
             // Reload the current playlist!
             loadPlayList ($('#playlistBrowser'), playlistName);

             $.toast({
                 heading: 'Success',
                 text: `Loading songs into Play List '${playlistName}'`,
                 icon: 'success'
             });

             $('#tabPlaylistBrowserSelect').click();
             if ($('#playlistBrowser .ui-accordion-header-active').attr('name') != playlistName)
             {
                 let hashID = Sha256.hash(playlistName);
                 $(`#hdr_${hashID}`).click();
             }
             console.log(result);
         }
       });
}
function FileListAddToPlayList (thisObj, playlistName)
{
    let idx            = $(thisObj).attr('idx');
    if (idx >= 0)
    {
        let queueDirectory = $(thisObj).attr('isDirectory');
        AddLocationToPlayList (playlistName, G_CurrentFileList[idx].full_path, $('#share_locs').find('option:selected').attr('type'), queueDirectory)
    }
    else // if -1 then selected from top of filelist, so add only the visible items in the list that may be filtered by the filter input field.
    {
        $('#fileList tbody tr:visible .addToPlayList').each(function (index)
        {
            let idx            = $(this).attr('idx');
            let queueDirectory = $(this).attr('isDirectory');
            AddLocationToPlayList (playlistName, G_CurrentFileList[idx].full_path, $('#share_locs').find('option:selected').attr('type'), queueDirectory)
        });
    }
}
function SearchListAddToPlayList (thisObj, playlistName)
{
    let idx            = $(thisObj).attr('idx');
    if (idx >= 0)
    {
        let queueDirectory = $(thisObj).attr('isDirectory');
        AddLocationToPlayList (playlistName, G_CurrentSearchList[idx].location, G_CurrentSearchList[idx].type, queueDirectory)
    }
    else
    {
        $('#searchList_tab tbody tr:visible .addToPlayList').each(function (index)
        {
            let idx            = $(this).attr('idx');
            let queueDirectory = $(this).attr('isDirectory');
            AddLocationToPlayList (playlistName, G_CurrentSearchList[idx].location, G_CurrentSearchList[idx].type, queueDirectory)
        });
    }
}

var G_FavouritesName = 'Favourites';
function FavouriteAddRemove (ccinfo=null)
{
    if ((! ccinfo) && G_LastChromeCastInfo)
        ccinfo = G_LastChromeCastInfo;

    if (! ccinfo)
        return;

    // test if favourite playlist has been created?
    if (! (G_FavouritesName in G_PlayListRefs))
    {
        CreatePlayList(G_FavouritesName);
        setTimeout(FavouriteAddRemove, 1000);
        return;
    }

    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                'action'   : 'exists_playlist_item',
                'name'     : G_FavouritesName,
                'location' : ccinfo.slinger_current_media.location,
                'type'     : ccinfo.slinger_current_media.type
             },
             dataType: 'json',
             success: function(result)
             {
                 if (result.exists)
                 {
                     DeletePlayListRowIDs (G_FavouritesName, [result.rowid])
                 }
                 else
                 {
                     AddLocationToPlayList (G_FavouritesName, ccinfo.slinger_current_media.location, ccinfo.slinger_current_media.type, false);
                 }
                 setTimeout(ShowIsFavourite, 1000, ccinfo);
             }
           });
}

function ShowIsFavourite (ccinfo=null)
{
    if ((! ccinfo) && G_LastChromeCastInfo)
        ccinfo = G_LastChromeCastInfo;

    if (! ccinfo)
        return;

    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                'action'   : 'exists_playlist_item',
                'name'     : G_FavouritesName,
                'location' : ccinfo.slinger_current_media.location,
                'type'     : ccinfo.slinger_current_media.type
             },
             dataType: 'json',
             success: function(result)
             {
                 if (result.exists)
                 {
                     $('#plyrCntrlAddToFavs').addClass ('SongIsFavourite');
                 }
                 else
                 {
                    $('#plyrCntrlAddToFavs').removeClass ('SongIsFavourite');
                 }
             }
           });
}

function GotoFolderLocation (fldrLocation)
{
    $('#tabFileBrowserSelect').click();
    let type = $('#share_locs').find('option:selected').attr('type');
    let base = $('#share_locs').val();
    $('#share_locs option').each(function (index)
    {
        if (fldrLocation.startsWith($(this).val()))
        {
            type = $(this).attr('type')
            base = $(this).val();

            console.log (`type:${type} Goto:${base}`);
            $('#share_locs').val($(this).val())
            $('#share_locs').selectmenu("refresh");
        }
    });
    loadFileList (fldrLocation, type, base);
    return false;
}

function ArtworkGotoFolder(location, type)
{
    let fileSep = G_OS_FileSeparator;
    if (type == 'smb')
        fileSep = G_SMB_FileSeparator; // '\\'
    return GotoFolderLocation(location.split(fileSep).slice(0,-1).join(fileSep));
}

function SearchGotoFolder(idx)
{
    let obj = G_CurrentSearchList[idx]
    let fileSep = G_OS_FileSeparator;
    if (obj.type == 'smb')
        fileSep = G_SMB_FileSeparator; // '\\'
    return GotoFolderLocation(obj.location.split(fileSep).slice(0,-1).join(fileSep));
}

function ImportSpotifyPlayList (spotifyURL, thisObj=null)
{
    if (thisObj)
        $(thisObj).addClass("ui-state-disabled");

     $.toast({
         heading: 'Importing Spotify Playlist',
         text: `please wait...`,
         icon: 'info'
     });

    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data : {
                  "action" : "import_spotify_playlist",
                  "spotifyPlaylistUrl" : spotifyURL
             },
             success: function(result)
             {
                 console.log (`ImportSpotifyPlayList success : ${ result}`);
                 // Reload the playlists!
                 LoadPlaylistNames ();
                 if (thisObj)
                     $(thisObj).removeClass("ui-state-disabled");

                 result = result.replaceAll('FAILED MATCH', '<span style="color:red">FAILED MATCH</span>');
                 list = result.split("\n")
                 $.toast({
                     heading: list[0],
                     text: list.splice(1),
                     icon: 'info',
                     hideAfter: 60 * 1000,
                     beforeShow: function ()
                                 {
                                     $('.jq-toast-single').css('width',      '600px');
                                     $('.jq-toast-single').css('height',     '400px');
                                     $('.jq-toast-single').css('overflow-y', 'scroll');
                                 }
                 });
             },
             error: function(jqXHR, status, errorThrown)
             {
                 console.log (`ImportSpotifyPlayList error : status:${status} ${ errorThrown}`);
                 if (thisObj)
                     $(thisObj).removeClass("ui-state-disabled");

                 $.toast({
                     heading: 'error',
                     text: `Failed importing Spotify Playlist: ${errorThrown}`,
                     icon: 'error',
                     hideAfter: 5000
                 });
             }
           });
}

function CreateSearchListPlayList(name, thisObj=null)
{
    name = name.replace("'", "").replace('"', '').trim();
    if (name == '')
        return;

    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                  "action" : "create_playlist",
                  "name"   : name
             },
             success: function(result)
             {
                 AddPlayList(name);

                 // Reload the current playlist!
                 loadPlayList ($('#playlistBrowser'), name);
                 console.log(result);
                 Build_PlaylistContextMenu ();

                 if (thisObj)
                 {
                    SearchListAddToPlayList (thisObj, name)
                 }
             }
           });
}

function QueueListToPlaylist (newPlayListName)
{
    newPlayListName = newPlayListName.trim();
    ccast_uuid = $('#ccast_uuid').val();
    action = 'save_queue_to_playlist';
    $.ajax ({url: `castcontroller.py` ,
             type: "POST",
             data : {
                 "ccast_uuid": ccast_uuid,
                 "action":     action,
                 "val1":       newPlayListName
             },
             success: function(result)
             {
                 AddPlayList(newPlayListName);
                 loadPlayList ($('#playlistBrowser'), newPlayListName);

                 $.toast({
                     heading: 'Success',
                     text: `Play List created as '${newPlayListName}'`,
                     icon: 'success'
                 });
                 console.log(result);
             }
           });
}

function OnClick_FileList (thisObj, queueDirectory=false, forcePlay=false)
{
    let idx = $(thisObj).attr('idx');

    if (G_CurrentFileList == null)
        return false;
    if (idx > G_CurrentFileList.length || idx < 0)
        return false;

    if ((queueDirectory == false) && (G_CurrentFileList[idx].isDirectory))
    {
        G_LastNavigatedPath.push($(thisObj).attr('filenameHash'));
        // console.log (`G_LastNavigatedPath Encoding on directory : ${G_CurrentFileList[idx].full_path} as ${$(thisObj).attr('filenameHash')}`)
        loadFileList (G_CurrentFileList[idx].full_path, $('#share_locs').find('option:selected').attr('type'), $('#share_locs').val());
    }
    else
    {
        chromeCastPlay(G_CurrentFileList[idx].full_path, $('#ccast_uuid').val(), $('#share_locs').find('option:selected').attr('type'), queueDirectory, forcePlay)
    }
}

function chromeCastShuffle (ccast_uuid)
{
    let val1   = 'true';
    if (G_LastChromeCastInfo && G_LastChromeCastInfo.slinger_shuffle)
        val1 = 'false';
    chromeCastBasicAction (ccast_uuid, 'shuffle', val1);
}

function chromeCastMetaDataShuffle (ccast_uuid, active=null)
{
    let val1                = 'true';
    let currentFileListPath = decodeURIComponent($('#fileListCurrentLocation').attr('filelocationparent')).toLocaleLowerCase();

    if (G_LastChromeCastInfo
        && G_LastChromeCastInfo.slinger_metadata_shuffle
        && (G_LastChromeCastInfo.slinger_metadata_shuffle_location.toLocaleLowerCase() == currentFileListPath)
       )
    {
        val1 = 'false';
    }

    // override the active state
    if (active != null)
    {
        val1 = (active == true) + "";
    }

    chromeCastBasicAction (ccast_uuid, 'metadata_shuffle', val1, $('#shuffleMetaFileType').val(), currentFileListPath );
}

function chromeCastMute (ccast_uuid)
{
    let val1   = 'true';
    if (G_LastChromeCastInfo && G_LastChromeCastInfo.volume_muted)
        val1 = 'false';
    chromeCastBasicAction (ccast_uuid, 'mute', val1);
}

function chromeCastBasicAction (ccast_uuid, action, val1='', val2='', val3='' )
{
    $.ajax ({url: `castcontroller.py`,
             type: "POST",
             data : {
                "ccast_uuid" : ccast_uuid,
                "action"     : action,
                "val1"       : val1,
                "val2"       : val2,
                "val3"       : val3
             },
             success: function(result)
             {
                console.log(result);
             }
           });
    return false;
}

function OnClick_FileListParent (thisObj)
{
    let type = $('#share_locs').find('option:selected').attr('type')
    let fileSep = G_OS_FileSeparator;
    if (type == 'smb')
        fileSep = G_SMB_FileSeparator; // '\\'

    let p  =  decodeURI($(thisObj).attr('filelocationParent'));
    let fp = p.split (fileSep);

    // remove the last item from the path
    let pl = fp.length-1;
    // if the last char is a '\', then decrement an extra field from the split array
    if (p[p.length-1] == fileSep)
    {
        pl--;
    }

    let parentPath = fp.slice(0,pl).join(fileSep);
    loadFileList (parentPath, $('#share_locs').find('option:selected').attr('type'), $('#share_locs').val());
}

function OnChange_FileLocation(thisObj)
{
    // console.log ('G_LastNavigatedPath cleared')
    G_LastNavigatedPath.clear();
    loadFileList ($('#share_locs').val(), $('#share_locs').find('option:selected').attr('type'), $('#share_locs').val());
}

function LoadFolderArtAsImage (filelocation, type, htmlID, custClass="", custStyle="")
{
     $.ajax ({url: `queryfileloc.py`,
              type: "POST",
              data: {
                'type' :  type,
                'location': filelocation,
                'get_folder_art' : 'y'
              },
              dataType: "json",
              success: function(data)
              {
                  // console.log('art = ' + data["art_url"]);
                  $(htmlID).html(`<img class="selectItemHand ${custClass}" style="${custStyle}" onclick="ViewLargeArt(this);event.stopPropagation();" src="${data['art_url'] ? data['art_url'] : getDefaultCoverArt() }">`)
              },
              error: function(jqXHR, textStatus, errorThrown)
              {
                  // On error, log the error to console
                  console.error(`Error: ${textStatus}, ${errorThrown}`);
              }
           });
}

function OnClick_SeekSong (thisObj)
{
    ccast_uuid = $('#ccast_uuid').val();
    if (isLocalPlayer(ccast_uuid))
    {
        let audio = $("#LocalAudioPlayerDevice");
        let video = $("#LocalVideoPlayerDevice");
        audio[0].currentTime = $(thisObj).val();
        video[0].currentTime = $(thisObj).val();
    }
    else
        chromeCastBasicAction($('#ccast_uuid').val(), 'seek', $(thisObj).val())

    return false;
}

function OnClick_RestartSong ()
{
    ccast_uuid = $('#ccast_uuid').val();
    if (isLocalPlayer(ccast_uuid))
    {
        let audio = $("#LocalAudioPlayerDevice");
        let video = $("#LocalVideoPlayerDevice");
        audio[0].currentTime = 0;
        video[0].currentTime = 0;
    }
    else
        chromeCastBasicAction(ccast_uuid, 'seek', 0);

    return false;
}

function OnClick_Stop ()
{
    chromeCastBasicAction (ccast_uuid, 'stop', 0);

    ccast_uuid = $('#ccast_uuid').val();
    if (isLocalPlayer(ccast_uuid))
    {
        let audio = $("#LocalAudioPlayerDevice");
        let video = $("#LocalVideoPlayerDevice");
        audio[0].pause();
        video[0].pause();

        setTimeout(function ()
        {
            let audio = $("#LocalAudioPlayerDevice");
            let video = $("#LocalVideoPlayerDevice");
            audio[0].pause();
            video[0].pause();
            audio[0].currentTime = 0;
            video[0].currentTime = 0;
            G_LastChromeCastInfo = null; // reset/refresh player control panel playing state
            $("#video-player-container").hide(500, function() {
                resizeFilePanels();
            });
        }, 500);
    }

    return false;
}


var G_RateLimitFileListFolderArtOp = 0;
function LoadFileListFolderArtAsImage (filelocation, type, idx, htmlID)
{
     // check if user has navigated away from current directory listing...
     try {
        if (filelocation != G_CurrentFileList[idx].full_path)
            return;
     } catch { return; }

     if (G_RateLimitFileListFolderArtOp > 10)
     {
        // delay random time and retry request, recursively so to speak.
        setTimeout(LoadFileListFolderArtAsImage, Math.floor(Math.random() * 900 + 100), filelocation, type, idx, htmlID)
        return;
     }
     G_RateLimitFileListFolderArtOp++;
     $.ajax ({url: `queryfileloc.py`,
              type: "POST",
              data: {
                'type' :  type,
                'location': filelocation,
                'get_folder_art' : 'y'
              },
              dataType: "json",
              success: function(data)
              {
                  G_RateLimitFileListFolderArtOp--;
                  try {
                     if (filelocation != G_CurrentFileList[idx].full_path)
                         return;
                  } catch { return; }

                  // console.log('art = ' + data["art_url"]);
                  //debugger;
                  // Validate if this is a full url, if not, go with the default folder image/icon
                  try
                  {
                      let u = new URL (data['art_url']);
                      $(htmlID).html(`<img class="selectItemHand albumArtURLSml" style="height: 24px;" onclick="ViewLargeArt(this);event.stopPropagation();" src="${data['art_url'] ? data['art_url'] : getDefaultCoverArt() }">`)
                  } catch {}
              },
              error: function(jqXHR, textStatus, errorThrown)
              {
                  G_RateLimitFileListFolderArtOp--;
                  // On error, log the error to console
                  console.error(`Error: ${textStatus}, ${errorThrown}`);
                  if (RateLimitLoadFileListFolderArt > 0)
                    RateLimitLoadFileListFolderArt--;
              }
           });
}


class Stack
{
    constructor() {
        this.items = [];
    }

    // Add a number to the stack
    push(number) {
        this.items.push(number);
    }

    // Take the top number off the stack
    pop() {
        if (this.items.length === 0)
            return "Oops, the stack is empty!";
        return this.items.pop();
    }

    // See what the top number is
    peek() {
        return this.items[this.items.length - 1];
    }

    // Check if the stack is empty
    isEmpty() {
        return this.items.length === 0;
    }

    clear() {
        this.items = [];
    }

    // Find out how many items are in the stack
    size() {
        return this.items.length;
    }
}

var G_CurrentFileList = null;
var G_LastNavigatedPath = new Stack();
async function loadFileList (filelocation, type, basePath)
{
    $.ajax ({url: `queryfileloc.py`,
             type: "post",
             data: {
                'type'       : type,
                'location'   : filelocation,
                'filter_type':'audio_only'
             },
             dataType: "json",
             success: function(data)
             {
                 G_CurrentFileList = data;
                 let parentDisabled = 'ui-state-disabled';
                 if (filelocation != basePath)
                     parentDisabled = '';

                 // fileBrowser
                 let flTable = `\n`;
                 flTable += `
<table id="fileListCurrentLocation" border=0 class="selectItemHand rcorners3" style="width:100%;" onclick="OnClick_FileListParent(this)" filelocationParent="${encodeURI(filelocation)}"><tr>
<td style="padding-right: 5px;">
    <i id="fileListParent" class="${parentDisabled} fa-solid fa-angles-left selectItemHand"></i>
    <br><font style="display:none; white-space:nowrap" class="showHelpText controlsIconFont">Parent Folder</font>
</td>
<td style="width:100%;">
    <div id="currentBrowserPath"  colspan='100%'>${filelocation.replace (RegExp("^" + escapeRegExp (basePath)), '')}</div>
</td></tr>
</table>
<table id="fileList" style="width:100%">
<thead>
<tr style="white-space:nowrap" class="SongListFormat">
    <th style="width:100%;cursor: pointer;" class="" title="Click to Filter">
        <span>Filter Title(s) : ${data.length}</span>
        <span style="padding-left:10px;text-decoration: none !important;">
            <input type="text" size=20 id="filenameFilter">
         </span>
        <span style="padding-left:20px;text-decoration: none !important;">
            <button onclick="$('#fileList tbody tr:visible .addToQueueList').click()" idx="-1" class="iconStyle24 selectItemHand" title="Add to Play Queue">
                <i class="fa-solid fa-list"></i>
            </button>
        </span>
        <span style="padding-left:20px;text-decoration: none !important;">
            <button class="iconStyle24 selectItemHand hasContextMenu" title="Add to Play List" isdirectory="false" idx="-1">
                <i class="fa-solid fa-table-list"></i>
            </button>
        </span>
    </th>
    <th>Queue Item</th>
</tr>
</thead>
`;
                 // Add into which list, queue, or playlist
                 let activeRightTab = $($("#tabsRight").find(".ui-tabs-panel")[$("#tabsRight").tabs("option", "active")]).attr('id');

                 let dirImg     = `<i class="fa-regular fa-folder"></i>`
                 let audioImg   = `<i class="fa-solid fa-music"></i>`
                 let videoImg   = `<i class="fa-solid fa-video"></i>`
                 let unknownImg = `<i class="fa-solid fa-circle-question"></i>`

                 for (idx = 0; idx < data.length; idx++)
                 {
                     let icon = dirImg;
                     if (! data[idx].isDirectory)
                     {
                         if (isVideo (data[idx].content_type))
                             icon = videoImg;
                         else if (isAudio (data[idx].content_type))
                             icon = audioImg;
                         else
                             icon = unknownImg;
                     }
                     flTable += `
<tr class="selectItemHand FileList-DataRow">
    <td onclick="OnClick_FileList(this, false, !${data[idx].isDirectory})" idx="${idx}" isDirectory="${data[idx].isDirectory}" filenameHash="${Sha256.hash(G_CurrentFileList[idx].full_path)}" class="FileList-Row"><span class="FileList-FileType" idx="${idx}">${ icon }</span>&nbsp;<span class="FileList-FileName" isDirectory="${data[idx].isDirectory}">${data[idx].filename}</span></td>

    <!-- Queue / Playlist controls -->
    <td style="white-space:nowrap">
        <table class="fileListQueueControls" border=0>
        <tr>
            <td style="width:50%; padding: 0px !important;text-align: center;" class="iconStyle24 selectItemHand addToQueueList" onclick="OnClick_FileList(this, ${data[idx].isDirectory}, false)" idx="${idx}" Title="Add to Play Queue">
                <i class="fa-solid fa-list"></i>
                <span  style="display:none" class=" fileListQueueControlsTxt showHelpText">+Queue&nbsp;</span>
            </td>
            <td style="width:5px"></td>
            <td style="width:50%; padding: 0px !important;text-align: center;" class="iconStyle24 addToPlayList selectItemHand hasContextMenu" Title="Add to Play List" isDirectory="${data[idx].isDirectory}" idx="${idx}">
                <i class="fa-solid fa-table-list"></i>
                <span  style="display:none" class=" fileListQueueControlsTxt showHelpText">+Playlist&nbsp;</span>
            </td>
        </tr>
        </table>
    </td>
</tr>`;
                 }
                 flTable += "</table>";
                 $('#fileBrowser').html(flTable);

                 if (! G_LastNavigatedPath.isEmpty())
                 {
                     lastNavigatedPath = G_LastNavigatedPath.peek();
                     // wait some time after this thread has existed and html has finished rendering before attempting to scroll to a previous position
                     (async () =>
                     {
                          await setTimeout(100);
                          try
                          {
                             // scroll to the previous directory if browsing out of an ending folder
                             // console.log (`G_LastNavigatedPath Trying to locate ${lastNavigatedPath} for ${filelocation}`);
                             let objFnd = $(`#fileList .FileList-DataRow td[filenamehash="${lastNavigatedPath}"]`)
                             if ($(objFnd).length > 0)
                             {
                                 // console.log (`G_LastNavigatedPath Located ${lastNavigatedPath} for ${filelocation}`);
                                 $(objFnd).get(0).scrollIntoView({block: "center", inline: "nearest"});
                                 // if successful, then remove item from navigation queue
                                 G_LastNavigatedPath.pop();
                                 $(objFnd).parent().addClass ('selected');
                             }
                             else
                             {
                                 $(`#fileList`).get(0).scrollIntoView({block: "top", inline: "nearest"});
                             }
                         }
                         catch {  }
                     })();
                 }

                 resizeFilePanels();
                 showHideIconInfo();
                 $("#filenameFilter").keyup(function ()
                 {
                     var rows = $("#fileList tbody").find(".FileList-DataRow").hide();
                     if (this.value.length)
                     {
                         var data = this.value.split(" ");
                         $.each(data, function (i, v)
                         {
                             let vl = v.toLowerCase();
                             for (idx = 0; idx < rows.length; idx++)
                             {
                                matchData = $(rows[idx]).find('.FileList-FileName');
                                for (midx = 0; midx < matchData.length; midx++)
                                {
                                    if ($(matchData[midx]).text().toLowerCase().indexOf(vl) > -1)
                                    {
                                        $(rows[idx]).show();
                                        break;
                                    }
                                }
                             }
                         });
                     }
                     else
                        rows.show();
                 });

                 Build_PlaylistContextMenu ();

                 // Load current folder art if it exists...
                 LoadFolderArtAsImage (filelocation, type, '#browserArt');

                 // load sub-dir folder art if it exists....
                 if (G_LoadFileFolderArt)
                 {
                     G_RateLimitFileListFolderArtOp = 0;
                     $('#fileList tbody .FileList-Row[isDirectory="true"]').each (function ()
                     {
                         (async () =>
                         {
                            let idx = $(this).attr('idx');

                            LoadFileListFolderArtAsImage (G_CurrentFileList[idx].full_path,
                                                          $('#share_locs').find('option:selected').attr('type'),
                                                          idx, `#fileList tbody .FileList-FileType[idx="${idx}"]`);
                         })();
                     });

                 }
             }
            });
    return false;
}

$( document ).ready(function()
{
    $('#share_locs').selectmenu();
    $('#share_locs').on('selectmenuchange', function() {
        $("#share_locs").trigger("change");
    });


    $('#tabsLeft').tabs();
    $('#tabsRight').tabs();
    $("#tabsRight").on("tabsactivate", function( event, ui ) {
        loadFileList ($($('#currentBrowserPath')).text(), $('#share_locs').find('option:selected').attr('type'), $('#share_locs').val());
        resizeFilePanels();
        //console.log("here " + $(this).accordion('option', 'active'));
        //console.log($(this).accordion( "widget" )[0])
        //console.log(ui.newHeader.text());
    });

    $("#tabsLeft").on("tabsactivate", function( event, ui ) {
        resizeFilePanels();
        //console.log("here " + $(this).accordion('option', 'active'));
        //console.log($(this).accordion( "widget" )[0])
        //console.log(ui.newHeader.text());
    });

    loadFileList ($('#share_locs').val(), $('#share_locs').find('option:selected').attr('type'), $('#share_locs').val());
});

function AddPlayList(name)
{
    let hashID = Sha256.hash(name);
    let html = `<h3 name='${name}' id='hdr_${hashID}'>${name}</h3><div id='${hashID}' name='${name}'></div>\n`;
    G_PlayListRefs[name] = hashID;
    $('#playlistBrowser').append(html);
    $('#playlistBrowser').accordion("refresh");
    $(`#hdr_${hashID}`).click();

    Build_PlaylistContextMenu ();
}

function CreatePlayList(name, fileListThisObj=null)
{
    name = name.replace("'", "").replace('"', '').trim();
    if (name == '')
        return;

    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                "action" : "create_playlist",
                "name"   : name
             },
             success: function(result)
             {
                 AddPlayList(name);

                 // Reload the current playlist!
                 loadPlayList ($('#playlistBrowser'), name);
                 console.log(result);
                 Build_PlaylistContextMenu ();

                 if (fileListThisObj)
                    FileListAddToPlayList (fileListThisObj, name);
             }
           });
}

function AccordianRemovePlayList (name)
{
    $(`#hdr_${G_PlayListRefs[name]}`).remove();
    $(`#${G_PlayListRefs[name]}`).remove();
    $('#playlistBrowser').accordion("refresh");
    delete G_PlayListRefs[name];
}

function DeletePlayList (name)
{
    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                "action" : "delete_playlist",
                "name"   : name
             },
             success: function(result)
             {
                 AccordianRemovePlayList (name);
                 Build_PlaylistContextMenu ();
                 console.log(result);
             }
           });
}

function ClearPlayListSelection ()
{
    let name  = $('#playlistBrowser .ui-accordion-header-active').attr('name');
    let refID = G_PlayListRefs[name];
    let allItems = $(`#${refID}_tab .dataRow`);
    for (let idx = 0; idx < allItems.length; idx++)
        $(allItems[idx]).removeClass ('selected');
}

function InvertPlayListSelection ()
{
    let name  = $('#playlistBrowser .ui-accordion-header-active').attr('name');
    let refID = G_PlayListRefs[name];
    let allItems = $(`#${refID}_tab .dataRow`);
    for (let idx = 0; idx < allItems.length; idx++)
    {
        if ($(allItems[idx]).hasClass ('selected'))
            $(allItems[idx]).removeClass ('selected');
        else
            $(allItems[idx]).addClass ('selected');
    }
}

function DeletePlayListRowIDs (name, rowIDS)
{
    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                "action" : "delete_playlist_items",
                "name"   : name,
                "rowid"  : rowIDS
             },
             success: function(result)
             {
                 // Reload the current playlist!
                 loadPlayList ($('#playlistBrowser'), $('#playlistBrowser .ui-accordion-header-active').attr('name'));
                 console.log(result);
                 Build_PlaylistContextMenu ();
             },
             error: function(jqXHR, textStatus, errorThrown)
             {
                 // On error, log the error to console
                 console.error(`Error: ${textStatus}, ${errorThrown}`);
             }
           });
}

function DeletePlayListItems()
{
    let name  = $('#playlistBrowser .ui-accordion-header-active').attr('name')
    let refID = G_PlayListRefs[name];
    let items = $(`#${refID}_tab .selected`);

    let rowIDS=[];
    for (let idx = 0; idx < items.length; idx++)
        rowIDS.push($(items[idx]).attr('rowid'));

    DeletePlayListRowIDs (name, rowIDS);
}

function LoadPlaylistNames ()
{
    $.ajax ({url: `playlistcontroller.py`,
             type: "POST",
             data: {
                  "action" : "get_playlist_names"
             },
             dataType: "json",
             success: function(data)
             {
                 $('#playlistBrowser').empty();

                 let loadFirst = true;
                 for (idx = 0; idx < data.length; idx++)
                 {
                     AddPlayList(data[idx]['name'])
                     if (loadFirst)
                        loadPlayList ($('#playlistBrowser'), data[idx]['name']);
                 }
                 Build_PlaylistContextMenu ();
             }
           });
}

function Build_PlaylistContextMenu ()
{
    // create a context menu dynamically for each filelist load
    $.contextMenu(
    {
        selector: '#fileList .hasContextMenu',
        trigger: 'left',
        className: 'contextMenu-title',
        build: function($trigger, e)
        {
            // Get current playlist list...
            let menuList = {};
            $('#playlistBrowser .ui-accordion-header').each(function()
            {
                menuList[$(this).attr('name')] = {'name':        $(this).attr('name'),
                                                  'playListObj': this,
                                                  'callback':    function(key, options)
                                                  {
                                                       console.log(options.items[key]['name']);
                                                       FileListAddToPlayList (options.$trigger[0], options.items[key]['name'])
                                                  }
                                                 };
                // console.log (`BuildPL ${$(this).attr('name')}`);
            });

            menuList['sep1'] = "---------";
            menuList['name'] = { name: "Enter New Play List Name",
                                 type: 'text',
                                 value: "",
                                 events:
                                 {
                                     keyup: function(e)
                                     {
                                         name = $(e.target).val().trim()
                                         if ((e.key === 'Enter' || e.keyCode === 13) && name != "")
                                         {
                                             // console.log ($(e.target).val());
                                             CreatePlayList (name, e.data.$trigger[0]);
                                             e.data.$menu.trigger('contextmenu:hide');
                                         }
                                     }
                                 },
                                 'callback': function(key, options)
                                 {
                                       console.log(options.items[key]['name']);
                                       //FileListAddToPlayList (options.$trigger[0], options.items[key]['name'])
                                 }
                               };
            return {
                items: menuList
            };
        }
    });

    // create a context menu dynamically for each search list load
    $.contextMenu(
    {
        selector: '#searchList .hasContextMenu',
        trigger: 'left',
        className: 'contextMenu-title',
        build: function($trigger, e)
        {
            // Get current playlist list...
            let menuList = {};
            $('#playlistBrowser .ui-accordion-header').each(function()
            {
                menuList[$(this).attr('name')] = {'name':        $(this).attr('name'),
                                                  'playListObj': this,
                                                  'callback':    function(key, options)
                                                  {
                                                       console.log(options.items[key]['name']);
                                                       SearchListAddToPlayList (options.$trigger[0], options.items[key]['name'])
                                                  }
                                                 };
            });

            menuList['sep1'] = "---------";
            menuList['name'] = { name: "Enter New Play List Name",
                                 type: 'text',
                                 value: "",
                                 events:
                                 {
                                     keyup: function(e)
                                     {
                                         name = $(e.target).val().trim()
                                         if ((e.key === 'Enter' || e.keyCode === 13) && name != "")
                                         {
                                             // console.log ($(e.target).val());
                                             CreateSearchListPlayList(name, e.data.$trigger[0]);
                                             e.data.$menu.trigger('contextmenu:hide');
                                         }
                                     }
                                 },
                                 'callback': function(key, options)
                                 {
                                       console.log(options.items[key]['name']);
                                       //FileListAddToPlayList (options.$trigger[0], options.items[key]['name'])
                                 }
                               };
            return {
                items: menuList
            };
        }
    });

    // create a context menu dynamically for current playing item
    $.contextMenu(
    {
        selector: '#playerControls .hasContextMenu',
        trigger: 'left',
        className: 'contextMenu-title',
        build: function($trigger, e)
        {
            // Get current playlist list...
            let menuList = {};
            $('#playlistBrowser .ui-accordion-header').each(function()
            {
                menuList[$(this).attr('name')] = {'name':        $(this).attr('name'),
                                                  'playListObj': this,
                                                  'callback':    function(key, options)
                                                  {
                                                      // function AddLocationToPlayList (playlistName, location, type, isDirectory)
                                                      if (G_LastChromeCastInfo.slinger_current_media.location != '' && G_LastChromeCastInfo.slinger_current_media.type != '')
                                                          AddLocationToPlayList (options.items[key]['name'], G_LastChromeCastInfo.slinger_current_media.location, G_LastChromeCastInfo.slinger_current_media.type, false);
                                                  }
                                                 };


            });

            menuList['sep1'] = "---------";
            menuList['name'] = { name: "Enter New Play List Name",
                                 type: 'text',
                                 value: "",
                                 events:
                                 {
                                     keyup: function(e)
                                     {
                                         name = $(e.target).val().trim()
                                         if ((e.key === 'Enter' || e.keyCode === 13) && name != "")
                                         {
                                             if (G_LastChromeCastInfo.slinger_current_media.location != '' && G_LastChromeCastInfo.slinger_current_media.type != '')
                                             {
                                                 CreatePlayList (name);


                                             }

                                             e.data.$menu.trigger('contextmenu:hide');
                                         }
                                     }
                                 },
                                 'callback': function(key, options)
                                 {
                                       console.log(options.items[key]['name']);
                                       //FileListAddToPlayList (options.$trigger[0], options.items[key]['name'])
                                 }
                               };
            return {
                items: menuList
            };
        }
    });
}

var G_CurrentSearchList = null;
function OnClick_SearchList (idx, forcePlay=false)
{
    if (G_CurrentSearchList == null)
        return false;
    if (idx > G_CurrentSearchList.length || idx < 0)
        return false;

    chromeCastPlay(G_CurrentSearchList[idx].location, $('#ccast_uuid').val(), G_CurrentSearchList[idx].type, false, forcePlay);
}

function SearchNowActive ()
{
     // console.log(results);
     $('#searchQuery').removeClass('ui-state-disabled');
     $('#searchBut').removeClass ('fa-circle-stop');
     $('#searchBut').addClass ('fa-angles-right');
     $('#searchBut').css('color', '');
     $('.search-running').css('display', 'none');
}

function SearchNowInActive ()
{
     $('#searchBut').removeClass ('fa-angles-right');
     $('#searchBut').addClass ('fa-circle-stop');
     $('#searchBut').addClass ('pulse');

     $('#searchBut').css('color', 'red');
     $('.search-running').css('display', '')
}

var G_SearchTimeoutID = null;
var G_SearchCnt = 0;
function SearchQueryInfo ()
{
    ccast_uuid = $('#ccast_uuid').val();

    $.ajax ({url: `executequery.py`,
             type: "POST",
             data: {
                  "action" : "status"
             },
             dataType: "json",
             success: function(data)
             {
                 // console.log (data);
                 G_SearchCnt++;
                 if (data['active'])
                 {
                    $('#searchResultsInfo').html("running")
                    let d = data.file_path.substring(0, 40)
                    if ((G_SearchCnt % 2) == 0)
                        d += '...';

                    $('#searchResultsInfo').html(d);

                    if ($('#searchBut').hasClass('fa-angles-right'))
                        SearchNowInActive ();
                    G_SearchTimeoutID = setTimeout(SearchQueryInfo, 1000);
                 }
                 else
                 {
                     $('#searchResultsInfo').html("")
                     if ($('#searchBut').hasClass('fa-circle-stop'))
                        SearchNowActive ();
                     G_SearchTimeoutID = setTimeout(SearchQueryInfo, 10000);
                 }
             },
             error: function(jqXHR, textStatus, errorThrown)
             {
                 // On error, log the error to console
                 console.error(`Error: ${textStatus}, ${errorThrown}`);
                 G_SearchTimeoutID = setTimeout(SearchQueryInfo, 10000);
             }
           });
}

// gather searching current status
$( document ).ready(function()
{
    setTimeout(SearchQueryInfo, 1000);
});

function runSearchQuery ()
{
     $('#searchQuery').addClass('ui-state-disabled');
     if ($('#searchBut').hasClass('fa-circle-stop'))
     {
         // abort the search ....
         $.ajax ({url: `executequery.py?action=stop`, type: "GET" });
         return;
     }

     SearchNowInActive ()
     if (G_SearchTimeoutID)
        clearTimeout (G_SearchTimeoutID);
     G_SearchTimeoutID = setTimeout(SearchQueryInfo, 1000);

     $.toast({
         heading: 'info',
         text: `Running search query now '${$('#searchQuery').val()}'`,
         icon: 'info'
     });
    scope = $('input[name="searchScope"]:checked').val();
    $.ajax ({url: `executequery.py`,
             type: "POST",
             data: {
                'action': 'start',
                'scope': scope,
                'query': $('#searchQuery').val()
             },
             dataType: "json",
             success: function(results)
             {
                 G_CurrentSearchList = results
                 // console.log(results);
                 SearchNowActive ();

                 $.toast({
                     heading: 'success',
                     text: `Search Results Returned<br>${results.length} rows matched`,
                     icon: 'success'
                 });

                 let srTable = `
<table id="searchList_tab" border=0 class="TableSelection SongListFormat" style="width:100%">
<thead>
    <tr>
        <th style="width:100%">
            <span>Filter Title(s) : ${results.length}</span>
            <span style="padding-left:10px"><input type="text" size=20 id="searchFilter"></span>
            <span style="padding-left:15px;text-decoration: none !important;">
                <button onclick="$('#searchList_tab tbody tr:visible .addToQueueList').click()" idx="-1" class="iconStyle24 selectItemHand" title="Add to Play Queue">
                    <i class="fa-solid fa-list"></i>
                </button>
            </span>
            <span style="padding-left:15px;text-decoration: none !important;">
                <button class="iconStyle24 selectItemHand hasContextMenu" title="Add to Play List" isdirectory="false" idx="-1">
                    <i class="fa-solid fa-table-list"></i>
                </button>
            </span>
        </th>
        <th style="min-width:200px">Album Name</th>
        <th>Artist</th>
        <th>Queue Item&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
    </tr>
</thead>`;
                 // console.log(key, value);
                 for (let idx=0; idx < results.length; idx++)
                 {
                     if (scope == 'db_metadata')
                     {
                         try {
                            metadata = JSON.parse(results[idx].metadata);
                         } catch {
                            console.log ("Failed parsing metadata! ?: " + results[idx].metadata);
                            continue;
                         }
                     }
                     else
                        metadata = results[idx].metadata;

                     art_url  = getDefaultCoverArt (metadata["content_type"]);

                     if (metadata["album_art_location"] != "")
                         art_url = `accessfile.py?type=${results[idx].type}&location=${encodeURI(metadata["album_art_location"])}`;

                     srTable += `
<tr class="dataRow songListRow selectItemHand" idx="${idx}">
    <td style="width:100%;display:flex">
                <img onclick="ViewLargeArt(this);" class="albumArtURLSml" src="${art_url}" style="height: 32px">
                <span style="padding-left:5px" onclick="OnClick_SearchList(${idx}, true)" class="songData">${metadata["title"]}</span>
    </td>
    <td onclick="OnClick_SearchList(${idx}, true)" class="songData">${metadata["albumName"]}</td>
    <td onclick="OnClick_SearchList(${idx}, true)" class="songData">${metadata["artist"]}</td>
    <!-- Queue / Playlist controls -->
    <td style="white-space:nowrap">
        <table class="fileListQueueControls" border=0>
        <tr>
            <td style="width:33% ;text-align:center;" class="iconStyle24 selectItemHand" onclick="SearchGotoFolder (${idx});" idx="${idx}" Title="Goto Folder">
                <i class="fa-solid fa-folder-open selectItemHand" ></i>
                <span style="display:none" class=" fileListQueueControlsTxt showHelpText">Goto Folder</span>
            </td>
            <td style="width:5px"></td>
            <td style="width:33%; text-align:center;" class="iconStyle24 selectItemHand addToQueueList" onclick="OnClick_SearchList(${idx})" idx="${idx}" Title="Add to Play Queue">
                <i class="fa-solid fa-list " ></i>
                <span style="display:none" class=" fileListQueueControlsTxt showHelpText">+Queue&nbsp;</span>
            </td>
            <td style="width:5px"></td>
            <td style="width:33%; !important;text-align: center;" class="iconStyle24 selectItemHand addToPlayList hasContextMenu" isDirectory="false" idx="${idx}" Title="Add to Play List">
                <i class="fa-solid fa-table-list"></i>
                <span style="display:none" class=" fileListQueueControlsTxt showHelpText">+Playlist</span>
            </td>
        </tr>
        </table>
    </td>
</tr>`;
                 }

                 srTable += "</table></div>";

                 // render playlist table and controls.
                 $('#searchList').html(srTable);
                 $("#searchFilter").keyup(function ()
                 {
                     var rows = $("#searchList_tab tbody").find(".songListRow").hide();
                     if (this.value.length)
                     {
                         var data = this.value.split(" ");
                         $.each(data, function (i, v)
                         {
                             let vl = v.toLowerCase();
                             for (idx = 0; idx < rows.length; idx++)
                             {
                                matchData = $(rows[idx]).find('.songData');
                                for (midx = 0; midx < matchData.length; midx++)
                                {
                                    if ($(matchData[midx]).text().toLowerCase().indexOf(vl) > -1)
                                    {
                                        $(rows[idx]).show();
                                        break;
                                    }
                                }
                             }
                         });
                     }
                     else
                        rows.show();
                 });

                 resizeFilePanels();
                 showHideIconInfo();
                 Build_PlaylistContextMenu ();
             },
             error: function(jqXHR, textStatus, errorThrown)
             {
                 SearchNowActive ();
                 $.toast({
                     heading: 'error',
                     text: `Search query error: '${textStatus}'`,
                     icon: 'error'
                 });
             }
           });
}

// Load Playlists upon start-up
var G_PlayListRefs = { };
$( document ).ready(function()
{
    LoadPlaylistNames ();
});

// Custom accordion action collapse all sections as needed.
$( document ).ready(function()
{
    $('.open').click(function () {
        $('.ui-accordion-header').removeClass('ui-corner-all').addClass('ui-accordion-header-active ui-state-active ui-corner-top').attr({'aria-selected':'true','tabindex':'0'});
        $('.ui-accordion-header .ui-icon').removeClass('ui-icon-triangle-1-e').addClass('ui-icon-triangle-1-s');
        $('.ui-accordion-content').addClass('ui-accordion-content-active').attr({'aria-expanded':'true','aria-hidden':'false'}).show();
        $(this).hide();
        $('.close').show();
    });
    $('.close').click(function () {
        $('.ui-accordion-header').removeClass('ui-accordion-header-active ui-state-active ui-corner-top').addClass('ui-corner-all').attr({'aria-selected':'false','tabindex':'-1'});
        $('.ui-accordion-header .ui-icon').removeClass('ui-icon-triangle-1-s').addClass('ui-icon-triangle-1-e');
        $('.ui-accordion-content').removeClass('ui-accordion-content-active').attr({'aria-expanded':'false','aria-hidden':'true'}).hide();
        $(this).hide();
        $('.open').show();
    });
    $('.ui-accordion-header').click(function () {
        $('.open').show();
        $('.close').show();
    });

    $("#playlistBrowser").accordion({ heightStyle: "content", collapsible:true, active:true});
    $("#playlistBrowser").on("accordionactivate", function( event, ui )
    {
         // console.log("here " + $(this).accordion('option', 'active'));
         //console.log($(this).accordion( "widget" )[0])
         //console.log(ui.newHeader.text());
         let refID = G_PlayListRefs[ui.newHeader.text()];
         // console.log ('loading ? ' + $(this).attr("playlistloaded"))
         if ($('#' + refID).attr('playlistloaded') != "true")
         {
            loadPlayList ($(this), ui.newHeader.text());
         }
    });

    $("#newPlayListName").on("keyup",function (e)
    {
        if (e.key === 'Enter' || e.keyCode === 13)
        {
            CreatePlayList($('#newPlayListName').val());
        }
    });

    $('#searchQuery').on("keyup",function (e)
    {
        if (e.key === 'Enter' || e.keyCode === 13)
        {
            runSearchQuery();
        }
    });

    $(window).on( "resize", function()
    {
        resizeFilePanels();
    });
});

function About ()
{
    $.toast({
         heading: 'Info',
         text: `<u><h2>Chrome Cast Audio Slinger</h2></u><b>Written by Steven De Toni<br>Aug 2024`,
         icon: 'info',
         hideAfter: 10000
     });
}

var G_ShowHideIconInfo = true;
function showHideIconInfo (mode=G_ShowHideIconInfo)
{
    G_ShowHideIconInfo = mode;
    if (G_ShowHideIconInfo)
    {
        $('.showHelpText').each(function() {
            $(this).css('display', '');
        });
        $('#showHelpTextInfo').addClass('controlEnabled');
    }
    else
    {
        $('.showHelpText').each(function() {
            $(this).css('display', 'none');
        });
        $('#showHelpTextInfo').removeClass('controlEnabled');
    }

    // Save settings in browser
    localStorage.setItem('G_ShowHideIconInfo', G_ShowHideIconInfo);
    resizeFilePanels();
}

function playerControlsExpandContract()
{
    // document.body.style.overflow = "hidden";

    
    if ($('.overlay-containerSml').css('display') == 'none')
    {
         document.body.style.overflow = "hidden"
         $('#busy-transcoding').css('font-size', '2px');
         $(".overlay-containerBig").hide(500, function() {
            $('#playerControlsSmallBig').removeClass('fa-angles-up');
            $('#playerControlsSmallBig').addClass('fa-angles-down');
            $('#playerControlsSmallBig').addClass('controlEnabled');
            resizeFilePanels();
            document.body.style.overflow = "";
         });
         $(".overlay-containerSml").show(500);
    }
    else
    {
         document.body.style.overflow = "hidden";
         $(".overlay-containerBig").show(500, function() {
            $('#playerControlsSmallBig').addClass('fa-angles-up');
            $('#playerControlsSmallBig').removeClass('fa-angles-down');
            $('#playerControlsSmallBig').removeClass('controlEnabled');
            $('#busy-transcoding').css('font-size', '5px');
            resizeFilePanels();
            document.body.style.overflow = "";
         });
         $(".overlay-containerSml").hide(500);
    }
}

var G_SmallBigViewMode = true;
function changeViewSmallBig (mode=G_SmallBigViewMode)
{
    G_SmallBigViewMode = mode;
    if (G_SmallBigViewMode && $('#playerControlsSmallBig').hasClass('fa-angles-up'))
    {
        playerControlsExpandContract();
    }
    else if (! G_SmallBigViewMode && $('#playerControlsSmallBig').hasClass('fa-angles-down'))
    {
        playerControlsExpandContract();
    }

    // Save settings in browser
    localStorage.setItem('G_PlayerViewMode', G_SmallBigViewMode);
}

function GetChromeCastDevices (forcedScan=false)
{
    $("#ccast_uuid").selectmenu();

    if (forcedScan)
    {
         $.toast({
             heading: 'Info',
             text: `Issuing a forced Chrome Cast scan<br>Please Wait...`,
             icon: 'info',
             hideAfter: 15000
         });
    }

    $.ajax ({url: `castdeviceinfo.py?action=${ forcedScan ? 'get_chromecasts_forced_scan' : 'get_chromecasts'}`,
             type: "GET",
             dataType: "json",
             success: function(results)
             {
                 if (forcedScan)
                 {
                     if (results.length > 0)
                     {
                         $.toast({
                             heading: 'Success',
                             text: `Chrome Cast devices found!`,
                             icon: 'success'
                         });
                     }
                     else
                     {
                         $.toast({
                             heading: 'Error',
                             text: `No Chrome Cast devices found!`,
                             icon: 'error'
                         });
                     }
                 }

                 ccast_uuid = $('#ccast_uuid').val();
                 let ccDevices = ""
                 for (idx = 0; idx < results.length; idx++)
                 {
                    ccDevices += `<option value='${results[idx].uuid}' ${ccast_uuid == results[idx].uuid ? 'selected' : '' }>${results[idx].friendly_name}</option>\n`;
                 }
                 ccDevices += `<option id="${BaseLocalPlayerID()}" value='${G_Local_Player}' ${ccast_uuid == '${G_Local_Player}' ? 'selected' : '' }>Local Player</option>\n`;

                 $('#ccast_uuid').html(ccDevices);
                 $("#ccast_uuid").selectmenu();
                 $("#ccast_uuid").selectmenu("refresh");
                 $('#ccast_uuid').on('selectmenuchange', function()
                 {
                     localStorage.setItem('ThisSelectedDevice', $("#ccast_uuid").val());
                     $("#ccast_uuid").trigger("change");
                 });

                 // set the last select/save device used
                 thisSelectedDevice = nvl(localStorage.getItem('ThisSelectedDevice', $("#ccast_uuid").val()));
                 if (thisSelectedDevice != "")
                 {
                     $("#ccast_uuid").val(thisSelectedDevice);
                     $("#ccast_uuid").trigger("change");
                     $("#ccast_uuid").selectmenu("refresh");
                 }
             }
           });
}

function SwitchUniqueLocalPlayer ()
{
    if ($("#NetWrkSharedLocalPlayerCB").is(':checked'))
    {
        G_Local_Player_UniqueID = "";
        G_Local_Player = BaseLocalPlayerID();
        localStorage.setItem('G_Local_Player_UniqueID', G_Local_Player_UniqueID);
        // console.log ("SwitchUniqueLocalPlayer :: checked :: "  + G_Local_Player)
    }
    else
    {
        G_Local_Player_UniqueID = GetOrMakeLocalPlayerUniqueID();
        localStorage.setItem('G_Local_Player_UniqueID', G_Local_Player_UniqueID);
        G_Local_Player = BaseLocalPlayerID() + '::' + G_Local_Player_UniqueID
        // console.log ("SwitchUniqueLocalPlayer :: unChecked :: " + G_Local_Player);
    }

    // console.log ("G_Local_Player :: " + G_Local_Player);
    $( '#' + BaseLocalPlayerID() ).attr('value', G_Local_Player);
    $("#ccast_uuid").trigger("change");
}

function GetOrMakeLocalPlayerUniqueID ()
{
    if (G_Generated_Local_Player_UniqueID == "")
    {
        G_Generated_Local_Player_UniqueID = generateUUID();
        localStorage.setItem('G_Generated_Local_Player_UniqueID', G_Generated_Local_Player_UniqueID);
    }
    return G_Generated_Local_Player_UniqueID;
}

function LoadUniqueLocalPlayerID ()
{
    $('#NetWrkSharedLocalPlayerCB').checkboxradio();

    G_Local_Player_UniqueID           =  nvl(localStorage.getItem('G_Local_Player_UniqueID'));
    G_Generated_Local_Player_UniqueID =  nvl(localStorage.getItem('G_Generated_Local_Player_UniqueID'));

    if (G_Local_Player_UniqueID == "" && G_Generated_Local_Player_UniqueID == "")
    {
        G_Local_Player_UniqueID = G_Generated_Local_Player_UniqueID = GetOrMakeLocalPlayerUniqueID ();
    }

    if (G_Local_Player_UniqueID != "")
    {
        $("#NetWrkSharedLocalPlayerCB").prop ('checked', false);
        $('#NetWrkSharedLocalPlayerCB').checkboxradio('refresh');
        SwitchUniqueLocalPlayer ();
    }
    else
    {
        $("#NetWrkSharedLocalPlayerCB").prop ('checked', true);
        $('#NetWrkSharedLocalPlayerCB').checkboxradio('refresh');    
    }
}

$( document ).ready(function()
{
    showHideIconInfo((localStorage.getItem('G_ShowHideIconInfo') == 'true'));
    changeViewSmallBig((localStorage.getItem('G_PlayerViewMode') == 'true'));
    LoadUniqueLocalPlayerID ();
    GetChromeCastDevices ();
});

