# -*- coding: utf-8 -*-
import os
import time
import logging
import configparser
from logging.handlers import RotatingFileHandler


class MyConfigParser(configparser.ConfigParser):

    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, optionstr):
        return optionstr

"""
	define logger object，inherit from logging.Logger，implement print to file and console
	Be Care!!!: 
	小心：这边的name和log_name是不一样的
	当然logging这个函数在多进程是不安全是指写入同一个文件，要是不同进程写入文件文件不一样不存在这个问题。
"""


class MyLogger(object):

	def __init__(self, name="logger", log_name=None, level=logging.DEBUG, console_level=logging.INFO, mode='a',config=None,LOGFOLDER_PATH=None):
		self.logger = logging.getLogger(name)

		#防止同一个实例加载好几次的handler
		if len(self.logger.handlers) > 0:
			return None
		# 设置logger的等级
		#super().__init__(name)
		# 注意这各会设置最低的等级，后续的设置只能比这个高
		self.logger.setLevel(level)

		if config == None:
			log_path_str = os.path.join(os.path.abspath(os.path.join(os.getcwd(), "")), "log")
			logmaxBytes = 256*1024*1024
			logbackupCount = 4
			logrotatestarted = 1

		if LOGFOLDER_PATH is not None:
			log_path_str = LOGFOLDER_PATH

		# python 在创建filehandler时路径不存在会报FileNotFoundError，这里要新建下路径（而具体文件存不存在都时可以的，python会自动创建文件）
		if not os.path.exists(log_path_str):
			os.makedirs(log_path_str)

		# 如何log名字没指定，组织一个带时间戳的字符串作为日志文件的名字,实现每天记录一个日志文件
		if log_name is None:
			date_time = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
			self.date_time = date_time
			logFile = os.path.join(log_path_str, date_time + '.log')
		else:
			logFile = os.path.join(log_path_str, log_name + '.log')
		self.logFile = logFile
		# 创建一个logging输出到文件的handler并设置等级和输出格式
		# mode属性用于控制写文件的模式，w模式每次程序运行都会覆盖之前的logger，而默认的是a则每次在文件末尾追加

		formatter = logging.Formatter('%(asctime)-.19s %(levelname)-.1s %(name)-5.5s %(funcName)-15.15s "%(message)s"')
		#fh = RotatingFileHandler(logFile, 'a', maxBytes=int(logmaxBytes) , backupCount=int(logbackupCount))
		fh = logging.FileHandler(logFile, mode)

		#if logrotatestarted == 1:
		#	fh.doRollover()
		fh.setLevel(level)
		fh.setFormatter(formatter)
		self.logger.addHandler(fh)
		self.logger.w_filehandler = fh

		# 控制台句柄
		ch = logging.StreamHandler()
		ch.setFormatter(formatter)
		ch.setLevel(console_level)
		self.logger.addHandler(ch)
		self.logger.w_consolehandle = ch

	def getLogger(self):
		return self.logger

	def getlogFile(self):
		return self.logFile

	def setLevel(self, level):
		self.logger.level = level

	def disable_file(self):
		handlers = self.logger.handlers
		if len(handlers) > 0 and self.logger.w_filehandler in handlers:
			self.logger.removeHandler(self.logger.w_filehandler)
		else:
			print("log file is already disable")

	def enable_file(self):
		handlers = self.logger.handlers
		if len(handlers) > 0 and self.logger.w_filehandler not in handlers:
			self.logger.addHandler(self.logger.w_filehandler)
		else:
			print("log file is already ensable")

	def disable_console(self):
		handlers = self.logger.handlers
		if len(handlers) > 0 and self.logger.w_consolehandle in handlers:
			self.logger.removeHandler(self.logger.w_consolehandle)
		else:
			print("console is already disable")

	def enable_console(self):
		handlers = self.logger.handlers
		if len(handlers) > 0 and self.logger.w_consolehandle not in handlers:
			self.logger.addHandler(self.logger.w_consolehandle)
		else:
			print("console is already enable")