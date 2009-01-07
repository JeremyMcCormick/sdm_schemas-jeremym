#!/usr/bin/env python

from administerRuns import AdminRuns
from mysqlBase import MySQLBase
import MySQLdb
import subprocess

gDb = "GlobalDB4cleanupTest"
dcV = "DC3a"
hostN = "localhost" # mysql server host name

# dummy mysql users + passwords
u1 = "dummy1"
p1 = "pwd1"
u2 = "dummy2"
p2 = "pwd2"


maxNIter = 30


def dropDB():
    admin = MySQLBase(hostN)
    admin.connect("becla", "")
    admin.execCommand0("DROP DATABASE IF EXISTS " + gDb)
    for n in range(1, maxNIter):
        admin.execCommand0("DROP DATABASE IF EXISTS %s_%s_u_myRun_%02i" % (u1, dcV, n))
        admin.execCommand0("DROP DATABASE IF EXISTS %s_%s_u_myRun_%02i" % (u2, dcV, n))

def createDummyUserAccounts():
    """
    This function makes sure the dummy user accounts required by this test
    program exist. In normal operations, these accounts should already exist
    prior to running anything.
    """
    cmd = "../scripts/addMySqlUser.py -f dummy -s localhost -u %s -p %s -e %s@x.com -c localhost -g %s -v %s" % (u1, p1, u1, gDb, dcV)
    print cmd
    subprocess.call(cmd.split())
    cmd = "../scripts/addMySqlUser.py -f dummy -s localhost -u %s -p %s -e %s@x.com -c localhost -g %s -v %s" % (u2, p2, u2, gDb, dcV)
    print cmd
    subprocess.call(cmd.split())


dropDB()

# one connection per user
a1 = AdminRuns(hostN, # mysql host
              gDb)   # global db name
a2 = AdminRuns(hostN, # mysql host
              gDb)   # global db name


# create global db
a1.setupGlobalDB("globalDBPolicy.txt")


createDummyUserAccounts()


a1.checkStatus("perRunDBPolicy.txt", 
               u1,     # non-superuser
               p1,     # password
               hostN)  # machine where mysql client is executed

a2.checkStatus("perRunDBPolicy.txt", 
               u2,     # non-superuser
               p2,     # password
               hostN)  # machine where mysql client is executed


b = MySQLBase(hostN)

bSU = MySQLBase(hostN)
bSU.connect("becla", "", gDb)


outLogFile = open("./_cleanup.log", "w")

# u1 starts regularly one run per day, extend a couple of runs
# u2 starts regularly one run every 3 days
for n in range(1, maxNIter):
    print "\n\n************** doing ", n, " **************\n"
    a1.prepareForNewRun("perRunDBPolicy.txt", "myRun_%02i"%n,  "u", u1, p1)

    # manually adjust the run start time, notice, have to run as su
    bSU.execCommand0("""
      UPDATE RunInfo 
      SET startDate = ADDTIME("2008-05-01 15:00:00", "%i 00:00:00"),
          expDate   = ADDTIME("2008-05-14 15:00:00", "%i 00:00:00")
      WHERE runName = 'myRun_%02i' 
        AND initiator = '%s'
""" % (n, n, n, u1))
    # If it is May 18, extend 5th run
    if n == 18:
        b.connect(u1, p1, gDb)
        b.execCommand0("SELECT extendRun('myRun_05', '%s', '%s')" % (dcV, u1))
        b.disconnect()
    # If it is May 19 extend 15th run
    if n == 19:
        b.connect(u1, p1, gDb)
        b.execCommand0("SELECT extendRun('myRun_15', '%s', '%s')" % (dcV, u1))
        b.disconnect()

    if n % 3 == 1:
        a2.prepareForNewRun("perRunDBPolicy.txt", "myRun_%02i"%n,  "u", u2, p2);

    # manually adjust the run start time
    bSU.execCommand0("""
      UPDATE RunInfo 
      SET startDate = ADDTIME("2008-05-01 15:00:00", "%i 00:00:00"),
          expDate   = ADDTIME("2008-05-14 15:00:00", "%i 00:00:00")
      WHERE runName = 'myRun_%02i' 
        AND initiator = '%s'

""" % (n, n, n, u2))

    a2.connect(u2, p2, gDb)

    print "Currently have:"
    res = a2.execCommandN("SELECT * FROM RunInfo")
    for r in res:
        print r

    print "\n\n******** now running cleanup script **********\n"

    cmd = "../scripts/cleanupExpiredRuns.py f -d 2008-05-%i -g %s" %\
        (n, gDb)
    print "calling ", cmd
    subprocess.call(cmd.split(), stdout=outLogFile)


outLogFile.close()