'''
####################################################
# Purpose: DB I/O for storing/retrieving information
# Written by Steven De Toni
####################################################
'''
import pprint
import sqlite3 as lite
import logging
import sys
import datetime
from threading import Thread, Lock, Timer

DB_VERSION      = 1.0
DB_NAME         = "daemon.db"
SQLEXEC_MAXTIME = 600   # 10 mins
SQLLOCK_MAXTIME = 30000 # 30 seconds

def lowerStrip (s): return s.strip().lower()
def upperStrip (s): return s.strip().upper()

class DBIO (object):
    datetime_format  = "%Y-%m-%d %H:%M:%S.%f"
    datetime_format2 = "%Y-%m-%d %H:%M:%S"

    sqlexec_maxtime = None
    sqllock_maxtime = None
    dbFilename      = None
    version         = None
    settings        = None
    dbcon           = None
    dbOpen          = None
    mutex           = None
    mutexCount      = None

    def __SQLInterrupt (self):
        logging.error('DBIO.__SQLInterrupt called!')
        self.__ReopenDB ()

    def __updateDB__ (self):
        try:
            dbVersion = self.sqlRtnResults('select version from db_version')[0]['version']
            if dbVersion < self.version:
                if dbVersion == 0.0:
                    # todo : add SQL to create tables, add column, and update data
                    logging.info ("Updating db from version 0.0 to 1.0")
                    self.sqlNoResults("update db_version "
                                      "set version   = ?,"
                                      "    timestamp = ?", (1.0,datetime.datetime.now()))
                    self.commit ()

                '''# TODO : future upgrade sql commands go here!
                if self.version == 2.0:                     
                    self.sqlNoResults("update db_version "
                                      "set version   = ?,"
                                      "    timestamp = ?", (2.0,datetime.datetime.now()))
                    self.commit ()
                '''

        except Exception as ex:
            logging.error('DBIO.updateDB failure ' + str(ex))
            sys.exit(1)

    def __buildTables__ (self):
        try:
            dbVersion = self.sqlRtnResults('select version from db_version')[0]['version']
            logging.info('DBIO.__buildTables__ DB version detected : ' + str(dbVersion))
        except Exception as ex:
            logging.info('DBIO.__buildTables__ Building DB Tables... ')
            self.sqlNoResults ("PRAGMA main.temp_store=MEMORY")
            self.sqlNoResults ("PRAGMA main.cache_size=10000")
            self.sqlNoResults ("PRAGMA main.cache_size=5000")

            logging.info('DBIO.__buildTables__ Create Table: db_version')
            self.sqlNoResults ("create table if not exists db_version (version numeric, timestamp date)")
            self.sqlNoResults ("delete from db_version")
            self.sqlNoResults ("insert into db_version (version, timestamp) values (?, ?)", (0.0, datetime.datetime.now()))
            self.commit()

    def __CleanDB__ (self):
        self.TransactionLock()
        try:
            # TODO db maintenance
            self.commit()
        finally:
            self.TransactionRelease()

    def __ReopenDB (self):
        # if db connection open, close and reopen db
        if self.dbcon:
            logging.info('DBIO.__ReopenDB Closing DB!')
            self.dbcon.interrupt()
            self.dbcon.close()
            self.dbcon = None

        logging.info('DBIO.__ReopenDB Opening DB!')
        self.dbcon = lite.connect(self.dbFilename, check_same_thread=False)
        self.sqlNoResults("PRAGMA busy_timeout = " + str(self.sqllock_maxtime))
        logging.info('DBIO.__ReopenDB DB Open!')

    def __del__(self):
        try:
            if self.dbcon:
                self.dbcon.close()
                self.dbcon = None
            self.dbOpen = False
            self.mutex  = None
        except Exception as ex:
            pass

    # --------------------------------------------------------

    def __init__(self, dbFilename = DB_NAME, version = 1.0, sqlexec_maxtime=SQLEXEC_MAXTIME, sqllock_maxtime=SQLLOCK_MAXTIME):
        self.version         = version
        self.dbFilename      = dbFilename
        self.sqlexec_maxtime = sqlexec_maxtime
        self.sqllock_maxtime = sqllock_maxtime
        self.mutex           = Lock()
        self.mutexCount      = 0
        self.settings        = {}
        self.__ReopenDB()

        self.dbOpen    = False
        self.__buildTables__()
        self.__updateDB__()
        self.__CleanDB__()
        self.dbOpen    = True

    # ---- DateTime Conversion -------------------------------

    def toPythonDateTime (self, rowDateTimeStr):
        try:
            return datetime.datetime.strptime(rowDateTimeStr, self.datetime_format)
        except Exception as e:
            pass
        return datetime.datetime.strptime(rowDateTimeStr, self.datetime_format2)

    def DTSecsSinceEpoch (self, dt):
        epoch = datetime.datetime.utcfromtimestamp(0)
        delta = dt - epoch
        return delta.seconds + ((delta.days * 24) * 3600)

    def sqlRtnCursor(self, sql, *args):
        bindings = ""
        for idx, item in enumerate(args):
            bindings = bindings + str(item)
        dbgSQL = sql + "\nSQL Bindings:" + bindings
        logging.debug("DBIO:__SQLRtn\n" + dbgSQL + "\n")

        # Set a time limit on SQL
        t = Timer(self.sqlexec_maxtime, self.__SQLInterrupt)
        try:
            t.start()
            cur = self.dbcon.cursor()
            cur.execute (sql, *args)
            logging.debug("DBIO:__SQLRtn completed!")
            return cur
        except Exception as ex:
            logging.error('DBIO.__SQL_Rtn__ failure :\n' + dbgSQL + '\n' + str(ex) )
        finally:
            t.cancel()
            # sys.exit(1)

    def sqlNoResults(self, sql, *args):
        self.sqlRtnCursor(sql, *args).close()

    def buildSQLResultList(self, cur):
        columns = cur.description
        result = []
        for value in cur.fetchall():
            tmp = {}
            for (index, column) in enumerate(value):
                tmp[columns[index][0]] = column
            result.append(tmp)
        return result

    def sqlRtnResults(self, sql, *args):
        cur = self.sqlRtnCursor(sql, *args)
        results = self.buildSQLResultList(cur)
        cur.close()
        return results

    def TransactionLock (self):
        logging.debug ('DBIO.TransactionLock @ ' + str(self.mutexCount))
        self.mutex.acquire()
        self.mutexCount += 1
        logging.debug('DBIO.TransactionLock Open @ ' + str(self.mutexCount))

    def TransactionRelease(self):
        logging.debug('DBIO.TransactionRelease Close @ ' + str(self.mutexCount))
        self.mutex.release()

    def commit (self):
        try:
            self.dbcon.commit()
        except Exception as ex:
            logging.error('DBIO.__Commit__ failure : ' + str(ex) )
            # sys.exit(1)

    # ---- User Functions ------------------------------------

    # TODO : Add user methods here to access database or inherit from this class to extend it...

    # ---- Debugging/Misc ------------------------------------

    def dumpRows (self, rowList):
        pprint.pprint(rowList)
