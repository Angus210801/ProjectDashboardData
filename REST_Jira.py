import os
import sqlite3 as lite
import sys
import timeit
from datetime import datetime
import mysql
import mysql.connector
from jira import JIRA

# set working directory
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

# Basic Jira login information
user = 'extalin@jabra.com'
apikey = 'lK0sW0VoDt5J2P5bnYrpCE48'
server = 'https://jabra1.atlassian.net'

options = {
 'server': server
}

jira = JIRA(options, basic_auth=(user,apikey) )

jsondata = {}
metadatafields = {}


def checkFolder():
    if not os.path.exists("logs"):
        os.makedirs("logs")
    if not os.path.exists("db"):
        os.makedirs("db")
    if not os.path.exists("db/jira/"):
        os.makedirs("db/jira/")


# Check the status of the project by exucuting a JQL
def checkStatus(project):
    status = jira.search_issues("project='%s' AND updated > -12w" % project.key)
    if not status:
        status = "Inactive"
        logData("Project %s is inactive" % project.key)
    else:
        status = "Active"
        logData("Project %s is active" % project.key)
    project.status = status
    project.jama = 0


# Get the various meta data and save them under targetbuilds
def queryJiraMeta(project):
    # Fetch the metadata
    jsonmeta = jira.createmeta(projectKeys='%s' % project.key, projectIds=None, issuetypeIds=None, issuetypeNames=None, expand="projects.issuetypes.fields")
    for k in jsonmeta["projects"]:
        aissuetype = {}
        for l in k["issuetypes"]:
            afields = {}
            akeys = list(l["fields"])
            for m in akeys:
                if l["fields"][m]["name"] == "Target Build":
                    afields["TargetBuild"] = m
            aissuetype[l["name"]] = afields
        metadatafields[k["key"]] = aissuetype

# Create query and fetch 100 issues at a time
def queryJira(project):
    issues = []
    block_size = 100
    block_num = 0
    while True:
        start_idx = block_num * block_size
        temp = jira.search_issues("project='%s'" % project.key, startAt='%s' % start_idx, maxResults='%s' % block_size)
        issues += temp
        if len(temp) == 0:  # Retrieve issues until there are none left
            break
        block_num += 1

    # Get Jama Link by going through the issues
    foundProject = {}
    for issue in issues:
        foundlink = issue.fields.customfield_11402
        if foundlink is not None:
            if "jama" in foundlink:
                found = (foundlink.split("projectId=", 1)[1])[:5]
            else:
                continue
            if found not in foundProject:
                foundProject[found] = 1
            else:
                foundProject[found] += 1

            if foundProject[found] > 5:  # If ID is repeated more than 5 times, then save and break
                project.jama = int(found)
                break
        else:
            project.jama = 0
            logData("Failed.")
    # Process the remaining data
    jsondata[project.key] = issues
    storeData(project)

