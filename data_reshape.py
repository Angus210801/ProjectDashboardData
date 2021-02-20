import re
"""
	Discription

"""
class data_reshape:
    

    @classmethod              
    def getProjects_reshape(cls, raw_datas, rawmeta):
        """
            raw_datas example:
                "data": [{
                "id": 20186,
                "projectKey": "AP",
                "parent": 20247,
           	    "isFolder": false,
                "createdDate": "2010-07-21T16:59:20.000+0000",
                "modifiedDate": "2016-08-08T12:34:39.000+0000",
                "createdBy": 16217,
                "modifiedBy": 18361,
                "fields": {
                    "projectKey": "AP",
                    "statusId": 156666,
                    "text1": "",
                    "name": "Agile Project",
                    "description": "This is an Agile project template.  This template contains the Sets most often used in an Agile project.",
                    "date2": "2010-07-20",
                    "projectGroup": 156424,
                    "date1": "2010-07-20"
            	},
                "type": "projects"
                }]
		"""
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for project in raw_datas:
                result.append({"name": str(project["fields"]["name"]), "id": project["id"], "statusId": project["fields"]["statusId"]})
                #result.append({project["id"]:{"name": str(project["fields"]["name"]), "status": project["fields"]["statusId"]}})
        return result

    @classmethod
    def getItemTypes_reshape(cls, raw_datas, rawmeta):
        result = []
        # Saving only ID, display name and type key
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item_type in raw_datas:
                result.append({"id":item_type["id"],"name":item_type["display"],"type_key":item_type["typeKey"]})
        return result

    @classmethod
    def getStatus_reshape(cls, raw_datas, rawmeta):
        """
            raw_datas example
            "data": {
                "id": 156421,
                "name": "Active",
                "description": "",
                "value": "",
                "active": true,
                "archived": false,
                "sortOrder": 2,
                "pickList": 89046,
                "default": true,
                "type": "picklistoptions"
            }
        """
        result = ""
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            result = raw_datas["name"]
        return result

    @classmethod
    def getPicklistOptions(cls, raw_datas, rawmeta):
        result = ""
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            result = raw_datas["name"]
        return result

    @classmethod
    def getParent(cls, raw_datas, rawmeta):
        result = {}
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            result = {
                        "id":raw_datas["id"],
                        "name":raw_datas["fields"]["name"],
                        "sequence":raw_datas["location"]["sequence"]
                    }
        return result

    @classmethod
    def getUpstreamRelationships(cls, raw_datas, rawmeta):
        result = ""
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                result += str(item["fromItem"]) + ", "
            result = result[:-2]
        return result

    @classmethod
    def getDownstreamCaseParentList(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                if "TC" in item["documentKey"]: ## ensure it is testcase
                    result.append(item["location"]["parent"]["item"]) ## store testcase parent id
        return result


    @classmethod
    def getDownstreamRelationships(cls, raw_datas, rawmeta):
        result = ""
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                result += str(item["toItem"]) + ", "
            result = result[:-2]
        return result

    @classmethod
    def getTestPlans(cls, raw_datas, rawmeta):
        result = {}
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for test_plan in raw_datas:
                test_plan_name = str(re.sub('[^\w\-_\. ]', "", test_plan["fields"]["name"]))
                index =  str(test_plan["id"]) + ":" + test_plan_name
                result[test_plan["id"]] = {
                    "id": test_plan["id"],
                    "name": test_plan_name,
                    "archived": test_plan["archived"],
                    "index":index
                }
        return result

    @classmethod
    def getTestCycles(cls, raw_datas, rawmeta):
        result = {}
        if len(raw_datas) == 0:
             print("raw_datas is None")
        else:
            for test_cycle in raw_datas:
                test_cycle_name = str(re.sub('[^\w\-_\. ]', "", test_cycle["fields"]["name"]))
                index = str(test_cycle["id"]) + ":" + test_cycle_name
                result[test_cycle["id"]] = {
                    "id": test_cycle["id"],
                    "name": test_cycle_name,
                    "index": index
                }

        return result

    @classmethod
    def getTestGroups(cls, raw_datas, rawmeta):
        print(raw_datas)
        result = {}
        if len(raw_datas) == 0:
             print("raw_datas is None")
        else:
            for test_group in raw_datas:
                test_group_name = test_group["name"]
                index = str(test_group["id"]) + ":" + test_group_name
                result[test_group["id"]] = {
                    "id": test_group["id"],
                    "name": test_group_name,
                    "index": index
                }

        return result

    @classmethod
    def getTestRunsByTestplan_all(cls, raw_datas, rawmeta):
        totalResults = 0
        if len(rawmeta) == 0:
             print("rawmeta is None")
        else:
            totalResults = rawmeta["pageInfo"]["totalResults"]
        return totalResults

    @classmethod
    def getTestCases(cls, raw_datas, rawmeta):
        result = {}
        #test_cases = {}
        if len(raw_datas) == 0:
             print("raw_datas is None")
        else:
            for test_case in raw_datas:
                #test_cases[test_case["id"]] = test_case
                test_case_name = str(re.sub('[^\w\-_\. ]', "", test_case["fields"]["name"]))
                if "test_case_approval_status$89011" in test_case["fields"]:
                    statusId = test_case["fields"]["test_case_approval_status$89011"]
                else:
                    statusId = ""

                result[test_case["id"]] = {
                    "id": test_case["id"],
                    "name":test_case_name,
                    "parentId":test_case["location"]["parent"]["item"],
                    "sequence":test_case["location"]["sequence"],
                    "documentKey":test_case["documentKey"],
                    "globalId":test_case["globalId"],
                    "createdDate":test_case["createdDate"],
                    "modifiedDate":test_case["modifiedDate"],
                    "lastActivityDate":test_case["lastActivityDate"],
                    "testCaseStatus":test_case["fields"]["testCaseStatus"],
                    "testRunResults":test_case["fields"]["testRunResults"],
                    "statusId":statusId,
                    ###these information need to fecth data from jama again 
                    "status":"",
                    "team":"",
                    "upstream":""
                }
        #result = {"testgroup":test_group_id,"testcases":test_cases}

        return result

    @classmethod
    def getTestRunsByTestplan_sub(cls, raw_datas, rawmeta):
        result = {}
        executionDate = 0
        if len(raw_datas) == 0:
             print("raw_datas is None")
        else:
            for test_run in raw_datas:
                test_run_name = str(re.sub('[^\w\-_\. ]', "", test_run["fields"]["name"]))

                if "executionDate" in test_run["fields"]:
                    executionDate = test_run["fields"]["executionDate"]
                index = str(test_run["id"]) + ":" + test_run_name

                result[test_run["id"]] = {
                    "id":test_run["id"],
                    "name":test_run_name,
                    "executionDate":executionDate,
                    "createdDate":test_run["createdDate"],
                    "testplanId":test_run["fields"]["testPlan"],
                    "testcycleId":test_run["fields"]["testCycle"],
                    "testRunStatus":test_run["fields"]["testRunStatus"],
                    "testgroupId":test_run["testGroup"],
                    "testcaseId":test_run["fields"]["testCase"],
                    "index":index,
                    ###these information need to fecth data from jama again
                    "testplanname":"",
                    "testcyclename":"",
                    "testgroupname":"",
                    "testcasename":"",
                    "testcasedocumentKey":"",
                    "testcasestatus":"",
                    "testcaseteam":"",
                    "testcaseupstream":"",
                    "valid":True
                }

        return result

    @classmethod
    def getFeatures(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for feature in raw_datas:
                result.append({"id":feature["id"], "name":feature["fields"]["name"], "documentKey":feature["documentKey"], "statusId":feature["fields"]["status"], "status":""})
        return result

    @classmethod
    def getChangeFeatures(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for feature in raw_datas:
                result.append({"id":feature["id"], "name":feature["fields"]["name"], "documentKey":feature["documentKey"], "statusId":feature["fields"]["status"], "status":""})
        return result

    @classmethod
    def getDeleteFeatures(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for feature in raw_datas:
                result.append({"id":feature["id"], "date":feature["date"], "item":feature["item"], "objectType":feature["objectType"], "action":feature["action"]})
        return result

    @classmethod
    def getChangeRequests(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                if "string1" in item["fields"]:
                    req = item["fields"]["string1"]
                else:
                    req = "Unassigned"
                result.append({"id":item["id"], "name":item["fields"]["name"], "documentKey":item["documentKey"], "statusId":item["fields"]["status"], "status":"","priorityId":item["fields"]["priority"],"priority":"","req":req})
        return result

    @classmethod
    def getAllChangeRequests(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                if "string1" in item["fields"]:
                    req = item["fields"]["string1"]
                else:
                    req = "Unassigned"
                result.append({"id":item["id"], "name":item["fields"]["name"], "documentKey":item["documentKey"], "statusId":item["fields"]["status"], "status":"","priorityId":item["fields"]["priority"],"priority":"","req":req})
        return result

    @classmethod
    def getChangeDesignspecs(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                result.append({"id":item["id"], "name":item["fields"]["name"], "documentKey":item["documentKey"], "statusId":item["fields"]["status"], "parentId":item["location"]["parent"]["item"], "status":"", "team":""})
        return result

    @classmethod
    def getAllDesignspecs(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                result.append({"id":item["id"], "name":item["fields"]["name"], "documentKey":item["documentKey"], "statusId":item["fields"]["status"], "parentId":item["location"]["parent"]["item"], "status":"", "team":""})
        return result

    @classmethod
    def getChangeUserStories(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                result.append(item)
        return result

    @classmethod
    def getDeleteUserStories(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for userstories in raw_datas:
                result.append({"id":userstories["id"]})
        return result       

    @classmethod
    def getAllUserStories(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                result.append({"id":item["id"], "name":item["fields"]["name"], "documentKey":item["documentKey"], "statusId":item["fields"]["status"],  "status":""})
        return result


    @classmethod
    def getDeleteDefects(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for defects in raw_datas:
                result.append({"id":defects["id"]})
        return result     

    @classmethod
    def getChangeDefects(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                if "jink_to_jira$89012" in item["fields"]:
                    jira = item["fields"]["jink_to_jira$89012"]
                result.append({"id":item["id"], "name":item["fields"]["name"], "documentKey":item["documentKey"], \
                                "statusId":item["fields"]["status"],  "status":"", "teamId":item["fields"]["responsible_function$89012"], "team":"",\
                                "priorityId":item["fields"]["priority"], "priority":"","upstream":"","jira":jira})
        return result

    @classmethod
    def getAllDefects(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item in raw_datas:
                if "jink_to_jira$89012" in item["fields"]:
                    jira = item["fields"]["jink_to_jira$89012"]
                result.append({"id":item["id"], "name":item["fields"]["name"], "documentKey":item["documentKey"], \
                                "statusId":item["fields"]["status"],  "status":"", "teamId":item["fields"]["responsible_function$89012"], "team":"",\
                                "priorityId":item["fields"]["priority"], "priority":"","upstream":"","jira":jira})
        return result

    @classmethod
    def getAllRequirements(cls, raw_datas, rawmeta):
        result = []
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            #teamIdlist = []
            for item in raw_datas:
                teamIdlist = []
                if "verifying_teams_new$89009" in item["fields"]:
                    teamIdlist = item["fields"]["verifying_teams_new$89009"]
                result.append({"id":item["id"], \
                                "name":item["fields"]["name"], \
                                "documentKey":item["documentKey"], \
                                "statusId":item["fields"]["status"], \
                                "status":"", \
                                "teamIdlist":teamIdlist, \
                                "teamlist":[], \
                                "upstreamrelationships":"", \
                                "downstreamrelationships":"", \
                                "downstreamcase_parentlist":[],\
                                "downstreamcase_teamlist":[],
                                "missingTC":"",
                                "verifyTC":""})
        return result