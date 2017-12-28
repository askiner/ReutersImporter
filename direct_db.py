import cx_Oracle
from settings import db_credentials, Libraries

import os
os.environ["NLS_LANG"] = "AMERICAN_CIS.CL8MSWIN1251"


def db_connect(server, service, user, password):
    return cx_Oracle.connect("{}/{}@{}/{}".format(user, password, server, service))


def open_connection():
    return db_connect(db_credentials['server'],
                      db_credentials['service'],
                      db_credentials['user'],
                      db_credentials['password'])


def hide_db_fixedid_item(fixed_id, conn):

    if id is None:
        raise ValueError(id)

    if conn is None:
        conn = open_connection()

    if conn is not None:
        try:
            cur = conn.cursor()
            cur.prepare('UPDATE OBJETS SET ID_STOCK = :stockid WHERE ID_OBJET IN (SELECT ID_OBJET FROM IPTC WHERE FIXED_IDENT = \':fixedid\');')
            cur.execute(None, {'stockid': Libraries['partners_hidden'], 'fixedid': fixed_id})
            conn.commit()
        except cx_Oracle.DatabaseError as e:
            raise SystemError('Database connection error: %s' % format(e))