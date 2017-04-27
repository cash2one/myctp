#coding=utf-8
import sys
from sqlalchemy import create_engine
import MySQLdb
import pandas as pd

class SqlApi():
    def __init__(self):
        self.host = 'localhost'
        self.user = 'root'
        self.passwd = '880501'
        self.dbname = 'stock'


    def readFromSql(self, table):
        mysql_cn = MySQLdb.connect(self.host, port=3306, user=self.user, passwd=self.passwd, db=self.dbname)
        sql_exce = 'select count(*) from %s;' % table
        df_mysql = pd.read_sql(sql_exce, con=mysql_cn)
        mysql_cn.close()
        return df_mysql

    def saveToSql(self, data, table):
        mysql_cn = MySQLdb.connect(self.host, port=3306, user=self.user, passwd=self.passwd, db=self.dbname)
        engine = create_engine('mysql://%s:%s@%s/%s?charset=utf8' % (self.user, self.passwd, self.host, self.dbname))
        data.to_sql(table, engine)