# Process SQL & HTML generation
def storeData(project):
    con = lite.connect("db/jira/%s.db" % project.key)  # Stores each project in their given database
    if project.jama > 0:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="jabra2020",
            database=str(project.jama)
        )

        crsr = mydb.cursor()
    with con:
        c = con.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS jirasessions (date TEXT)")
        c.execute("DROP TABLE IF EXISTS rawjiradata")
        c.execute("CREATE TABLE IF NOT EXISTS rawjiradata (jirasession_id INT, key TEXT, name TEXT, type TEXT, targetbuild TEXT, createddate INT, status TEXT, labels TEXT, priority TEXT, team TEXT, jama TEXT, jamaid TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS jirastatus (jirasession_id INT, type TEXT, targetbuild TEXT, status TEXT, labels TEXT, priority TEXT, team TEXT, date TEXT, count INT)")
        c.execute("DELETE FROM jirastatus WHERE date='{0}'".format(str(datetime.now().date())))
        c.execute("DELETE FROM jirasessions WHERE date='{0}'".format(str(datetime.now().date())))
        c.execute("INSERT INTO jirasessions (date) VALUES ('{0}')".format(str(datetime.now().date())))
        try:
            c.execute("ALTER TABLE jirastatus ADD COLUMN priority TEXT")
        except:
            pass

        #Get the latest run id
        rowid = c.execute("SELECT max(rowid) as rowid FROM jirasessions").fetchone()[0]

        # insert_into_rawjiradata
        for issue in jsondata[project.key]:
            try:
                team = issue.fields.customfield_11500.value
            except AttributeError:
                team = "Unassigned"

            try:
                targetbuildname = issue.fields.customfield_10600.name
            except AttributeError:
                targetbuildname = "Unspecified"

            if hasattr(issue.fields, 'labels'):
                labelobj = issue.fields.labels
                if labelobj:
                    labels = labelobj[0]
                    if not labels == "PDP":
                        labels = labels
                else:
                    labels = "Other"
            if project.jama > 0 and issue.fields.issuetype.name == "Bug":
                try:
                    crsr.execute("SELECT id, uniqueid from alldefects WHERE jira LIKE %s", ("%" + str(issue.key) + "%",))
                    data = crsr.fetchone()
                    mydb.close()
                except:
                    data = None
                if data is None:
                    jama = "0"
                    jamaid = "0"
                else:
                    jama = data[1]
                    jamaid = data[0]
            else:
                jama = "0"
                jamaid = "0"
            priority = issue.fields.priority.name if issue.fields.priority else ""
            createdate = str(issue.fields.created).split("T")[0]
            c.execute("INSERT INTO rawjiradata (jirasession_id, key, name, type, targetbuild, createddate, status, labels, priority, team, jama, jamaid) values (?,?,?,?,?,?,?,?,?,?,?,?)",
                (rowid, issue.key, issue.fields.summary, issue.fields.issuetype.name, targetbuildname, createdate, issue.fields.status.name, labels, priority, team, jama, jamaid))

        # insert into jirastatus
        c.execute("INSERT INTO jirastatus (jirasession_id, type, targetbuild, status, labels, priority, team, date, count) SELECT jirasession_id, type, targetbuild, status, labels, priority, team, ? as date, count(rowid) as count FROM rawjiradata WHERE jirasession_id=? GROUP BY targetbuild, type, status, labels, priority, team ORDER BY targetbuild",
            (str(datetime.now().date()), rowid))

        # commit and close db
        con.commit()

# Save projects in db
def saveProjects():

    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="jabra2020",
        database="projects"
    )
    c = mydb.cursor(buffered=True)

    alt = list()
    c.execute("SELECT * FROM projects WHERE status = 'Active' AND jama != 0")
    myresult = c.fetchall()
    for project in myresult:
        alt.append(project[0])

    c.execute("CREATE TABLE IF NOT EXISTS projects (keyy TEXT, name TEXT, status TEXT, jama INT)")
    for project in projects:
        if project.key in alt:

            val = (project.key, project.name, project.status, project.jama)
            if project.key not in alt:
                c.execute("INSERT INTO projects (keyy, name, status, jama) VALUES (%s, %s, %s, %s)",val)

            c.execute("SELECT jama FROM projects WHERE keyy='{0}'".format(project.key))
            existingjama = c.fetchone()[0]
            if existingjama == 0 and project.jama != 0:
                c.execute("UPDATE projects SET jama=? WHERE keyy=?", (project.jama, project.key))

    mydb.commit()
    mydb.close()

def logData(log):
    print(log)
    file = open("logs/" + datetime.now().strftime('log_%d_%m_%Y.log'), "a+")
    file.write(datetime.now().strftime('%H:%M:%S') + " [JIRA]: " + log + "\n")
    file.close()

# Main program
if __name__ == '__main__':
    start_time = timeit.default_timer()
    checkFolder()
    logData("Processing all projects from Jira")
    status = ""
    rowid = 0

    # Fetch projects from Jira
    projects = jira.projects()
    logData("Total projects fetched: %s" % len(projects))

    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="jabra2020",
        database="projects"
    )

    c = mydb.cursor()
    alt = list()
    c.execute("SELECT * FROM projects WHERE status = 'Active' AND jama != 0")
    myresult = c.fetchall()
    for project in myresult:
        alt.append(project[0])
    c.close()
    mydb.close()

    # Check the project status
    for project in projects:
        if project.key in alt:
            logData("Checking status for " + project.name + "")
            checkStatus(project)
            logData("Done checking status for " + project.name + "")
            logData("Processing data for " + project.name + "")
            logData("Fetching periods for " + project.name + "")
            project.periods = jira.project_versions(project.key)
            logData("Fetching meta for " + project.name + "")
            queryJiraMeta(project)
            logData("Fetching data for " + project.name + "")
            queryJira(project)
    logData("Saving projects in db")
    saveProjects()
    elapsed = timeit.default_timer() - start_time
    logData("Done fetching & parsing data from Jira. Elapsed time: %s" % elapsed)