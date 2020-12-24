import os
import re
import sys
import pdb
import math
import json
import timeit
import requests
import mysql.connector

from datetime import datetime
from api.api_common import api_calls
from data_reshape import data_reshape
from Mysqlconn import Mysqlconn
#from helper.common import common_functions

#import logging
import threading
from concurrent.futures import ThreadPoolExecutor,as_completed
Max_threads = 10

import multiprocessing
import utils
from utils import MyLogger,MyConfigParser

"""
     Global parameter:
        G_parameter: for config.ini.
        all_projects: one project have one database.
        active_projects: user can decide which projects are active.
"""
G_parameter = {}
all_projects = []
active_projects = []
"""
    General check
	1.check folders->create main.log
"""
log_path = utils.checkFolders()
print(log_path)
LOGGER_CONTROL = MyLogger(log_name="main", log_path=log_path)
#LOGGER_CONTROL.disable_file()
LOGGER_Main = LOGGER_CONTROL.getLogger()

def read_config_file():
    global G_parameter
    cfg = MyConfigParser()
    cfg_path = "./config.ini"
    cfg.read(cfg_path)
    sections = cfg.sections()
    if 'General' in sections:
        G_parameter['General'] = {}
        for key in cfg['General']:
            G_parameter['General'][key] = cfg.get('General',key)
    if 'JamaTeams' in sections:
        G_parameter['JamaTeams'] = {}
        for key in cfg['JamaTeams']:
            teams = cfg.get('JamaTeams',key)
            G_parameter['JamaTeams'][key] = teams.splitlines()
    LOGGER_Main.info(G_parameter)

def check_database_projects():
    global all_projects,active_projects
    mydb = Mysqlconn(
            host="127.0.0.1",
            user="root",
            passwd="jabra2020",
            database="projects"
    )
    cursor = mydb.cursor
    mydb.execute("SHOW DATABASES")
    for project in cursor:
        all_projects.append(project[0])
    mydb.execute("SELECT * FROM projects WHERE status = 'Active' AND jama != 0")

    results = cursor.fetchall()
    for project in results:
        if str(project[3]) not in all_projects:
            mydb.execute("CREATE DATABASE IF NOT EXISTS `%d`" % project[3])
        active_projects.append(project)
    mydb.cursor_close()
    mydb.db_commit()
    mydb.db_close()
    print(active_projects)

#def main_single_project()

if __name__ == "__main__":
    read_config_file()
    check_database_projects()
    rest_api = api_calls(G_parameter = G_parameter)
    jama_projects = rest_api.getResource(resource="projects", suffix="", params={"startAt":0,"maxResults":50}, \
                                               callback=data_reshape.getProjects_reshape, endless=True)
    jama_itemtypes = rest_api.getResource(resource="itemtypes", suffix="", params={"startAt":0,"maxResults":50}, \
                                              callback=data_reshape.getItemTypes_reshape, endless=True)

    print(jama_projects)
    # jama_projects_ids = [item["id"] for item in jama_projects]
    # pool = multiprocessing.Pool(processes = 10)
    # # #print(jama_itemtypes)
    # for key, name, status, p_id in active_projects:
    #     if p_id not in jama_projects_ids:
    #         LOGGER_Main.error("This project %s is not in jama"%(name))

    # # 	msg = "hello %d" %(i)
    #     pool.apply_async(fetch_main, (msg, ))

    # pool = multiprocessing.Pool(processes = 10)

    # with multiprocessing.Pool(processes=10) as pool:

    #     results = pool.apply_async()





