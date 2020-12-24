
"""
	Discription

"""
class data_reshape:
    

    @classmethod              
    def getProjects_reshape(cls, raw_datas):
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
    def getItemTypes_reshape(cls, raw_datas):
        result = []
        # Saving only ID, display name and type key
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for item_type in raw_datas:
                result.append({"id":item_type["id"],"name":item_type["display"],"type_key":item_type["typeKey"]})
        return result

    @classmethod
    def getStatus_reshape(cls, raw_datas):
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
    def getTestPlans(cls, raw_datas):
        result = {}
        if len(raw_datas) == 0:
            print("raw_datas is None")
        else:
            for test_plan in raw_datas:
                result[test_plan["id"]] = {"name": str(re.sub('[^\w\-_\. ]', "", test_plan["fields"]["name"])),
                                                    "id": test_plan["id"], "archived": test_plan["archived"]}
        return result