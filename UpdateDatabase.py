from datetime import datetime, timedelta
from Mysqlconn import Mysqlconn

from utils import MyLogger,MyConfigParser


class UpdateDatabase:

    def __init__(self, project, jama_itemtypes, G_parameter, loghandle):
        self.project = project
        self.jama_itemtypes = jama_itemtypes
        self.G_parameter = G_parameter

        self.loghandle = loghandle

        self.mydb = Mysqlconn(
            host = self.G_parameter['General']['mysqlhost'],
            user = self.G_parameter['General']['mysqluser'],
            passwd = self.G_parameter['General']['mysqlpassword'],
            database = str(self.project["id"]),
            loghandle = self.loghandle
        )
        self.dbenable = self.mydb.connect()

    def Store_alltests(self, existing_testplans, P_alltests, P_testcases):
        if self.dbenable:
            self.update_database_testruns(P_alltests)
            self.update_database_tests(existing_testplans)
            self.update_database_testapproval(P_testcases)
        else:
            self.loghandle.info("DB is not ready!!!")

    def Store_features(self, P_changefeatures, P_deletefeatures, P_allfeatures):
        if self.dbenable:
            self.update_database_features(P_changefeatures, P_deletefeatures, P_allfeatures)
        else:
            self.loghandle.info("DB is not ready!!!")
    
    def Store_allchange_requests(self, P_changerequests, P_allchangerequests):
        if self.dbenable:
            self.update_database_allchange_requests(P_changerequests, P_allchangerequests)
        else:
            self.loghandle.info("DB is not ready!!!")

    def Store_alldesignspecs(self, P_changedesignspecs, P_alldesignspecs):
        if self.dbenable:
            self.update_database_alldesignspecs(P_changedesignspecs, P_alldesignspecs)
        else:
            self.loghandle.info("DB is not ready!!!")

    def Store_alluserstories(self, P_changeuserstories, P_deleteuserstories,  P_alluserstories):
        if self.dbenable:
            self.update_database_alluserstories(P_changeuserstories, P_deleteuserstories, P_alluserstories)
        else:
            self.loghandle.info("DB is not ready!!!")

    def Store_alldefects(self, P_changedefects, P_deletedefects, P_alldefects):
        if self.dbenable:
            self.update_database_alldefects(P_changedefects, P_deletedefects, P_alldefects)
        else:
            self.loghandle.info("DB is not ready!!!")

    def Store_allrequirements(self, P_reqcovered, P_allrequirements):
        if self.dbenable:
            self.update_database_allrequirements(P_reqcovered, P_allrequirements)
        else:
            self.loghandle.info("DB is not ready!!!")


    def update_database_tests(self, existing_testplans):
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


    def update_database_testruns(self, P_alltests):
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

        for testplanId in P_alltests:
            testruns = P_alltests[testplanId]["testruns"]
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
    
    def update_database_testapproval(self, P_testcases):
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

        for testcaseId in P_testcases:
            case  =  P_testcases[testcaseId]
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



    def update_database_features(self,P_changefeatures, P_deletefeatures, P_allfeatures):
        allfeatures_list = []
        change_allfeatures_list = []
        delete_allfeatures_list = []

        create_features_cmd = "CREATE TABLE IF NOT EXISTS features (\
                                rel TEXT, status TEXT, count INT, date TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        insert_features_cmd = "INSERT INTO features (rel, status, count, date) \
                                SELECT rel, status, count((@rn := @rn + 1)) as count, '{0}' as date FROM allfeatures cross join (select @rn := 0) const GROUP BY rel, status".format(str(datetime.now().date()))
        delete_features_cmd = "DELETE FROM features WHERE date='{0}'".format(str(datetime.now().date()))

        create_allfeatures_cmd = "CREATE TABLE IF NOT EXISTS allfeatures (\
                                id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT,test_status TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_allfeatures_cmd = "DELETE FROM allfeatures WHERE id=%d"
        insert_allfeatures_cmd = "INSERT INTO allfeatures (id, uniqueid, name, status, rel) VALUES (%s, %s, %s, %s, %s)"
        
        self.mydb.execute(create_features_cmd, rollback=False)
        self.mydb.execute(create_allfeatures_cmd, rollback=False)
        self.mydb.execute(delete_features_cmd, rollback=False)
        
        if len(P_allfeatures) > 0:
            for item in P_allfeatures:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified")
                allfeatures_list.append(val)
        else:
            for item in P_changefeatures:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified")
                change_allfeatures_list.append(val)

            for item in P_deletefeatures:
                delete_allfeatures_list.append(item["id"])
            for item in P_changefeatures:
                delete_allfeatures_list.append(item["id"])

        if len(P_allfeatures) > 0:
            self.mydb.executemany(insert_allfeatures_cmd, allfeatures_list)
        else:
            for item in delete_allfeatures_list:
                self.mydb.execute(delete_allfeatures_cmd%(item))
            self.mydb.executemany(insert_allfeatures_cmd, change_allfeatures_list)

        self.mydb.execute(insert_features_cmd)
        self.mydb.db_commit()


    def update_database_allchange_requests(self, P_changerequests, P_allchangerequests):
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
        if len(P_allchangerequests) >0:
            for item in P_allchangerequests:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["priority"], item["req"])
                insert_many.append(val)
        else:
            for item in P_changerequests:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["priority"], item["req"]) 
                insert_many.append(val)
                self.mydb.execute(delete_allchanges_cmd%(item["id"]), rollback=False)

        self.mydb.executemany(insert_allchanges_cmd, insert_many)
        self.mydb.db_commit()
        self.mydb.execute(insert_changes_cmd, rollback=False)
        self.mydb.db_commit()

    def update_database_alldesignspecs(self, P_changedesignspecs, P_alldesignspecs):
        create_designspecs_cmd = "CREATE TABLE IF NOT EXISTS designspec (\
                            rel TEXT, team TEXT, status TEXT, count INT, date text) ENGINE=InnoDB DEFAULT CHARSET=utf8"

        delete_designspecs_cmd = "DELETE FROM designspec WHERE date='{0}'".format(str(datetime.now().date()))
        insert_designspecs_cmd = "INSERT INTO designspec (rel, team, status, count, date) SELECT rel, team, status, count((@rn := @rn + 1)) as count, '{0}' as date FROM alldesignspec cross join (select @rn := 0) const GROUP BY rel, team, status".format(str(datetime.now().date()))

        create_alldesignspecs_cmd = "CREATE TABLE IF NOT EXISTS alldesignspec ( \
                            id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT, team TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"

        delete_alldesignspecs_cmd = "DELETE FROM alldesignspec WHERE id=%d"
        insert_alldesignspecs_cmd = "INSERT INTO alldesignspec (id, uniqueid, name, status, rel, team) VALUES (%s, %s, %s, %s, %s, %s)"

        self.mydb.execute(create_designspecs_cmd, rollback=False)
        self.mydb.execute(create_alldesignspecs_cmd, rollback=False)
        self.mydb.execute(delete_designspecs_cmd, rollback=False)

        insert_many = []
        if len(P_alldesignspecs) >0:
            for item in P_alldesignspecs:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["team"])
                insert_many.append(val)
        else:
            for item in P_changedesignspecs:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["team"]) 
                insert_many.append(val)
                self.mydb.execute(delete_alldesignspecs_cmd%(item["id"]), rollback=False)

        self.mydb.executemany(insert_alldesignspecs_cmd, insert_many)
        self.mydb.db_commit()
        self.mydb.execute(insert_designspecs_cmd, rollback=False)
        self.mydb.db_commit()

    def update_database_alluserstories(self, P_changeuserstories, P_deleteuserstories, P_alluserstories):
        alluserstories_list = []
        change_userstories_list = []
        delete_userstories_list = []
        create_userstories_cmd = "CREATE TABLE IF NOT EXISTS userstories ( \
                rel TEXT, status TEXT, count INT, date TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"

        delete_userstories_cmd = "DELETE FROM userstories WHERE date='{0}'".format(str(datetime.now().date()))
        insert_userstories_cmd = "INSERT INTO userstories (rel, status, count, date) SELECT rel, status, count((@rn := @rn + 1)) as count, '{0}' as date FROM alluserstories cross join (select @rn := 0) const GROUP BY rel, status".format(str(datetime.now().date()))

        create_alluserstories_cmd = "CREATE TABLE IF NOT EXISTS alluserstories ( \
                id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_allusertories_cmd = "DELETE FROM alluserstories WHERE id = %d"
        insert_allusertories_cmd = "INSERT INTO alluserstories (id, uniqueid, name, status, rel) VALUES (%s, %s, %s, %s, %s)"


        self.mydb.execute(create_userstories_cmd, rollback=False)
        self.mydb.execute(create_alluserstories_cmd, rollback=False)
        self.mydb.execute(delete_userstories_cmd, rollback=False)


        if len(P_alluserstories) > 0:
            for item in P_alluserstories:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified")
                alluserstories_list.append(val)
        else:
            for item in P_changeuserstories:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified")
                change_userstories_list.append(val)

            for item in P_deleteuserstories:
                delete_userstories_list.append(item["id"])
            for item in P_changeuserstories:
                delete_userstories_list.append(item["id"])

        if len(P_alluserstories) > 0:
            self.mydb.executemany(insert_allusertories_cmd, alluserstories_list)
        else:
            for item in delete_userstories_list:
                self.mydb.execute(delete_allusertories_cmd%(item))
            self.mydb.executemany(insert_allusertories_cmd, change_userstories_list)

        self.mydb.execute(insert_userstories_cmd)
        self.mydb.db_commit()

    def update_database_alldefects(self, P_changedefects, P_deletedefects, P_alldefects):
        alldefects_list = []
        change_defects_list = []
        delete_defects_list = []
        create_defects_cmd = "CREATE TABLE IF NOT EXISTS defects ( \
                    rel TEXT, team TEXT, status TEXT, priority TEXT, count INT, date TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_defects_cmd = "DELETE FROM defects WHERE date='{0}'".format(str(datetime.now().date()))
        insert_defects_cmd = "INSERT INTO defects (rel, team, status, count, date, priority) SELECT rel, team, status, count((@rn := @rn + 1)) as count, '{0}' as date, priority FROM alldefects cross join (select @rn := 0) const GROUP BY rel, team, status, priority".format(str(datetime.now().date()))


        create_alldefects_cmd = "CREATE TABLE IF NOT EXISTS alldefects ( \
                    id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT, team TEXT, priority TEXT, jira TEXT, upstream TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_alldefects_cmd = "DELETE FROM alldefects WHERE id = %d"
        insert_alldefects_cmd = "INSERT INTO alldefects (id, uniqueid, name, status, rel, team, priority, jira, upstream) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"

        self.mydb.execute(create_defects_cmd, rollback=False)
        self.mydb.execute(create_alldefects_cmd, rollback=False)
        self.mydb.execute(delete_defects_cmd, rollback=False)

        if len(P_alldefects) > 0:
            for item in P_alldefects:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["team"], item["priority"], item["jira"], item["upstream"])
                alldefects_list.append(val)
        else:
            for item in P_changedefects:
                val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified")
                change_defects_list.append(val)

            for item in P_deletedefects:
                delete_defects_list.append(item["id"])
            for item in P_changedefects:
                delete_defects_list.append(item["id"])

        if len(P_alldefects) > 0:
            self.mydb.executemany(insert_alldefects_cmd, alldefects_list)
        else:
            for item in delete_defects_list:
                self.mydb.execute(delete_alldefects_cmd%(item))
            self.mydb.executemany(insert_alldefects_cmd, change_defects_list)

        self.mydb.execute(insert_defects_cmd)
        self.mydb.db_commit()

    def update_database_allrequirements(self, P_reqcovered, P_allrequirements):
        allrequirements_list = []
        allcoverage_list = []
        coverage_list = []
        create_requirements_cmd = "CREATE TABLE IF NOT EXISTS requirements (\
                        rel TEXT, status TEXT, count INT, date TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"

        delete_requirements_cmd = "DELETE FROM requirements WHERE date='{0}'".format(str(datetime.now().date()))
        insert_requirements_cmd = "INSERT INTO requirements (rel, status, count, date) SELECT rel, status, count((@rn := @rn + 1)) as count, '{0}' as date FROM allrequirements cross join (select @rn := 0) const GROUP BY rel, status".format(str(datetime.now().date()))

        create_allrequirements_cmd = "CREATE TABLE IF NOT EXISTS allrequirements (\
                        id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT, upstream TEXT, downstream TEXT, team TEXT, test_status TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"

        drop_allrequirements_cmd = "DROP TABLE IF EXISTS allrequirements"
        insert_allrequirements_cmd = "INSERT INTO allrequirements (id, uniqueid, name, status, rel, upstream, downstream,team) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        update_allrequirements_cmd = "UPDATE allrequirements SET team = %s WHERE id = %s"

        create_allcoverage_cmd = "CREATE TABLE IF NOT EXISTS allcoverage (\
                        id INT, uniqueid TEXT, name TEXT, status TEXT, rel TEXT, verify TEXT, missing TEXT) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        
        drop_allcoverage_cmd = "DROP TABLE IF EXISTS allcoverage"
        insert_allcoverage_cmd = "INSERT INTO allcoverage (id, uniqueid, name, status, rel, verify, missing) VALUES (%s,%s,%s,%s,%s,%s,%s)"

        create_coverage_cmd = "CREATE TABLE IF NOT EXISTS coverage (\
                        team text, covered int, expected int, date text) ENGINE=InnoDB DEFAULT CHARSET=utf8"
        delete_coverage_cmd = "DELETE FROM coverage WHERE date='{0}'".format(str(datetime.now().date()))
        insert_coverage_cmd = "INSERT INTO coverage (team, covered, expected, date) VALUES (%s,%s,%s,%s)"

        self.mydb.execute(drop_allrequirements_cmd, rollback=False)
        self.mydb.execute(drop_allcoverage_cmd, rollback=False)
        
        self.mydb.execute(create_requirements_cmd, rollback=False)
        self.mydb.execute(create_allrequirements_cmd, rollback=False)
        self.mydb.execute(create_coverage_cmd, rollback=False)
        self.mydb.execute(create_allcoverage_cmd, rollback=False)

        self.mydb.execute(delete_requirements_cmd, rollback=False)
        self.mydb.execute(delete_coverage_cmd, rollback=False)

        if len(P_allrequirements) > 0:
            for item in P_allrequirements:
                allreq_val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["upstreamrelationships"], item["downstreamrelationships"], item["verifyTC"])
                allcoverage_val = (item["id"], item["documentKey"], item["name"], item["status"], "Unspecified", item["verifyTC"], item["missingTC"] )
                allrequirements_list.append(allreq_val)
                allcoverage_list.append(allcoverage_val)

        self.mydb.executemany(insert_allrequirements_cmd, allrequirements_list)
        self.mydb.db_commit()
        self.mydb.executemany(insert_allcoverage_cmd, allcoverage_list)
        self.mydb.db_commit()

        self.mydb.execute(insert_requirements_cmd)
        self.mydb.db_commit()

        if len(P_reqcovered):
            for item in P_reqcovered:
                val = (item, P_reqcovered[item]["covered"], P_reqcovered[item]["expected"], str(datetime.now().date()))
                coverage_list.append(val)
            self.mydb.executemany(insert_coverage_cmd, coverage_list)  
        self.mydb.db_commit()

