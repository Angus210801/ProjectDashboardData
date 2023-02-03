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
from Mysqlconn import Mysqlconn

from Subprogress import JamaData
#from Sub_savedata import UpdateDatabase

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
    LOGFOLDER_PATH = os.path.join(G_parameter['General']['baselogpath'],date)
    if not os.path.exists("db/jira/"):
        os.makedirs("db/jira")
    if not os.path.exists(LOGFOLDER_PATH):
        os.makedirs(LOGFOLDER_PATH)
    return LOGFOLDER_PATH

def get_project_tables(input_projects):
    active_projects = input_projects
    for project in active_projects:
        projectdb = Mysqlconn(
                host=G_parameter['General']['mysqlhost'],
                user=G_parameter['General']['mysqluser'],
                passwd=G_parameter['General']['mysqlpassword'],
                database=str(project["id"])
        )
        if projectdb.connect():
            projectdb.execute("SHOW TABLES")
            tables = projectdb.fetchall()
            if len(tables) >0:
                project["tables"] = [item[0] for item in tables]

            projectdb.cursor_close()
            projectdb.db_commit()
            projectdb.db_close()
    return active_projects

def check_database_projects(G_parameter, flag="ALL"):
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
            param2 - active_projects, type-list, store all 
    """
    all_projects = []
    active_projects = []
    mydb = Mysqlconn(
            host=G_parameter['General']['mysqlhost'],
            user=G_parameter['General']['mysqluser'],
            passwd=G_parameter['General']['mysqlpassword'],
            database="projects"
    )
    if mydb.connect():
        mydb.execute("SHOW DATABASES")
        for project in mydb.cursor:
            all_projects.append(project[0])
        if flag=="ALL":
            mydb.execute("SELECT keyy, name, status, jama FROM projects WHERE jama != 0")
        else:
            mydb.execute("SELECT keyy, name, status, jama FROM projects WHERE status = 'Active' AND jama != 0")

        results = mydb.fetchall()
        for keyy, name, webstatus, jamaId in results:
            if str(jamaId) not in all_projects:
                mydb.execute("CREATE DATABASE IF NOT EXISTS `%d`" % jamaId)
            active_projects.append({"keyy":keyy,"name":name,"webstatus":webstatus,"id":jamaId, "tables":[]})
        mydb.cursor_close()
        mydb.db_commit()
        mydb.db_close()
    active_projects = get_project_tables(active_projects)

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
    ### update {status:xxx} item in jama_projects to active_projects
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

#def throw_exception(name):
#    print("Sub progress %s raise a exception"%name)

# class MultilogExceptions(object):
#     def __init__(self, callable):
#         self.__callable = callable

#     def __call__(self, LOGFOLDER_PATH, *args, **kwargs):
#         print(LOGFILE_PATH_SUB)
#         try:
#             LOGGER_CONTROL = MyLogger(name = project["name"], log_name= project["name"], LOGFOLDER_PATH = LOGFOLDER_PATH)
#             LOGGER_SUB = LOGGER_CONTROL.getLogger()
#             logFile_path = LOGGER_CONTROL.getlogFile()
#             result = self.__callable(*args, **kwargs)

#         except Exception as e:
#             # Here we add some debugging help. If multiprocessing's
#             # debugging is on, it will arrange to log the traceback
#             exc_type, exc_value, exc_traceback = sys.exc_info()
#             #error(traceback.format_exc())
#             traceback.print_exc(file=open(LOGFILE_PATH_SUB,'a'))
#             # Re-raise the original exception so the Pool worker can
#             # clean up
#             raise
#         return result


def fetch_data(project, jama_itemtypes, G_parameter, LOGFOLDER_PATH):
    try:
        LOGGER_CONTROL = MyLogger(name = project["name"], log_name= project["name"], LOGFOLDER_PATH = LOGFOLDER_PATH)
        LOGGER_CONTROL.disable_console()
        LOGGER_SUB_HANDLE = LOGGER_CONTROL.getLogger()
        LOGFILE_PATH_SUB = LOGGER_CONTROL.getlogFile()
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exc()

    try:

        jamadata = JamaData(project, jama_itemtypes, G_parameter, LOGGER_SUB_HANDLE)
        jamadata.Get_and_Save()
        #jamadata.Save_all()

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exc(file=open(LOGFILE_PATH_SUB,'a'))


if __name__ == "__main__":
    test_projects = []
    jama_projects, jama_itemtypes = [],[]
    ### prepare phase
    G_parameter = read_config_file()
    LOGFOLDER_PATH = CreateFolders(G_parameter)
    LOGGER_CONTROL = MyLogger(name= "main", log_name="main", LOGFOLDER_PATH=LOGFOLDER_PATH)

    #LOGGER_CONTROL.disable_file()
    LOGGER_MAIN_HANDLE = LOGGER_CONTROL.getLogger()
    LOGGER_MAIN_HANDLE.info(G_parameter)


    ### pre project deal.
    all_projects, active_projects = check_database_projects(G_parameter, flag="ALL")

    rest_api = api_calls(G_parameter = G_parameter, loghandle = LOGGER_MAIN_HANDLE)
    jama_projects = rest_api.getResource(resource="projects", suffix="", params={"startAt":0,"maxResults":50}, \
                                               callback=data_reshape.getProjects_reshape, endless=True)
    jama_itemtypes = rest_api.getResource(resource="itemtypes", suffix="", params={"startAt":0,"maxResults":50}, \
                                              callback=data_reshape.getItemTypes_reshape, endless=True)


    #active_projects = [{'keyy': 'ANAC', 'name': 'Anaconda', 'webstatus': 'Active', 'id': 20434}, \
    #                   {'keyy': 'PYT', 'name': 'Python', 'webstatus': 'Active', 'id': 20446}]
    #active_projects = [{'keyy': 'ANAC', 'name': 'Anaconda', 'webstatus': 'Active', 'id': 20434}]
    #active_projects = [{'keyy': 'PYT', 'name': 'Python', 'webstatus': 'Active', 'id': 20446}]
    #print(active_projects)
    for i,item in enumerate(active_projects):
        if item["id"] in [20446,20434,20547,20550,20403,20568,20564,20565,20625]:
            test_projects = test_projects+[active_projects[i]]
    #print(test_projects)
    #print(jama_itemtypes)
    #final_projects = pre_deal_projects(jama_projects, active_projects, rest_api)
    final_projects = pre_deal_projects(jama_projects, test_projects, rest_api)
    #print(final_projects)
    #pdb.set_trace()

    ### start fetch data from jama for every project 
    #print(G_parameter['JamaTeams'])
    pool = multiprocessing.Pool(processes = 10)
    for project in final_projects:

        pool.apply_async(func=fetch_data, args=(project, jama_itemtypes , G_parameter,LOGFOLDER_PATH,))

    pool.close()
    pool.join()
    pool.terminate()
    pool.close()






