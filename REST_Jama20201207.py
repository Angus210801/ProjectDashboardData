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
#G_parameter = {}

#jama_status = {}
#[{'keyy': 'ANAC', 'name': 'Anaconda', 'webstatus': 'Active', 'jama_id': 20434}, {'keyy': 'BEZOS', 'name': 'Bezos', 'webstatus': 'Active', 'jama_id': 20340}]
"""
    General check
	1.check folders->create main.log
"""
#log_path = utils.checkFolders()
#print(log_path)
#LOGGER_CONTROL = MyLogger(log_name="main", log_path=log_path)
#LOGGER_CONTROL.disable_file()
#LOGGER_Main = LOGGER_CONTROL.getLogger()

def read_config_file():
    G_parameter = {}
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
    print(G_parameter)
    return G_parameter

def check_database_projects():
    #global all_projects,active_projects
    all_projects = []
    active_projects = []
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
    mydb.execute("SELECT keyy, name, status, jama FROM projects WHERE status = 'Active' AND jama != 0")

    results = cursor.fetchall()
    for keyy, name, webstatus, jamaId in results:
        if str(jamaId) not in all_projects:
            mydb.execute("CREATE DATABASE IF NOT EXISTS `%d`" % jamaId)
        active_projects.append({"keyy":keyy,"name":name,"webstatus":webstatus,"id":jamaId})
    mydb.cursor_close()
    mydb.db_commit()
    mydb.db_close()
    return all_projects, active_projects

def pre_deal_projects(jama_projects, active_projects, rest_api):
    jama_status = {}
    """ 
        Discription: 
            Project Filter 1: project that configured by web page but not in jama will be removed
            Project Filter 2: project in jama but its status is in [ignore|test|demo|template|archive] will be removed 
        Parameters:
                param1 - jama_projects, it is jama all projects
                param2 - active_projects, it is configured by web page
        Returns:
            final_projects: it is final projects that need to fetch data from jama
    """
    final_projects = []
    jama_projects_ids = { project["id"]:num for num, project in enumerate(jama_projects) }
    ##Filter1
    mid_results = list(filter(lambda x:x["id"] in list(jama_projects_ids.keys()), active_projects))
    ### update {status:xxx} item in jama_projects to activate_projects
    for project in mid_results:
        num = jama_projects_ids[project["id"]]
        update_item = {"statusId":jama_projects[num]["statusId"]}
        project.update(update_item)
    ##Filter 2
    for project in mid_results:
        if project["statusId"] not in jama_status:
            statusName = rest_api.getResource(resource="picklistoptions", suffix="/"+str(project["statusId"]), \
                                                callback=data_reshape.getStatus_reshape)
            jama_status[project["statusId"]]= {"name":statusName}
        else:
            statusName = jama_status[project["statusId"]]["name"]
        #print(project,statusName)
        if statusName == "Active":
            final_projects.append(project)
    return final_projects

def fetch_data(project, G_parameter, log_path):
        LOGGER_CONTROL = MyLogger(log_name=project["name"], log_path=log_path)
        LOGGER_SUB = LOGGER_CONTROL.getLogger()
        rest_api = api_calls(G_parameter = G_parameter, loghandle = LOGGER_SUB)
        existing_testplans = rest_api.getResource(resource="testplans", suffix="", \
                params={"project":project["id"],"startAt":0,"maxResults":50}, callback=data_reshape.getTestPlans, endless=True)
        LOGGER_SUB.info(existing_testplans)


if __name__ == "__main__":
    ### prepare phase
    log_path = utils.checkFolders()
    G_parameter = read_config_file()
    log_path = utils.checkFolders()
    LOGGER_CONTROL = MyLogger(log_name="main", log_path=log_path)
    #LOGGER_CONTROL.disable_file()
    LOGGER_Main = LOGGER_CONTROL.getLogger()
    LOGGER_Main.info(G_parameter)


    ### pre project deal.
    all_projects, active_projects = check_database_projects()
    rest_api = api_calls(G_parameter = G_parameter, loghandle = LOGGER_Main)
    jama_projects = rest_api.getResource(resource="projects", suffix="", params={"startAt":0,"maxResults":50}, \
                                               callback=data_reshape.getProjects_reshape, endless=True)
    jama_itemtypes = rest_api.getResource(resource="itemtypes", suffix="", params={"startAt":0,"maxResults":50}, \
                                              callback=data_reshape.getItemTypes_reshape, endless=True)

    #print(jama_projects)
    active_projects = [{'keyy': 'ANAC', 'name': 'Anaconda', 'webstatus': 'Active', 'id': 20434}, \
                        {'keyy': 'BEZOS', 'name': 'Bezos', 'webstatus': 'Active', 'id': 20340}]
    final_projects = pre_deal_projects(jama_projects, active_projects, rest_api)

    ### start fetch data from jama for every project 
    pool = multiprocessing.Pool(processes = 10)
    for project in final_projects:
        pool.apply_async(func=fetch_data, args=(project, G_parameter, log_path))

    pool.close()
    pool.join()  # 进程池中进程执行完毕后再关闭，如果注释，那么程序直接关闭。
    pool.terminate()
    pool.close()
    # #     if p_id not in jama_projects_ids:
    #         LOGGER_Main.error("This project %s is not in jama"%(name))
    #         continue
    #     rest_api.getResource(resource="picklistoptions", suffix="", project["status"])
    # # 	msg = "hello %d" %(i)
    #    pool.apply_async(main_single_project, (msg, ))

    # pool = multiprocessing.Pool(processes = 10)

    # with multiprocessing.Pool(processes=10) as pool:

    #     results = pool.apply_async()





