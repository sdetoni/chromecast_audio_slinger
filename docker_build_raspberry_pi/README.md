# Docker build run scripts 
This is a very simple docker build, and run scripts developed for the Raspberry PI.
The **start** command will run Chromecast Audio Slinger docker image in daemon mode. This
means you do not need to configure a Linux systemd server to have it run on a server reboot; 
this makes installer a little simpler than normal.

## Install Docker
Run install script to install docker:

**sudo ./install_docker**
```
apt install docker docker.io
```

## Build Docker Chromecast Audio Slinger Image
**sudo ./build**
```
export DOCKER_BUILDKIT=1
if [ ! -z "config" ]; then
    echo "Copying in default config directory from base source..."
    cp -rp ../config . 
fi
 
docker build -t chromecast-audio-slinger .
```

## Run Chromecast Audio Slinger Image
run script to run as a daemon:

**sudo ./start**


Edit the run script add your own config and media mount points.

```
docker rm -f chromecast_audio_slinger >/dev/null  2>&1

RUN_AS_USER=pi
CONFIG_DIR=$(pwd)/config
MEDIA_DIR=/mnt/MediaServer
TC_CACHE_LOCATION=/mnt/ffmpeg_cache
TEMP_FILE_LOCATION=/mnt/tmpfs
LOG_FILES=/dev/null

./logs/

echo Edit this script to change these.
echo
echo "Running with the current Custom Mount points:"
echo "   log files:                 ${LOG_FILES}"
echo "   config directory:          ${CONFIG_DIR}"
echo "   media directory:           ${MEDIA_DIR}"
echo "   tmp directory:             ${TEMP_FILE_LOCATION}"
echo "   transcode cache directory: ${TC_CACHE_LOCATION}"
echo

docker run -d \
  --name chromecast_audio_slinger \
  --network host \
  -v ${CONFIG_DIR}:/config \
  -v $LOG_FILES:/app/logs  \
  -v ${MEDIA_DIR}:${MEDIA_DIR} \
  -v ${TEMP_FILE_LOCATION}:${TEMP_FILE_LOCATION} \
  -v ${TC_CACHE_LOCATION}:${TC_CACHE_LOCATION} \
  --restart unless-stopped \
  chromecast-audio-slinger

echo

docker ps
docker logs -f chromecast_audio_slinger
```

## Stop Chromecast Audio Slinger Image
**sudo ./stop**
```
docker rm -f chromecast_audio_slinger >/dev/null  2>&1 
```

## Check Chromecast Audio Slinger logs
**sudo ./view_log**

```
docker logs -f chromecast_audio_slinger
```

## Check if Chromecast Audio Slinger Image is running
**sudo ./is_running**

```
docker ps | grep chromecast-audio-slinger

37d75cf239e7   chromecast-audio-slinger   "/entrypoint.sh"   3 hours ago   Up 3 hours             chromecast_audio_slinger
```

# Config Editing
Adjust config file in the **docker_build_raspberry_pi/config** directory to update settings 
within the docker image. This will allow you to refresh the git project source with affecting the docker 
config settings. 

Update config settings as required and restart the docker image for the changes to take effect.

```
sudo ./stop; sleep 1; sudo ./start
```


