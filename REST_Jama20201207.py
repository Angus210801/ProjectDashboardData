import os
import re
import sys
import pdb
import time
import json
import timeit
import traceback

from datetime import datetime
from api.api_common import api_calls
from data_reshape import data_reshape
from Subprogress import Subprogress
from Mysqlconn import Mysqlconn


import multiprocessing
from utils import MyLogger,MyConfigParser



def read_config_file():
    """
        Discription:
            get the configuration of Config.ini and save it in G_paramter
    """
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
    return G_parameter

def CreateFolders(G_parameter):
    """
        Discription:
            check db/jira, log/%Y%m%d, if not exist, create it
        Parameters:
            param1 - G_paramter comes from Config.ini
    """
    date = time.strftime("%Y%m%d", time.localtime(time.time()))
    logFolder_path = os.path.join(G_parameter['General']['baselogpath'],date)
    if not os.path.exists("db/jira/"):
        os.makedirs("db/jira")
    if not os.path.exists(logFolder_path):
        os.makedirs(logFolder_path)
    return logFolder_path

def check_database_projects(G_parameter):
    """
        Discription:
            1.all projects store in projects database.
            2.every project have a database and database name is jamaid.
            3.if a project is configured active by website, it means that it should update from jama
            if a project(active) is found in projects database but have not seperated databse, should create it.

        Parameters:
            param1 - G_paramter comes from Config.ini
        Return:
            param1 - all_projects, type-list, store all projects ids,[20446....] 
            param2 - active_projects， type-list, store all 
    """
    all_projects = []
    active_projects = []
    mydb = Mysqlconn(
            host=G_parameter['General']['mysqlhost'],
            user=G_parameter['General']['mysqluser'],
            passwd=G_parameter['General']['mysqlpassword'],
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

def throw_exception(name):
    print("Sub progress %s raise a exception"%name)

def fetch_data(project, jama_itemtypes, G_parameter, logFolder_path):
    LOGGER_CONTROL = MyLogger(name = project["name"], log_name= project["name"], logFolder_path = logFolder_path)
    LOGGER_SUB = LOGGER_CONTROL.getLogger()
    logFile_path = LOGGER_CONTROL.getlogFile()

    try:
        sub_process = Subprogress(project, G_parameter, LOGGER_SUB)
        sub_process.Get_allcases()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
    #     #LOGGER_SUB.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        traceback.print_exc(file=open(logFile_path,'a'))


if __name__ == "__main__":
    jama_projects, jama_itemtypes = [],[]
    ### prepare phase
    G_parameter = read_config_file()
    logFolder_path = CreateFolders(G_parameter)
    LOGGER_CONTROL = MyLogger(name= "main", log_name="main", logFolder_path=logFolder_path)
    #Main_logFile_path = LOGGER_CONTROL.getlogFile()
    #LOGGER_CONTROL.disable_file()
    LOGGER_Main = LOGGER_CONTROL.getLogger()
    LOGGER_Main.info(G_parameter)


    ### pre project deal.
    all_projects, active_projects = check_database_projects(G_parameter)
    rest_api = api_calls(G_parameter = G_parameter, loghandle = LOGGER_Main)
    jama_projects = rest_api.getResource(resource="projects", suffix="", params={"startAt":0,"maxResults":50}, \
                                               callback=data_reshape.getProjects_reshape, endless=True)
    jama_itemtypes = rest_api.getResource(resource="itemtypes", suffix="", params={"startAt":0,"maxResults":50}, \
                                              callback=data_reshape.getItemTypes_reshape, endless=True)


    #active_projects = [{'keyy': 'ANAC', 'name': 'Anaconda', 'webstatus': 'Active', 'id': 20434}, \
    #                    {'keyy': 'BEZOS', 'name': 'Bezos', 'webstatus': 'Active', 'id': 20340}]
    active_projects = [{'keyy': 'ANAC', 'name': 'Anaconda', 'webstatus': 'Active', 'id': 20434}]
    #final_projects = pre_deal_projects(jama_projects, active_projects, rest_api)

    final_projects = active_projects
    ### start fetch data from jama for every project 
    pool = multiprocessing.Pool(processes = 1)
    for project in final_projects:
        pool.apply_async(func=fetch_data, args=(project, jama_itemtypes , G_parameter, logFolder_path,))

    pool.close()
    pool.join()
    pool.terminate()
    pool.close()






