import time
import pychromecast

chromecasts = pychromecast.get_chromecasts()

#[cc.device.friendly_name for cc in chromecasts]
#-> ['kitchen']

#cast = next(cc for cc in chromecasts if cc.device.friendly_name == 'kitchen')
cast = chromecasts[0][0]
cast.wait()
cast.media_controller.play_media("http://192.168.20.17:800/04 - Love Over Gold.flac", "audio/flac")
cast.status
cast.media_controller.block_until_active(20)
while cast.media_controller.status.player_state in ('PLAYING', 'BUFFERING'):
    cast.media_controller.update_status()
    print (f"state {cast.media_controller.status.player_state}  position {cast.media_controller.status.current_time}")
    time.sleep(0.5)

#-> CastStatus(is_active_input=None, is_stand_by=None, volume_level=0.25, volume_muted=False, app_id='ZZZ', display_name='Google Play Music', namespaces=['urn:x-cast:com.google.cast.broadcast', 'urn:x-cast:com.google.cast.media', 'urn:x-cast:com.google.cast.cac', 'urn:x-cast:com.google.android.music.cloudqueue'], session_id='YYY', transport_id='YYY', status_text='Google Play Music')

#http://192.168.20.23:8096/emby/Items/16987/Download?api_key=45e98d28016d49f6890ddbb75c27aea4