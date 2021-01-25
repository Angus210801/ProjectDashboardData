import math
import threading
from datetime import datetime, timedelta
from Mysqlconn import Mysqlconn
from api.api_common import api_calls

from utils import MyLogger,MyConfigParser
from data_reshape import data_reshape
from concurrent.futures import ThreadPoolExecutor,as_completed


class Subprogress:

    def __init__(self, project, jama_itemtypes, G_parameter, loghandle):
        self.project = project
        self.jama_itemtypes = jama_itemtypes
        self.Not_Found = "Not Found"
        self.G_parameter = G_parameter
        self.Max_threads = G_parameter['General']["Max_threads"]
        self.Jamacaseteam = list(G_parameter['JamaTeams'].keys())
        ### Store all about tests in project . {testplan:{"testcycles":{}, "testgroups": {}, "testruns": {}, "testcases":{}}...}
        self.P_alltests = {}
        ### Store all testcases in project. {testcaseId:{xxx},...}, and add another information in testcase (status, team, upstream)
        self.P_testcases = {}
        ### Store all status in project. {satusId:status,...}
        self.P_status = {}
        ### Store all caseteams in project. {parentId:team,...}
        self.P_caseteams = {}

        self.P_allfeatures = []
        self.P_changefeatures = []
        self.P_deletefeatures = []

        self.P_changerequests = []
        self.P_allchangerequests = []

        self.existing_testplans = {}

        self.loghandle = loghandle
        self.rest_api = api_calls(G_parameter = self.G_parameter, loghandle = self.loghandle)
        self.mydb = Mysqlconn(
            host = self.G_parameter['General']['mysqlhost'],
            user = self.G_parameter['General']['mysqluser'],
            passwd = self.G_parameter['General']['mysqlpassword'],
            database = str(self.project["id"]),
            loghandle = self.loghandle
        )
        self.dbenable = self.mydb.connect()

    def getType(self, input_type):
        """Function to get item type"""
        for item_type in self.jama_itemtypes:
            if item_type["type_key"].lower() == input_type.lower():
                return item_type["id"]

    def get_status(self, statusId):
        status = 0
        status = self.rest_api.getResource(resource="picklistoptions", suffix="/%s"%(str(statusId)), \
                    params=None, endless=False, callback=data_reshape.getStatus)
        return status

    def get_upstreamrelationships(self, testcaseId):
        #### Get all testcases upstream
        testcaseupstream = ""
        testcaseupstream = self.rest_api.getResource(resource="items", suffix="/%s/upstreamrelationships"%(testcaseId), \
            params=None, callback=data_reshape.getUpstreamRelationships)

        return testcaseupstream

    def get_caseteam(self, parentId):
        result = {}
        team = "Unassigned"       
        count = 10

        while count > 1:
                #new_parantId = result["id"]
                result = self.rest_api.getResource(resource="items", suffix="/%s/parent"%parentId, \
                    params=None, endless=False, callback=data_reshape.getParent)
        
                if len(result) == 0 or count <=1:
                    team = "Unassigned"
                    break
                elif result["name"] in self.Jamacaseteam:
                    team = result["name"]
                    break
                elif "." not in result["sequence"]:
                    team = "Unassigned"
                    break
                else:
                    parentId = result["id"]
                    count = count - 1

        return team

    def get_testplans(self, projectId):
        existing_testplans = {}
        existing_testplans = self.rest_api.getResource(resource="testplans", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50}, callback=data_reshape.getTestPlans, endless=True)
        return existing_testplans

    def get_testcycles(self, testplanId):
        testcycles = {}
        testcycles = self.rest_api.getResource(resource="testplans", suffix="/%s/testcycles"%(testplanId), \
                params={"startAt":0,"maxResults":50}, callback=data_reshape.getTestCycles, endless=True)
        return testcycles

    def get_testgroups(self, testplanId):
        testgroups = {}
        testgroups = self.rest_api.getResource(resource="testplans", suffix="/%s/testgroups"%(testplanId), \
                params={"startAt":0,"maxResults":50}, callback=data_reshape.getTestGroups, endless=True)      
        return testgroups

    def get_testruns(self, testplanId):
        testruns = {}
        #### Get all test plan testruns
        Totaltestruns = self.rest_api.getResource(resource="testruns", suffix="", \
            params={"testPlan":testplanId}, callback=data_reshape.getTestRunsByTestplan_all, endless=False)

        with ThreadPoolExecutor(max_workers=int(self.Max_threads)) as executor:
            obj_list = []
            for startAt in range(math.ceil(Totaltestruns/50)):

                obj = executor.submit(self.rest_api.getResource,resource="testruns", suffix="", \
                    params={"testPlan":testplanId,"startAt":startAt,"maxResults":50}, callback=data_reshape.getTestRunsByTestplan_sub)
                obj_list.append(obj)

            for future in as_completed(obj_list):
                result = future.result()
                if len(result) == 0:
                    self.loghandle.info("Error:Test testruns result is None,testplane:%s"%(testplanId))
                testruns.update(result)
        return testruns

    def get_testcases(self, testplanId, testgroups):
        #### Get all test plan testcases
        testcases = {}
        with ThreadPoolExecutor(max_workers=int(self.Max_threads)) as executor:
            obj_list = []
            for testgroup in testgroups:
                #obj = executor.submit(self.rest_api.NewgetTestCases,"testplans",testplanId, testgroup, \
                #    params={"startAt":0,"maxResults":50}, endless=True, callback=data_reshape.getTestCases)
                obj = executor.submit(self.rest_api.getResource,resource="testplans", suffix="/%s/testgroups/%s/testcases"%(testplanId, testgroup), \
                        params={"startAt":0,"maxResults":50}, endless=True,callback=data_reshape.getTestCases)
                obj_list.append(obj)
                     
            for future in as_completed(obj_list):
                result = future.result()
                testcases.update(result)        
        return testcases

    def get_features(self, projectId, feature_type_id):
        features = []
        features = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":feature_type_id}, callback=data_reshape.getFeatures, endless=True)

        return features

    def get_change_features(self, projectId, feature_type_id):
        change_features = []
        change_features = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":feature_type_id,"lastActivityDate":str(datetime.now().date()-timedelta(30)) + "T00%3A00%3A00%2B00%3A00&"}, \
            callback=data_reshape.getChangeFeatures, endless=True)

        return change_features


    def get_delete_features(self, projectId, feature_type_id):
        delete_features = []
        delete_features = self.rest_api.getResource(resource="activities", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":feature_type_id,"eventType":"DELETE","objectType":"ITEM","deleteEvents":"true"}, \
            callback=data_reshape.getDeleteFeatures, endless=True)

        return delete_features

    def get_change_requests(self, projectId, item_type_id):
        change_requests = []
        change_requests = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id,"lastActivityDate":str(datetime.now().date()-timedelta(30)) + "T00%3A00%3A00%2B00%3A00&"}, \
            callback=data_reshape.getChangeRequests, endless=True)

        return change_requests

    def get_allchangerequests(self, projectId, item_type_id):
        allchange_requests = []
        allchange_requests = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id}, callback=data_reshape.getAllChangeRequests, endless=True)

        return allchange_requests

    def tidy_alltestcases(self):
        """
            Description:
                Tidy up all cases for project, remove the duplicate case, get extra information and store in the P_testcases
                Because a project have many testplans, every testplan have many testcases
                for example: Anaconda have two testplans- planA, planB. 
                planA have two testcases case1, case2, planB have three testcases case1, case2, case3
                P_testcases: Anaconda project have case1, case2 case3. 
                this step is to reduce the https request, it will take much time to get extra information if we \
                    request https the duplicate testcase: case1, case2, case1, case2, case3
            Parameters:
                param1 - existing_testplans: store all project testplans
                param2 - P_alltests: store all about project tests (testplans, testcycles, testgroups, testruns,testcases)
            return:
                param1 - P_testcases: store all project testcases
        """
        P_testcases = {}
        #for testplanId in [8041459,3904102]:
        for testplanId in self.tmp_list:
            tmp = self.P_alltests[testplanId]["testcases"]
            P_testcases.update(tmp)

        #self.loghandle.info(P_testcases)
        #### get extra information of testcase(status, team, upstream)
        statusId_dict = {k:v["statusId"]  for k, v in P_testcases.items()}
        parentId_dict = {k:v["parentId"]  for k, v in P_testcases.items()}
        testcaseId_list = list(P_testcases.keys())

        for testcaseId, statusId in statusId_dict.items():
            if statusId not in self.P_status:
                status = self.get_status(statusId)
                self.P_status[statusId] = status
                P_testcases[testcaseId]["status"] = status
            else:
                P_testcases[testcaseId]["status"] = status

        for testcaseId, parentId in parentId_dict.items():
            if parentId not in self.P_caseteams:
                team = self.get_caseteam(parentId)
                self.P_caseteams[parentId] = team
                P_testcases[testcaseId]["team"] = team
            else:
                P_testcases[testcaseId]["team"] = team

        for testcaseId in testcaseId_list:
            upstream = self.get_upstreamrelationships(testcaseId)
            P_testcases[testcaseId]["upstream"] = upstream

        self.P_testcases = P_testcases
        #self.loghandle.info(self.P_testcases)

    def tidy_alltestruns(self):
        """
            Description:
                Tidy up all testruns for project, remove the invalid testruns, fill the extra information into testruns
            Parameters:
                param1 - None
            return:
                param1 - P_testcases: store all project testcases
        """
        for testplanId in self.P_alltests:
            testruns = self.P_alltests[testplanId]["testruns"]
            testcycles = self.P_alltests[testplanId]["testcycles"]
            testgroups = self.P_alltests[testplanId]["testgroups"]
            testcases = self.P_alltests[testplanId]["testcases"]

            for testrunId in testruns:
                testcycleId = testruns[testrunId]["testcycleId"]
                testcaseId = testruns[testrunId]["testcaseId"]
                ### delete those testruns which are should update or are invalid
                if (testplanId not in self.existing_testplans) or \
                    (testcycleId not in testcycles) or \
                    (testcaseId not in testcases):
                    testruns[testrunId]["valid"] = False
                    continue
                testruns[testrunId]["testplanname"] = self.existing_testplans[testplanId]["name"]
                testruns[testrunId]["testcyclename"] = testcycles[testcycleId]["name"]
                testruns[testrunId]["testcasename"] = testcases[testcaseId]["name"]

                testgrouplist = testruns[testrunId]["testgroupId"]
                if isinstance(testgrouplist, list):
                    for num, testgroupId in enumerate(testgrouplist):
                        if testgroupId in testgroups:
                            testruns[testrunId]["testgroupId"] = testgroupId  ##list -> int, only save the correct groupid
                            testruns[testrunId]["testgroupname"] = testgroups[testgroupId]["name"]
                            break
                        if num == len(testgrouplist)-1 and testgroupId not in testgroups:
                            testruns[testrunId]["testgroupId"] = self.Not_Found
                            testruns[testrunId]["testgroupname"] = self.Not_Found
                else:
                    testruns[testrunId]["testgroupId"] = self.Not_Found
                    testruns[testrunId]["testgroupname"] = self.Not_Found
                testruns[testrunId]["testcasename"] = self.P_testcases[testcaseId]["name"]
                testruns[testrunId]["testcasestatus"] = self.P_testcases[testcaseId]["status"]
                testruns[testrunId]["testcaseteam"] = self.P_testcases[testcaseId]["team"]
                testruns[testrunId]["testcaseupstream"] = self.P_testcases[testcaseId]["upstream"]
                testruns[testrunId]["testcasedocumentKey"] = self.P_testcases[testcaseId]["documentKey"]
        #self.loghandle.info(self.P_alltests)


    def Get_alltests(self):
        #### Get test plans
        print_runs=[]

        self.loghandle.info("Get project name:%s id:%s all testplans"%(self.project["name"], self.project["id"]))
        existing_testplans = self.get_testplans(self.project["id"])
        self.existing_testplans = existing_testplans
        self.loghandle.info(self.existing_testplans)
        self.loghandle.info("Get project name:%s id:%s all testplans successful!!!"%(self.project["name"], self.project["id"]))

        #for testplanId in [8041459,3904102]:
        if self.project["keyy"] == "ANAC":
            self.tmp_list = [3904102]
        else:
            self.tmp_list = [7372947]
        for testplanId in self.tmp_list:
            testcycles, testgroups, testruns, testcases = {}, {}, {}, {}
            if not existing_testplans[testplanId]["archived"]:
                self.P_alltests[testplanId] = {"testcycles":{}, "testgroups": {}, "testruns": {}, "testcases":{}}
                testcycles = self.get_testcycles(testplanId)
                testgroups = self.get_testgroups(testplanId)
                testruns = self.get_testruns(testplanId)
                testcases = self.get_testcases(testplanId, testgroups)
                
                self.P_alltests[testplanId]["testcycles"] = testcycles
                self.P_alltests[testplanId]["testgroups"] = testgroups
                self.P_alltests[testplanId]["testruns"] = testruns
                self.P_alltests[testplanId]["testcases"] = testcases


        self.tidy_alltestcases()
        self.tidy_alltestruns()

        # self.P_alltests = P_alltests
        # self.P_testcases = P_testcases

    def Get_allfeatuers(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        feature_type_id = self.getType("feat")
        if "features" in tables:
            self.P_changefeatures =  self.get_change_features(projectId, feature_type_id)
            self.P_deletefeatures = self.get_delete_features(projectId,feature_type_id)
            #self.loghandle.info(self.P_changefeatures)
            #self.loghandle.info(self.P_deletefeatures)
        else:
            self.P_allfeatures = self.get_features(projectId, feature_type_id)
            #self.loghandle.info(self.P_allfeatures)

    def Get_allchangerequests(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        change_request_type_id = self.getType("cr")
        if "changes" in tables:
            self.P_changerequests =  self.get_change_requests(projectId, change_request_type_id)
            self.loghandle.info(self.P_changerequests)

        else:
            self.P_allchangerequests = self.get_allchangerequests(projectId, change_request_type_id)
            self.loghandle.info(self.P_allchangerequests)


    def Get_alldesignspecs(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        designspecs_type_id = self.getType("fspec")
        if "designspec" in tables:
            #self.P_changerequests =  self.get_change_designspecs(projectId, change_request_type_id)
            #self.loghandle.info(self.P_changerequests)
            pass

        else:
            pass
            #self.P_allchangerequests = self.get_alldesignspecs(projectId, change_request_type_id)
            #self.loghandle.info(self.P_allchangerequests)

    def update_database_tests(self):
        existing_testplans = self.existing_testplans
        create_tests_cmd = "CREATE TABLE IF NOT EXISTS tests ( \
                            testplan_id INT, \
                            testplan_name TEXT, \
                            testplan_status TEXT, \
                            rel TEXT, status TEXT, \
                            count INT, date TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_tests_cmd = "DELETE FROM tests WHERE date='{0}'".format(str(datetime.now().date()))
        select_testplanId_cmd = "SELECT testplan_id FROM tests GROUP BY testplan_id"

        select_testplanName_cmd = "SELECT testplan_name FROM tests WHERE testplan_id={0} LIMIT 1"
        update_testplanName_cmd = "UPDATE tests SET testplan_name='{0}' WHERE testplan_id={1}"
        update_testplanInactive_cmd = "UPDATE tests SET testplan_status='Inactive' WHERE testplan_id={0}"
        update_testplanActive_cmd = "UPDATE tests SET testplan_status='Active' WHERE testplan_id={0}"
       
        insert_testplanall_cmd = "INSERT INTO tests (testplan_id, testplan_name, testplan_status, rel, status, count, date) SELECT testplan_id, testplan_name, 'Active' as testplan_status, rel, status, count((@rn := @rn + 1)) as count, '{0}' as date FROM testcases cross join (select @rn := 0) const GROUP BY testplan_id, rel, status"

        self.mydb.execute(create_tests_cmd, rollback=False)
        self.mydb.execute(delete_tests_cmd, rollback=False)
        self.mydb.execute(select_testplanId_cmd, rollback=False)

        #### if testplan name or status is change, need to modify the history database data.
        rows = self.mydb.fetchall()
        tpsql = [row[0] for row in rows]
        # Check for unarchived test plans, name changes and remove deleted testplans
        for testplan in existing_testplans:
            if testplan in tpsql:
                self.mydb.execute(select_testplanName_cmd.format(testplan), rollback=False)
                tmp = self.mydb.fetchone()
                if tmp[0] != existing_testplans[testplan]["name"]:
                    self.mydb.execute(update_testplanName_cmd.format(existing_testplans[testplan]["name"], testplan), rollback=False)
                if existing_testplans[testplan]["archived"]:
                    self.mydb.execute(update_testplanInactive_cmd.format(testplan), rollback=False)
                if not existing_testplans[testplan]["archived"]:
                    self.mydb.execute(update_testplanActive_cmd.format(testplan), rollback=False)

        self.mydb.db_commit()

        self.mydb.execute(insert_testplanall_cmd, rollback=False)
        self.loghandle.info("Insert tests table successful")
        self.mydb.db_commit()


    def update_database_testruns(self):
        ### this function should be modifed ,it should save testruns, so it makes sense that db name is testruns 
        insert_many = []
        drop_testcases_cmd = "DROP TABLE IF EXISTS testcases"
        create_testcases_cmd = "CREATE TABLE IF NOT EXISTS testcases ( \
                            testplan_id INT, \
                            testplan_name TEXT, \
                            testgroup_id INT, \
                            testgroup_name TEXT, \
                            testcycle_id INT, \
                            testcycle_name TEXT, \
                            rel TEXT, \
                            id INT, \
                            uniqueid TEXT, \
                            name TEXT, \
                            status TEXT, \
                            upstream TEXT, \
                            downstream TEXT, \
                            executionDate TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        sql_many = "INSERT INTO testcases (testplan_id, testplan_name, \
                                        testgroup_id, testgroup_name, \
                                        testcycle_id, testcycle_name, \
                                        rel, id, uniqueid, name, status, \
                                        upstream, executionDate) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        
        self.mydb.execute(drop_testcases_cmd, rollback=False)
        self.mydb.execute(create_testcases_cmd, rollback=False)

        for testplanId in self.P_alltests:
            testruns = self.P_alltests[testplanId]["testruns"]
            for testrunId in testruns:
                if testruns[testrunId]["valid"] == True:
                    val = (testruns[testrunId]["testplanId"], testruns[testrunId]["testplanname"], \
                            testruns[testrunId]["testgroupId"], testruns[testrunId]["testgroupname"], \
                            testruns[testrunId]["testcycleId"], testruns[testrunId]["testcyclename"], \
                            "Unspecified", testruns[testrunId]["testcaseId"], testruns[testrunId]["testcasedocumentKey"], \
                            testruns[testrunId]["testcasename"], testruns[testrunId]["testcasestatus"], \
                            testruns[testrunId]["testcaseupstream"], testruns[testrunId]["executionDate"])
                    insert_many.append(val)

        self.mydb.executemany(sql_many, insert_many)
        self.mydb.db_commit()
        self.loghandle.info("Insert testcases table successful")
    
    def update_database_testapproval(self):
        testapproval = []
        create_testapproval_cmd = "CREATE TABLE IF NOT EXISTS testapproval ( \
                                rel TEXT, team TEXT, status TEXT, upstream TEXT, count INT, date TEXT \
                                ) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_testapproval_cmd = "DELETE FROM testapproval WHERE date='{0}'".format(str(datetime.now().date()))
        insert_testapproval_cmd = "INSERT INTO testapproval (rel, team, status, count, date, upstream) SELECT rel, team, status, count((@rn := @rn + 1)) as count, '{0}' as date, upstream FROM alltestapproval cross join (select @rn := 0) const GROUP BY rel, team, status, upstream".format(str(datetime.now().date()))

        drop_alltestapproval_cmd = "DROP TABLE IF EXISTS alltestapproval"
        create_alltestapproval_cmd = "CREATE TABLE IF NOT EXISTS alltestapproval ( \
                                id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT, team TEXT, upstream TEXT \
                                ) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        insert_alltestapproval_cmd = "INSERT INTO alltestapproval (id, uniqueid, name, status, rel, team, upstream) VALUES (%s, %s, %s, %s, %s, %s, %s)"

        for testcaseId in self.P_testcases:
            case  =  self.P_testcases[testcaseId]
            testapproval.append((case["id"], case["documentKey"], case["name"], case["status"], "Unspecified", case["team"], case["upstream"]))


        self.mydb.execute(create_testapproval_cmd, rollback=False)

        self.mydb.execute(drop_alltestapproval_cmd, rollback=False)
        self.mydb.execute(create_alltestapproval_cmd, rollback=False)

        self.mydb.execute(delete_testapproval_cmd, rollback=False)
        self.mydb.db_commit()
        self.mydb.executemany(insert_alltestapproval_cmd, testapproval)
        self.mydb.db_commit()
        self.mydb.execute(insert_testapproval_cmd, rollback=False)
        self.mydb.db_commit()

    def Store_alltests(self):
        if self.dbenable:
            self.update_database_testruns()
            self.update_database_tests()
            self.update_database_testapproval()
        else:
            self.loghandle.info("DB is not ready!!!")

    def update_database_features(self):
        allfeatures_list = []
        change_allfeatures_list = []
        delete_allfeatures_list = []

        create_features_cmd = "CREATE TABLE IF NOT EXISTS features (\
                                rel TEXT, status TEXT, count INT, date TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        insert_features_cmd = "INSERT INTO features (rel, status, count, date) \
                                SELECT rel, status, count((@rn := @rn + 1)) as count, '{0}' as date FROM allfeatures cross join (select @rn := 0) const GROUP BY rel, status".format(str(datetime.now().date()))
        delete_features_cmd = "DELETE FROM features WHERE date='{0}'".format(str(datetime.now().date()))

        create_allfeatures_cmd = "CREATE TABLE IF NOT EXISTS allfeatures (\
                                id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_allfeatures_cmd = "DELETE FROM allfeatures WHERE id=%d"
        insert_allfeatures_cmd = "INSERT INTO allfeatures (id, uniqueid, name, status, rel) VALUES (%s, %s, %s, %s, %s)"
        
        self.mydb.execute(create_features_cmd, rollback=False)
        self.mydb.execute(create_allfeatures_cmd, rollback=False)
        self.mydb.execute(delete_features_cmd, rollback=False)
        
        if len(self.P_allfeatures) > 0:
            for item in self.P_allfeatures:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified")
                allfeatures_list.append(val)
        else:
            for item in self.P_changefeatures:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified")
                change_allfeatures_list.append(val)

            for item in self.P_deletefeatures:
                delete_allfeatures_list.append(item["id"])
            for item in self.P_changefeatures:
                delete_allfeatures_list.append(item["id"])

        if len(self.P_allfeatures) > 0:
            self.mydb.executemany(insert_allfeatures_cmd, allfeatures_list)
        else:
            for item in delete_allfeatures_list:
                self.mydb.execute(delete_allfeatures_cmd%(item))
            self.mydb.executemany(insert_allfeatures_cmd, change_allfeatures_list)

        self.mydb.execute(insert_features_cmd)
        self.mydb.db_commit()


    def Store_features(self):
        if self.dbenable:
            self.update_database_features()
        else:
            self.loghandle.info("DB is not ready!!!")

    def update_database_allchange_requests(self):
        create_changes_cmd = "CREATE TABLE IF NOT EXISTS changes ( \
                                rel TEXT, status TEXT, priority TEXT, \
                                requester TEXT, date TEXT, count INT) ENGINE=InnoDB DEFAULT CHARSET=utf8"

        delete_changes_cmd = "DELETE FROM changes WHERE date='{0}'".format(str(datetime.now().date()))

        insert_changes_cmd = "INSERT INTO changes ( \
                                rel, status, priority, requester, date, count) \
                                SELECT rel, status, priority, requester, '{0}' as date, count((@rn := @rn + 1)) as count FROM allchanges \
                                cross join (select @rn := 0) const GROUP BY rel, status, priority, requester".format(str(datetime.now().date()))


        create_allchanges_cmd = "CREATE TABLE IF NOT EXISTS allchanges ( \
                                id INT, uniqueid TEXT, name TEXT, \
                                status TEXT, rel TEXT, priority TEXT, \
                                requester TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_allchanges_cmd = "DELETE FROM allchanges WHERE id=%d"
        insert_allchanges_cmd = "INSERT INTO allchanges (id, uniqueid, name, status, rel, priority, requester) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        self.mydb.execute(create_changes_cmd, rollback=False)
        self.mydb.execute(create_allchanges_cmd, rollback=False)
        self.mydb.execute(delete_changes_cmd, rollback=False)

        insert_many = []
        if len(self.P_allchangerequests) >0:
            for item in self.P_allchangerequests:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["priority"], item["req"])
                insert_many.append(val)
        else:
            for item in self.P_changerequests:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["priority"], item["req"]) 
                insert_many.append(val)
                self.mydb.execute(delete_allchanges_cmd%(item["id"]), rollback=False)

        self.mydb.executemany(insert_allchanges_cmd, insert_many)
        self.mydb.db_commit()
        self.mydb.execute(insert_changes_cmd, rollback=False)
        self.mydb.db_commit()

    def Store_allchange_requests(self):
        if self.dbenable:
            self.update_database_allchange_requests()
        else:
            self.loghandle.info("DB is not ready!!!")
