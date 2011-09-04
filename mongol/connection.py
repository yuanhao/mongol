# -*- coding: utf-8 -*-
# Author: Yuanhao Li <jay_21cn [at] hotmail [dot] com>


import logging

from pymongo.connection import Connection
from pymongo.master_slave_connection import MasterSlaveConnection
from pymongo.errors import ConnectionFailure


_connection = None
db = None
_db_name = None
_db_username = None
_db_password = None


def bind_db(connection, database, username=None, password=None):
    global _connection, _db_name, _db_username, _db_password
    _connection = connection
    _db_name = database
    _db_username = username
    _db_password = password
    return get_db()


def get_db():
    global db, _connection
    if not _connection:
        raise ConnectionFailure, "Database connection not created. "

    if not db:
        if not _db_name:
            raise ConnectionFailure, "Not connected to the database. "
        db = _connection[_db_name]
        if _db_username and _db_password:
            _db.authenticate(_db_username, _db_password)

    return db


def get_connection():
    global _connection
    if not _connection:
        raise ConnectionFailure, "Database connection not created. "
    return _connection


def connect(database, username=None, password=None, **kwargs):
    global _connection
    if not _connection:
        _connection = Connection(**kwargs)
    return bind_db(_connection, database, username=username, password=password)


# TODO
# def sharding_connect():
    # pass


if __name__ == "__main__":
    db = connect('test')


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


