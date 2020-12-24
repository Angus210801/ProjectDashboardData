import mysql.connector

class Mysqlconn():

	def __init__(self, host, user, passwd, database):
		self.mydb = mysql.connector.connect(
			host=host,
			user=user,
			passwd=passwd,
			database=database
		)
		self.cursor = self.mydb.cursor()

	def execute(self, cmd):
		self.cursor.execute(cmd)

	def cursor_close(self):
		self.cursor.close()

	def db_commit(self):
		self.mydb.commit()

	def db_close(self):
		self.mydb.close()
