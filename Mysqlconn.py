import mysql.connector

class Mysqlconn:

	def __init__(self, host, user, passwd, database, loghandle=None):

		self.mydb = None
		self.cursor = None
		self.host = host
		self.user = user
		self.passwd = passwd
		self.database = database

		self.loghandle = loghandle

	def Print(self, message, flag = "info"):
		if self.loghandle is None:
			print(flag+": "+message)
		else:
			if flag in ["info", "INFO", "I", "i"]:
				self.loghandle.info(message)
			elif flag in ["error", "Error", "E", "e"]:
				self.loghandle.error(message)

	def checkdb(self):
		if self.mydb is None or self.cursor is None:
			self.Print("mydb or cursor is None!!!")
			return False
		else:
			return True

	def connect(self):
		try:
			self.mydb = mysql.connector.connect(
				host = self.host,
				user = self.user,
				passwd = self.passwd,
				database = self.database
			)
			self.cursor = self.mydb.cursor()
			self.Print("Connet %s successfully!!!"%(self.database))
			return True
		except Exception as e:
			self.Print(e)
			return False

	def execute(self, cmd, rollback=False):
		if self.checkdb():
			if rollback==False:
				self.cursor.execute(cmd)
			else:
				try:
					self.cursor.execute(cmd)
				except Exception as e:
					self.mydb.rollback()
					self.Print(e)
		else:
			self.Print("execute %s failed because mydb or cursor is None!!!")

	def fetchall(self):
		result = []
		if self.checkdb():
			result = self.cursor.fetchall()
		return result

	def cursor_close(self):
		if self.checkdb():
			self.cursor.close()

	def db_commit(self):
		if self.checkdb():
			self.mydb.commit()

	def db_close(self):
		if self.checkdb():
			self.mydb.close()

