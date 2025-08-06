import daemon.DBIO as DBIO
import datetime
import hashlib
import logging
import daemon.GlobalFuncs as GF
import sys
import json
import re
class SlingerDB (DBIO.DBIO):

    def __init__(self, dbFilename=DBIO.DB_NAME, version=1.0, sqlexec_maxtime=DBIO.SQLEXEC_MAXTIME, sqllock_maxtime=DBIO.SQLLOCK_MAXTIME):
        super().__init__(dbFilename, version,sqlexec_maxtime,sqllock_maxtime)
        self.abortSearch = False

    def __buildTables__ (self):
        try:
            dbVersion = self.sqlRtnResults('select version from db_version')[0]['version']
            logging.info('DBIO.__buildTables__ DB version detected : ' + str(dbVersion))
        except Exception as ex:
            super().__buildTables__()
            super().__updateDB__()
            dbVersion = self.sqlRtnResults('select version from db_version')[0]['version']

        if (dbVersion == 1.0):
            # update from version 1.0 to 1.1
            logging.info('DBIO.__buildTables__ Create Table: metadata_cache')
            self.sqlNoResults("create table if not exists metadata_cache (id_hash varchar(64) not null, location text, type varchar(16) not null, loaded date, metadata text,  primary key (id_hash, type))")

            self.sqlNoResults("create table if not exists playlists      (name varchar(64) not null, created date, lastplayed date,  primary key (name))")
            self.sqlNoResults("create table if not exists playlist_songs (seq integer primary key autoincrement, name varchar(64) not null, location text, type varchar(32))")
            self.commit()

        # if (dbVersion == x.x):
            # TODO : future SQL to create tables, indexes here

    def __updateDB__ (self):
        try:
            dbVersion = self.sqlRtnResults('select version from db_version')[0]['version']
            if dbVersion < self.version:
                if dbVersion == 1.0:
                    logging.info ("Updating db from version 1.0 to 1.1")
                    # todo : add SQL update data in tables
                    #self.sqlNoResults("update db_version "
                    #                  "set version   = ?,"
                    #                  "    timestamp = ?", (1.1,datetime.datetime.now()))
                    #dbVersion = 1.1
                    self.commit ()

                # if dbVersion == x.x:
                #   TODO : future updates here
        except Exception as ex:
            logging.error('DBIO.updateDB failure ' + str(ex))
            sys.exit(1)

    def StoreCachedMetadata (self, location, type, metadata):
        if not location:
            return None
        try:
            self.sqlNoResults('delete from metadata_cache where id_hash = ? ',(hashlib.sha256(location.encode('utf-8')).hexdigest(),) )
            self.sqlNoResults('insert into metadata_cache (id_hash, location, type, loaded, metadata) values (?, ?, ?, ?, ?)',(hashlib.sha256(location.encode('utf-8')).hexdigest(), location, type, datetime.datetime.now(), json.dumps(metadata, indent=4) ) )
            self.commit()
        except Exception as ex:
            logging.error('DBIO.StoreMetaDataCache failure ' + str(ex))
        return None

    def GetCachedMetadata (self, location, type):
        if not location:
            return None
        try:
            rows = self.sqlRtnResults('select * from metadata_cache where id_hash = ? and type = ?', (hashlib.sha256(location.encode('utf-8')).hexdigest(), type) )
            if len(rows) > 0:
                return json.loads(rows[0]['metadata'])
        except Exception as ex:
            logging.error('DBIO.GetCachedMetadata failure ' + str(ex))
        return None

    def ClearMetadataCache (self):
        self.sqlNoResults('delete from metadata_cache')
        self.commit()

    def DelMetadata (self, id_hash, type):
        self.sqlNoResults('delete from metadata_cache where id_hash = ? and type = ?', (id_hash, type))

    def SearchMetaDataTrackAlbumArtist (self, regexTrack, regexArtist, regexAlbum):
        cur = self.sqlRtnCursor('select * from metadata_cache')
        self.abortSearch = False
        columns = cur.description
        result = []
        for value in cur.fetchall():
            if self.abortSearch:
                break

            tmp = {}
            for (index, column) in enumerate(value):
                tmp[columns[index][0]] = column

            # check if this is the row to match on ...
            metadata = json.loads(tmp['metadata'])
            if re.search(regexTrack, metadata['title'], re.IGNORECASE)     and \
               (re.search(regexAlbum, metadata['albumName'], re.IGNORECASE) or re.search(regexArtist, metadata['artist'], re.IGNORECASE)):
                result.append(tmp)

        cur.close()
        return result

    def SearchMetaData (self, regex, maxResultsLen=1000):
        cur = self.sqlRtnCursor('select * from metadata_cache')
        self.abortSearch = False
        columns = cur.description
        result = []
        for value in cur.fetchall():
            if self.abortSearch:
                break

            tmp = {}
            for (index, column) in enumerate(value):
                tmp[columns[index][0]] = column

            # check if this is the row to match on ...
            metadata = json.loads(tmp['metadata'])
            if re.search(regex, metadata['title'], re.IGNORECASE) or        \
               re.search(regex, metadata['albumName'], re.IGNORECASE) or    \
               re.search(regex, metadata['artist'], re.IGNORECASE) or       \
               re.search(regex, metadata['album_artist'], re.IGNORECASE) or \
               re.search(regex, tmp['location'], re.IGNORECASE):
                if len(result) >= maxResultsLen:
                    break
                result.append(tmp)

        cur.close()
        return result

    def AbortSearch (self):
        self.abortSearch = True

    def ExistMetadataCache (self, location, type):
        if not location:
            return False
        try:
            rows = self.sqlRtnResults('select count(*) as numfnd from metadata_cache where id_hash = ? and type = ?',
                                      (hashlib.sha256(location.encode('utf-8')).hexdigest(), type))
            if len(rows) > 0 and rows[0]['numfnd'] > 0:
                return True
        except Exception as ex:
            logging.error('DBIO.ExistMetadataCache failure ' + str(ex))
        return False

    def CountMetadataCache (self):
        try:
            rows = self.sqlRtnResults('select count(*) as numfnd from metadata_cache')
            if len(rows) > 0:
                return rows[0]['numfnd']
        except Exception as ex:
            logging.error('DBIO.CountMetadataCache failure ' + str(ex))
        return -1

    def DeletePlayList (self, playListName):
        self.sqlNoResults('delete from playlists       where name = ? ',(playListName,))
        self.sqlNoResults('delete from playlist_songs where name = ? ', (playListName,))
        self.commit()

    def CreatePlayList (self, playListName):
        if self.PlayListExists(playListName):
            return False
        self.sqlNoResults("insert into playlists (name, created, lastplayed) values (?, ?, null)", (playListName.strip(), datetime.datetime.now()))
        self.commit()

    def GetPlayListNames(self):
        try:
            return self.sqlRtnResults('select name from playlists')
        except Exception as ex:
            logging.error('DBIO.GetPlayListNames failure ' + str(ex))
        return None

    def PlayListExists (self, name):
        count = self.sqlRtnResults('select count(*) as c from playlists where name = ?', (name,))
        if int(count[0]['c']) > 0:
            return True
        return False

    def PlayListSongExists (self, name, location, type ):
        try:
            return self.sqlRtnResults('select * from playlist_songs where name = ? and location = ? and type = ?', (name,location,type))[0]
        except:
            pass
        return None

    def AddPlayListSong (self, playListName, location, type, unique=True):
        if unique and self.PlayListSongExists(name=playListName, location=location, type=type):
            return

        try:
            self.TransactionLock()
            self.sqlNoResults('insert into playlist_songs (name, location, type) values (?, ? ,?)', (playListName, location, type))
            self.commit()
        finally:
            try:
                self.TransactionRelease()
            except:
                pass

    def GetPlayListSongs (self, playListName=None):
        try:
            if not playListName:
                return self.sqlRtnResults('select * from playlist_songs order by seq asc')

            return self.sqlRtnResults('select * from playlist_songs where name = ? order by seq asc',(playListName, ))
        except Exception as ex:
            logging.error('DBIO.GetPlayListSongs failure ' + str(ex))
        return None

    def GetPlayListSong (self, playListSeq):
        try:
            return self.sqlRtnResults('select * from playlist_songs where seq = ?', (playListSeq,))
        except Exception as ex:
            logging.error('DBIO.GetPlayListSong failure ' + str(ex))
        return None

    def RenamePlayList (self, name, newName):
        name = name.strip()
        newName = newName.strip()
        #rename the playlist if it does not alreay exist!
        if self.PlayListExists(newName):
            return False

        self.sqlNoResults('update playlists set      name = ? where name = ?',(newName, name))
        self.commit()
        self.sqlNoResults('update playlist_songs set name = ? where name = ?', (newName, name))
        self.commit()
        return True

    def DeletePlayListSongs (self, playListName, rowidList=None):
        try:
            if not rowidList:
                self.sqlNoResults('delete from playlist_songs where name = ?', (playListName,))
                self.commit()
                return

            for rowid in rowidList:
                self.sqlNoResults('delete from playlist_songs where name = ? and seq == ? ', (playListName, int(rowid)))
            self.commit()
        except Exception as ex:
            logging.error('DBIO.DeletePlayListSongs failure ' + str(ex))
        return

DB = SlingerDB(dbFilename=GF.Config.getSettingStr('slinger/DB_FILENAME', DBIO.DB_NAME),
            version=GF.Config.getSettingValue('slinger/DB_VERSION', DBIO.DB_VERSION),
            sqlexec_maxtime=GF.Config.getSettingValue('slinger/DB_SQLEXEC_MAXTIME', DBIO.SQLEXEC_MAXTIME),
            sqllock_maxtime=GF.Config.getSettingValue('slinger/DB_SQLLOCK_MAXTIME', DBIO.SQLLOCK_MAXTIME))
