import math
import threading
from datetime import datetime, timedelta
from Mysqlconn import Mysqlconn
from api.api_common import api_calls
from UpdateDatabase import UpdateDatabase

from utils import MyLogger,MyConfigParser
from data_reshape import data_reshape
from concurrent.futures import ThreadPoolExecutor,as_completed


class JamaData:

    def __init__(self, project, jama_itemtypes, G_parameter, loghandle):
        self.project = project
        self.loghandle = loghandle
        self.jama_itemtypes = jama_itemtypes
        self.Not_Found = "Not Found"
        self.G_parameter = G_parameter
        self.Max_threads = G_parameter['General']["Max_threads"]

        self.Jamamainteam = list(G_parameter['JamaTeams'].keys())
        self.Jamasubteams = list(G_parameter['JamaTeams'].values()) ## it also includes mainteam name, the first one

        ### P_alltests all about tests in project . {testplan:{"testcycles":{}, "testgroups": {}, "testruns": {}, "testcases":{}}...}
        ### P_testcases all testcases in project. {testcaseId:{xxx},...}, and add another information in testcase (status, team, upstream)
        ### Store all caseteams in project. {parentId:team,...}
        self.existing_testplans = {}
        self.P_alltests, self.P_testcases, self.P_caseteams = {}, {}, {}
        ### all about picklistoptions
        self.P_picklistoptions = {}

        self.P_changefeatures,     self.P_deletefeatures,    self.P_allfeatures     = [], [], []
        self.P_changeuserstories, self.P_deleteuserstories, self.P_alluserstories  = [], [], []
        self.P_changedefects,     self.P_deletedefects,     self.P_alldefects      = [], [], []
        self.P_changerequests,    self.P_allchangerequests                         = [], []
        self.P_changedesignspecs, self.P_alldesignspecs                            = [], []

        self.P_allrequirements, self.P_reqcovered = [], {}

        self.P_featurestest, self.P_requirementsTest= [],[]
        self.P_c_featurestest, self.P_c_requirementsTest = [], []
        self.P_allfeatures_test_status, self.P_allrequirements_test_status = [], []

        self.rest_api = api_calls(G_parameter = self.G_parameter, loghandle = self.loghandle)
        self.Update_db = UpdateDatabase(project, jama_itemtypes, G_parameter, loghandle)


    def getType(self, input_type):
        """Function to get item type"""
        for item_type in self.jama_itemtypes:
            if item_type["type_key"].lower() == input_type.lower():
                return item_type["id"]

    # def get_status(self, statusId):
    #     status = 0
    #     status = self.rest_api.getResource(resource="picklistoptions", suffix="/%s"%(str(statusId)), \
    #                 params=None, endless=False, callback=data_reshape.getStatus)
    #     return status

    def get_picklistoptions(self, picklistoptionsId):
        result = ""
        if picklistoptionsId in self.P_picklistoptions:
            result = self.P_picklistoptions[picklistoptionsId]
        else:
            result = self.rest_api.getResource(resource="picklistoptions", suffix="/%s"%(str(picklistoptionsId)), \
                        params=None, endless=False, callback=data_reshape.getPicklistOptions)
            self.P_picklistoptions[picklistoptionsId] = result
        return result

    def get_multipicklistoptions(self, picklistoptionsId_list):
        ## for requirements
        result = []
        name = ""
        mainteam = ""
        for item in picklistoptionsId_list:
            name = self.get_picklistoptions(item)
            ## if name is subteam name, find its mainteam name, if it is mainteam, reqteam = mainteam 
            for i, subteam in enumerate(self.Jamasubteams):
                if name in subteam:
                    mainteam = subteam[0] ##mainteam name
                    break
                if i == len(self.Jamasubteams) - 1 and name not in subteam:
                    self.loghandle.info("%s don't find the mainteam name from G_parameter"%(name))

            result.append({"reqteam":name,"mainteam":mainteam,"verified":0})
        return result

    def get_upstreamrelationships(self, itemId):
        #### Get all upstream
        upstreamrelationships = ""
        upstreamrelationships = self.rest_api.getResource(resource="items", suffix="/%s/upstreamrelationships"%(itemId), \
            params=None, callback=data_reshape.getUpstreamRelationships)

        return upstreamrelationships

    def get_downstreamcase_parentlist(self, itemId):
        downstreamcase_parentlist = []
        downstreamcase_parentlist = self.rest_api.getResource(resource="items", suffix="/%s/downstreamrelated"%(itemId), \
            params=None, callback=data_reshape.getDownstreamCaseParentList)
        return downstreamcase_parentlist

    def get_downstreamrelationships(self, itemId):
        #### Get all upstream
        downstreamrelationships = ""
        downstreamrelationships = self.rest_api.getResource(resource="items", suffix="/%s/downstreamrelationships"%(itemId), \
            params=None, callback=data_reshape.getDownstreamRelationships)

        return downstreamrelationships

    def get_caseteam(self, parentId, sequence):
        ### for certain case, team infortmation can't get by get_team. it needs another way to get.
        result = {}
        team = "Unassigned"
        count = 10
        flag = True
        #original_parentId = parentId
        #if parentId in self.P_caseteams:
        #    team = self.P_caseteams[parentId]
        if len(self.P_caseteams) > 0:
            for key, value in self.P_caseteams.items():
                if sequence.startswith(key):
                    team  = value
                    flag = False

        if flag:
            while count > 1:
                    #new_parantId = result["id"]
                    result = self.rest_api.getResource(resource="items", suffix="/%s/parent"%parentId, \
                        params=None, endless=False, callback=data_reshape.getParent)

                    if len(result) == 0 or count <=1:
                        team = "Unassigned"
                        break
                    elif result["name"] in self.Jamamainteam:
                        team = result["name"]
                        self.P_caseteams[result["sequence"]] = team
                        break
                    elif "." not in result["sequence"]:
                        team = "Unassigned"
                        break
                    else:
                        parentId = result["id"]
                        count = count - 1
            #self.P_caseteams[original_parentId] = team
        self.loghandle.info(self.P_caseteams)
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

    def get_change_designspecs(self, projectId, item_type_id):
        change_designspecs = []
        change_designspecs = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id,"lastActivityDate":str(datetime.now().date()-timedelta(30)) + "T00%3A00%3A00%2B00%3A00&"}, \
            callback=data_reshape.getChangeDesignspecs, endless=True)

        return change_designspecs


    def get_alldesignspecs(self, projectId, item_type_id):
        alldesignspecs = []
        alldesignspecs = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id}, callback=data_reshape.getAllDesignspecs, endless=True)

        return alldesignspecs

    def get_change_userstories(self, projectId, item_type_id):
        change_userstories = []
        change_userstories = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id,"lastActivityDate":str(datetime.now().date()-timedelta(30)) + "T00%3A00%3A00%2B00%3A00&"}, \
            callback=data_reshape.getChangeUserStories, endless=True)

        return change_userstories

    def get_delete_userstories(self, projectId, item_type_id):
        delete_userstories = []
        delete_userstories = self.rest_api.getResource(resource="activities", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id,"eventType":"DELETE","objectType":"ITEM","deleteEvents":"true"}, \
            callback=data_reshape.getDeleteUserStories, endless=True)

        return delete_userstories

    def get_alluserstories(self, projectId, item_type_id):
        alluserstories = []
        alluserstories = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id}, callback=data_reshape.getAllUserStories, endless=True)

        return alluserstories       

    def get_change_defects(self, projectId, item_type_id):
        change_defects = []
        change_defects = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id,"lastActivityDate":str(datetime.now().date()-timedelta(30)) + "T00%3A00%3A00%2B00%3A00&"}, \
            callback=data_reshape.getChangeDefects, endless=True)

        return change_defects

    def get_delete_defects(self, projectId, item_type_id):
        delete_defects = []
        delete_defects = self.rest_api.getResource(resource="activities", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id,"eventType":"DELETE","objectType":"ITEM","deleteEvents":"true"}, \
            callback=data_reshape.getDeleteDefects, endless=True)

        return delete_defects
    
    def get_alldefects(self, projectId, item_type_id):
        alldefects = []
        alldefects = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id}, callback=data_reshape.getAllDefects, endless=True)

        return alldefects  
    
    def get_allrequirements(self, projectId, item_type_id):
        allrequirements = []
        allrequirements = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id}, callback=data_reshape.getAllRequirements, endless=True)

        return allrequirements

    def get_change_requirements(self, projectId, item_type_id):
        allrequirements = []
        allrequirements = self.rest_api.getResource(resource="abstractitems", suffix="", \
            params={"project":projectId,"startAt":0,"maxResults":50,"itemType":item_type_id}, callback=data_reshape.getAllRequirements, endless=True)

        return allrequirements  

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

        for testplanId in self.P_alltests:
            tmp = self.P_alltests[testplanId]["testcases"]
            P_testcases.update(tmp)

        #self.loghandle.info(P_testcases)
        #### get extra information of testcase(status, team, upstream)
        statusId_dict = {k:v["statusId"]  for k, v in P_testcases.items()}
        parentId_dict = {k:[v["parentId"],v["sequence"]]  for k, v in P_testcases.items()}
        testcaseId_list = list(P_testcases.keys())

        for testcaseId, statusId in statusId_dict.items():
            # if statusId not in self.P_picklistoptions:
            status = self.get_picklistoptions(statusId)
            #     self.P_picklistoptions[statusId] = status
            P_testcases[testcaseId]["status"] = status
            # else:
            #     P_testcases[testcaseId]["status"] = self.P_picklistoptions[statusId]

        for testcaseId, itemlist in parentId_dict.items():
            # if parentId not in self.P_caseteams:
            parentId = itemlist[0]
            sequence = itemlist[1]
            team = self.get_caseteam(parentId,sequence)
            #    self.P_caseteams[parentId] = team
            P_testcases[testcaseId]["team"] = team
            # else:
            #     P_testcases[testcaseId]["team"] = self.P_caseteams[parentId]

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
    
    def Get_and_Save(self):
        self.Get_alltests()
        self.Update_db.Store_alltests(self.existing_testplans, self.P_alltests, self.P_testcases)

        #self.Get_allfeatuers()
        #self.Update_db.Store_features(self.P_changefeatures, self.P_deletefeatures, self.P_allfeatures)

        #self.Get_allchangerequests()
        #self.Update_db.Store_allchange_requests(self.P_changerequests, self.P_allchangerequests)

        #self.Get_alldesignspecs()
        #self.Update_db.Store_alldesignspecs(self.P_changedesignspecs, self.P_alldesignspecs)

        #self.Get_alluserstories()
        #self.Update_db.Store_alluserstories(self.P_changeuserstories, self.P_deleteuserstories, self.P_alluserstories)

        #self.Get_alldefects()
        #self.Update_db.Store_alldefects(self.P_changedefects, self.P_deletedefects, self.P_alldefects)

        #self.Get_allrequirements()
        #self.Update_db.Store_allrequirements(self.P_reqcovered, self.P_allrequirements)

        #self.Get_extra_information()

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
        #for testplanId in self.tmp_list:
        for testplanId in self.existing_testplans:
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
    
    def get_futher_information_features(self, maindata):
        result = maindata
        for item in result:
            item["status"] = self.get_picklistoptions(item["statusId"])
        return result

    def Get_allfeatuers(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        feature_type_id = self.getType("feat")
        if "features" in tables:
            self.P_changefeatures =  self.get_change_features(projectId, feature_type_id)
            self.P_deletefeatures = self.get_delete_features(projectId,feature_type_id)
            self.P_changefeatures = self.get_futher_information_features(self.P_changefeatures)
            self.loghandle.info(self.P_changefeatures)
        else:
            self.P_allfeatures = self.get_features(projectId, feature_type_id)
            self.P_allfeatures = self.get_futher_information_features(self.P_allfeatures)
            self.loghandle.info(self.P_allfeatures)
    
    def get_futher_information_changerequests(self, maindata):
        result = maindata
        for item in result:
            item["status"] = self.get_picklistoptions(item["statusId"])
            item["priority"] = self.get_caseteam(item["priorityId"])
        return result

    def Get_allchangerequests(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        change_request_type_id = self.getType("cr")
        if "changes" in tables:
            self.P_changerequests =  self.get_change_requests(projectId, change_request_type_id)
            self.P_changerequests = self.get_futher_information_changerequests(self.P_changerequests)
            self.loghandle.info(self.P_changerequests)
        else:
            self.P_allchangerequests = self.get_allchangerequests(projectId, change_request_type_id)
            self.P_allchangerequests = self.get_futher_information_changerequests(self.P_allchangerequests)
            self.loghandle.info(self.P_allchangerequests)


    def get_futher_information_designspecs(self, maindata):
        result = maindata
        for item in result:
            item["status"] = self.get_picklistoptions(item["statusId"])
            item["team"] = self.get_caseteam(item["parentId"])
        return result

    def Get_alldesignspecs(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        designspecs_type_id = self.getType("fspec")
        if "designspec" in tables:
            self.P_changedesignspecs =  self.get_change_designspecs(projectId, designspecs_type_id)
            self.P_changedesignspecs = self.get_futher_information_designspecs(self.P_changedesignspecs)
        else:
            self.P_alldesignspecs = self.get_alldesignspecs(projectId, designspecs_type_id)
            self.P_alldesignspecs = self.get_futher_information_designspecs(self.P_alldesignspecs)

    def get_futher_information_userstories(self, maindata):
        result = maindata
        for item in result:
            item["status"] = self.get_picklistoptions(item["statusId"])
        return result

    def Get_alluserstories(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        userstories_type_id = self.getType("sty")
        if "userstories" in tables:
            self.P_changeuserstories =  self.get_change_userstories(projectId, userstories_type_id)
            self.P_deleteuserstories = self.get_delete_userstories(projectId, userstories_type_id)
            self.P_changeuserstories = self.get_futher_information_userstories(self.P_changeuserstories)
            self.loghandle.info(self.P_changeuserstories)
        else:
            self.P_alluserstories = self.get_alluserstories(projectId, userstories_type_id)
            self.P_alluserstories = self.get_futher_information_userstories(self.P_alluserstories)
            self.loghandle.info(self.P_alluserstories)


    def get_futher_information_defects(self, maindata):
        result = maindata
        for item in result:
            item["status"] = self.get_picklistoptions(item["statusId"])
            item["team"] = self.get_picklistoptions(item["teamId"])
            item["priority"] = self.get_picklistoptions(item["priorityId"])
            item["upstream"] = self.get_upstreamrelationships(item["id"])
        return result

    def Get_alldefects(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        defects_type_id = self.getType("bug")
        if "defects" in tables:
            self.P_changedefects =  self.get_change_defects(projectId, defects_type_id)
            self.P_deletedefects = self.get_delete_defects(projectId, defects_type_id)
            self.P_changedefects = self.get_futher_information_defects(self.P_changedefects)
            self.loghandle.info(self.P_changedefects)
        else:
            self.P_alldefects = self.get_alldefects(projectId, defects_type_id)
            self.P_alldefects = self.get_futher_information_defects(self.P_alldefects)
            self.loghandle.info(self.P_alldefects)

    def get_futher_information_requirements(self, maindata):
        coveredTeams = ["Industrial Design", "Strategic Alliances", "PM", "PMM"]  # Teams that don't require testcase
        result = maindata
        for req in result:
            testcaseteams = []
            missingTC = ""
            verifyTC = ""
            req["status"] = self.get_picklistoptions(req["statusId"])
            req["downstreamcase_parentlist"] = self.get_downstreamcase_parentlist(req["id"])
            req["upstreamrelationships"] = self.get_upstreamrelationships(req["id"])
            req["downstreamrelationships"] = self.get_downstreamrelationships(req["id"])
            if len(req["teamIdlist"]) > 0:
                req["teamlist"] = self.get_multipicklistoptions(req["teamIdlist"])

            if len(req["downstreamcase_parentlist"]) !=0:
                for parentId in req["downstreamcase_parentlist"]:
                        testcaseteam = self.get_caseteam(parentId)
                        testcaseteams.append(testcaseteam)
                req["downstreamcase_teamlist"] = testcaseteams

            req_mainteams = [item["mainteam"] for item in req["teamlist"]]
            case_mainteams = [item for item in req["downstreamcase_teamlist"]]


            for num,item in enumerate(req["teamlist"]):
                if item["mainteam"] in coveredTeams:
                    req["teamlist"][num]["verified"] = 1
                    break
                if len(item["mainteam"])>0 and item["mainteam"] in case_mainteams:
                    req["teamlist"][num]["verified"] = 1
            
            for item in req["teamlist"]:
                if item["reqteam"] not in self.P_reqcovered:
                    self.P_reqcovered[item["reqteam"]] = {"covered":0, "expected":1}
                else:
                    self.P_reqcovered[item["reqteam"]]["expected"] += 1

                if item["verified"] == 0:
                    missingTC += item["reqteam"] + ", "
                else:
                    verifyTC += item["reqteam"] + ", "
                    self.P_reqcovered[item["reqteam"]]["covered"] += 1


            req["missingTC"] = missingTC[:-2]
            req["verifyTC"] = verifyTC[:-2]


        return result


    def Get_allrequirements(self):
        projectId = self.project["id"]
        requirements_type_id = self.getType("req")
        self.P_allrequirements =  self.get_allrequirements(projectId, requirements_type_id)
        self.P_allrequirements = self.get_futher_information_requirements(self.P_allrequirements)
        self.loghandle.info(self.P_allrequirements)
        self.loghandle.info(self.P_reqcovered)


    # Gets the status of the item depending on the type
    def getStatus(self, statusses, type):
        status = ""

        if (type == "req"):
            if "PASSED" in statusses and "FAILED" not in statusses and "BLOCKED" not in \
                    statusses and "SCHEDULED" not in statusses and "NOT_SCHEDULED" not in statusses:
                status = "PASSED"
            if "FAILED" in statusses and "BLOCKED" not in statusses and "SCHEDULED" \
                    not in statusses and "NOT_SCHEDULED" not in statusses:
                status = "FAILED"
            if "BLOCKED" in statusses:
                status = "INCOMPLETE TESTING"
            if "SCHEDULED" in statusses:
                status = "INCOMPLETE TESTING"
            if "NOT_SCHEDULED" in statusses:
                status = "INCOMPLETE TESTING"
        else:
            if "PASSED" in statusses and "FAILED" not in statusses and "INCOMPLETE TESTING" \
                    not in statusses and "MISSING TEST COVERAGE" not in statusses:
                status = "PASSED"
            if "FAILED" in statusses and "INCOMPLETE TESTING" not in statusses \
                    and "MISSING TEST COVERAGE" not in statusses:
                status = "FAILED"
            if "INCOMPLETE TESTING" in statusses:
                status = "INCOMPLETE TESTING"
            if "MISSING TEST COVERAGE" in statusses:
                status = "MISSING TEST COVERAGE"
        return status

    def Get_extra_information(self):
        tables = self.project["tables"]
        projectId = self.project["id"]
        status_list = ["Passed", "Failed", "Incomplete testing", "Missing Test Coverage"]

        if self.P_allfeatures and self.P_testcases and self.P_allrequirements:

            for f_iteam in self.P_allfeatures:
                all_reqstat = []
                featuresId = f_item["id"]

                all_req = list(filter(lambda x: x["upstreamrelationships"] == featuresId, self.P_allrequirements))
                for req_item in all_req:
                    statusses = []
                    requirementsId = req_item["id"]
                    if len(req_item["missingTC"]) >0:
                        substatus = "MISSING TEST COVERAGE"
                    else:
                        for testcaseId in self.P_testcases:
                            upstream = self.P_testcases[testcaseId]["upstream"]
                            if upstream == featuresId:
                                statusses.append(self.P_testcases[testcaseId]["testCaseStatus"])
                    
                        substatus = self.getStatus(statusses,"req")
                    self.P_allrequirements_test_status.append((substatus.lower(), requirementsId))
                    self.P_requirementsTest.append(("Unspecified", status.lower(), str(datetime.now().date())))
                    all_reqstat.append(substatus)

                status = self.getStatus(all_reqstat, "feat")

                self.P_allfeatures_test_status.append((status.lower(), featuresId))
                self.P_featurestest.append(("Unspecified", status.lower(), str(datetime.now().date())))


        for item in status_list:
            status = item.upper()
            count1 = sum([ 1 if feat[0]==status else 0 for feat in self.P_featurestest])
            self.P_c_featurestest.append(("Unspecified",status, count1, str(datetime.now().date())))
            count2 = sum([ 1 if req[0]==status else 0 for req in self.P_requirementsTest])
            self.P_c_requirementsTest.append(("Unspecified",status, count2, str(datetime.now().date())))
