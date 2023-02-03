""" Common REST API functions for JAMA

Description: This file includes common REST API functions for JAMA

Author:         jackie
Created:        11-11-2020
Updated:
Updated by:
Copyright:      (c) Jabra 2020

Update Notes:

-------------------------------------------------------------------------------
"""
import sys
import json
import requests
#from data_reshape import data_reshape
from datetime import datetime, timedelta


class api_calls:
    """ 
        Common class for Jama api calls

        Jama api calls 

        Refer: https://jabra.jamacloud.com/api-docs/#/
        Jama api include these components:
        abstractitems, activities, files, attachments, baselines, comments
        filters, itemtypes, items, picklists, picklistoptions, projects, relationshiprulesets
        relationshiptypes, relationships, releases, system, tags, testcycles, testplans, testruns
        testruns, usergroups, users
    """

    def __init__(self, username=None, password=None, baseurl=None, G_parameter=None, loghandle=None):
        """ 
            Initialization method 
            Parameters:
                param1 - this parameter for jama username
                param2 - this parameter for jama password
                param3 - this parameter for jama baseurl
                param3 - this parameter is from config file(config.ini)
                        G_paramter:{
                            "General":{"username":xxx,"password":xxx,...},
                            "projects":{"getProjects":xxx,...}
                            ...
                        }
            Priority : username:password > G_parameter 
        """
        if G_parameter is not None:
            self.G_parameter = G_parameter
            self.username = self.G_parameter['General']['jamausername']
            self.password = self.G_parameter['General']['jamapassword']
            self.baseurl = self.G_parameter['General']['baseurl']
            self.Retry = int(self.G_parameter['General']['netretry'])
            self.loghandle = loghandle
        else:
            self.username = username
            self.password = password
            self.baseurl = baseurl
            self.Retry = 5
            self.loghandle = loghandle
    
    def Print(self, message, flag="info"):
        if self.loghandle is None:
            print(flag+": "+message)
        else:
            if flag in ["info", "INFO", "I", "i"]:
                self.loghandle.info(message)
            elif flag in ["error", "Error", "E", "e"]:
                self.loghandle.error(message)

    def httpget(self, url, auth=None):
        retry_count = 0
        response = None
        while retry_count < self.Retry:
            try:
                response = requests.get(url, auth=auth)
                if response.status_code == 200:
                    break
                else:
                    retry_count = retry_count + 1
                    response = None
            except Exception as e:
                self.Print(e,flag="Error")
                #retry = retry + 1
                #response = None
        if response is None and retry_count == self.Retry:
            pass
            #self.Print("Can't url:%s get response, network error or parameter error, retry count = %s"%(url, str(self.Retry)),flag='Error')
        #print(url)
        return response

    def combine(self, purl, params):
        """ 
            Discription: 
                Combine the url and query param
            Parameters:
                param1 - this is jama pre-ready url, http://xxxx
                param2 - this is a query dict , for example:
                        params:{
                            "startAt":0,"maxResults":10
                        }
            Returns:
                https:xxx?startAt=0&maxResults=10
        """
        list_params = list(params.items())
        query = ""

        for i, (k, v) in enumerate(list_params):
            if i != len(list_params) - 1:
                query = query + str(k) + "=" + str(v) + "&"
            else:
                query = query + str(k) + "=" + str(v)

        url = purl + "?" + query
        return url

    def getResource(self, resource, suffix, params=None, complete_url=None, endless=False, callback=None):
        """ 
            Discription: 
                    Function used to get resource
                    use the base_url
            Parameters:
                param1 - query parameter, dict, such as:
                        {"startAt":0,"maxResults":10}
                param2 - endless mode. if True, it will fetch all data
            Returns:
                rawdatas
        """
        rawmeta = {}
        rawdatas = []

        if complete_url is None:
            purl = self.baseurl + resource + suffix
        else:
            purl = complete_url 

        if endless == False:
            if params is not None:
                url = self.combine(purl, params)
            else:
                url = purl
            #self.Print(url+":start")
            response = self.httpget(url, auth=(self.username, self.password))
            if response is not None:
                json_response = json.loads(response.text)
                # Processing data side of response
                if "data" in json_response:
                    rawdatas = json_response["data"]
                if "meta" in json_response:
                    rawmeta = json_response["meta"]
                #self.Print(url+":succesful")
        else:
            while True:
                url = self.combine(purl, params)
                #self.Print(url+":start")
                response = self.httpget(url, auth=(self.username, self.password))
                if response is None:
                    break
                json_response = json.loads(response.text)

                page_info = json_response["meta"]["pageInfo"]
                resultCount = page_info["resultCount"]
                totalResults = page_info["totalResults"]
                startIndex = page_info["startIndex"] + resultCount
                params['startAt'] = startIndex

                # Processing data side of response
                json_response_data = json_response["data"]
                rawdatas = rawdatas + json_response_data
                #self.Print(url+":succesful")
                if startIndex >= totalResults:
                    break
        if callback is None:
            return rawdatas,rawmeta
        else:
            return callback(rawdatas,rawmeta)


    def NewgetTestCases(self, resource, test_plan_id, test_group_id, params = {"startAt":0,"maxResults":50}, endless=True, callback=None):
        """ Function to get test case info for a test group in a test plan """
        purl = self.baseurl + resource + "/%s/"%(test_plan_id) + "testgroups/%s/testcases"%(test_group_id)
        rawdatas = []

        while True:
                url = self.combine(purl, params)
                self.Print(url+":start")
                response = self.httpget(url, auth=(self.username, self.password))
                if response is None:
                    break
                json_response = json.loads(response.text)

                page_info = json_response["meta"]["pageInfo"]
                resultCount = page_info["resultCount"]
                totalResults = page_info["totalResults"]
                startIndex = page_info["startIndex"] + resultCount
                params['startAt'] = startIndex

                # Processing data side of response
                json_response_data = json_response["data"]
                rawdatas = rawdatas + json_response_data
                #self.Print(url+":succesful")
                if startIndex >= totalResults:
                    break

        if callback is None:
            return rawdatas
        else:
            return callback(test_group_id, rawdatas)

