# Created on Mar 9, 2012
#
# @author: Richard Plevin
# @author: Sam Fendell
# @author: Ryan Jones
#
# Copyright (c) 2012-2015. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.
'''
This module includes contributions by Sam Fendell and Ryan Jones.
'''
from __future__ import print_function
from collections import Iterable
from contextlib import contextmanager
from datetime import datetime
from six import string_types, iteritems, MAXSIZE
from six.moves import xrange
import sys

from sqlalchemy import create_engine, Table, Column, String, Float, text, MetaData, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, load_only
from sqlalchemy.orm.exc import NoResultFound
#from sqlalchemy.pool import QueuePool

from pygcam.config import getSection, getParam, getParamAsBoolean
from pygcam.log import getLogger

from . import util as U
from .constants import RegionMap
from .error import PygcamMcsUserError, PygcamMcsSystemError
from .schema import (ORMBase, Run, Sim, Input, Output, InValue, OutValue, Experiment,
                     Program, Code, Region, TimeSeries)

_logger = getLogger(__name__)

def usingSqlite():
    '''
    Return True if the DbURL indicates that we're using Sqlite, else return False
    '''
    url = getParam('MCS.DbURL')
    return url.lower().startswith('sqlite')

def usingPostgres():
    '''
    Return True if the DbURL indicates that we're using Postgres, else return False
    '''
    url = getParam('MCS.DbURL')
    return url.lower().startswith('postgres')


@event.listens_for(Engine, "connect")
def sqlite_FK_pragma(dbapi_connection, connection_record):
    '''Turn on foreign key support in sqlite'''
    if usingSqlite():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # TODO: might be useful:
    # pd.read_sql_table('data', engine, columns=['Col_1', 'Col_2'])
    # pd.read_sql_table('data', engine, index_col='id')
    # pd.read_sql_table('data', engine, parse_dates=['Date'])
    # pd.read_sql_table('data', engine, parse_dates={'Date': '%Y-%m-%d'})


RegionAliases = {
    'all regions':   'global',
    'rest of world': 'multiple',
    'row':           'multiple'
}

# The name of the program as stored in the "program" table
GCAM_PROGRAM = 'gcam'

# Constants to avoid misspelling errors
DFLT_PROGRAM  = 'default'

# Status strings for Run table
RUN_NEW       = 'new'
RUN_QUEUED    = 'queued'
RUN_RUNNING   = 'running'
RUN_SUCCEEDED = 'succeeded'
RUN_FAILED    = 'failed'
RUN_KILLED    = 'killed'
RUN_ABORTED   = 'aborted'
RUN_ALARMED   = 'alarmed'
RUN_UNSOLVED  = 'unsolved'
RUN_GCAMERROR = 'gcamerror'     # any other GCAM runtime error
ENG_TERMINATE = 'terminate'

RUN_FAILURES  = [RUN_FAILED, RUN_KILLED, RUN_ABORTED, RUN_ALARMED, RUN_UNSOLVED,
                 RUN_GCAMERROR]
RUN_STATUSES  = [RUN_NEW, RUN_QUEUED, RUN_RUNNING, RUN_SUCCEEDED] + RUN_FAILURES


# TBD: maybe drop this and store it from Context instead
def beforeSavingRun(_mapper, _connection, run):
    '''
    Before inserting/updating a Run instance, set numerical status and
    timestamps according to the status string.
    '''
    if run.status in (RUN_NEW, RUN_QUEUED):
        run.queueTime = datetime.now()
        run.startTime = None
        run.endTime   = None
        run.duration  = None
    elif run.status == RUN_RUNNING:
        run.startTime = datetime.now()
        run.endTime   = None
        run.duration  = None
    elif run.startTime:
        run.endTime   = datetime.now()
        delta         = run.endTime - run.startTime
        run.duration  = delta.seconds // 60


# Associate a listener function with Run, to execute before inserts and updates
event.listen(Run, 'before_insert', beforeSavingRun)
event.listen(Run, 'before_update', beforeSavingRun)

def parseSqlScript(filename=None, text=None):
    '''
    Parse a SQL script into semi-colon-terminated statements.

    :param filename: (str) the path of the file of SQL statements
    :param text: (str) optionally pass the contents of the file
      rather than the filename
    :return: (list of str) the individual statements
    '''
    from six.moves import StringIO

    if not (filename or text):
        raise PygcamMcsSystemError('Called parseSqlScript with neither filename nor text')

    if text:
        lines = StringIO(text).readlines()
    else:
        with open(filename) as f:
            lines = f.readlines()

    statements = []
    buffer = ''

    for line in lines:
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        buffer += line
        if buffer[-1] == ';':
            statements.append(buffer)
            buffer = ''
        else:
            buffer += ' '

    return statements

class CoreDatabase(object):

    def __init__(self):
        from sqlalchemy.orm import scoped_session
        factory = sessionmaker() # N.B. sessionmaker returns a class object
        self.Session = scoped_session(factory)

        self.url     = None
        self.engine  = None
        self.appId   = None

    def endSession(self, session):
        '''
        Helper method to handle thread-scoped session objects for use with ipyparallel

        :param session: the open session
        :return: none
        '''
        try:
            self.Session.remove()
        except Exception as e:
            _logger.debug("Can't remove Session: %s", e)
            session.close()

    @contextmanager
    def sessionScope(self, withRetry=True):
        """
        Provide a transactional scope around a series of operations.
        Usage:
           with sessionScope() as session:
        """
        session = self.Session()
        session.expire_on_commit = False

        try:
            yield session
            if withRetry:
                self.commitWithRetry(session)
            else:
                session.commit()
        except:
            session.rollback()
            raise
        finally:
            self.endSession(session)

    # create_engine(*args, **kwargs)
    # The string form of the URL is dialect+driver://user:password@host/dbname[?key=value..],
    # where dialect is a database name such as mysql, oracle, postgresql, etc., and driver
    # the name of a DBAPI, such as psycopg2, pyodbc, cx_oracle, etc.
    # psycopg2: http://www.stickpeople.com/projects/python/win-psycopg/
    #
    # postgres|mysql: engine = create_engine('postgresql://scott:tiger@localhost/mydatabase')
    #
    # sqlite:   engine = create_engine('sqlite:///foo.db') -- if relative pathname, or
    #           engine = create_engine('sqlite:////absolute/path/to/foo.db') if abs pathname.
    #
    # To add a user and database in postgres:
    #    createuser -P mcsuser      # -P => prompt for password
    #    createdb -O mcsuser mcs    # -O => make mcsuser owner of database mcs
    #
    def startDb(self, checkInit=True):
        '''
        Links session to the database file identified in the config file as 'dbfile'.
        This needs to be called before any database operations can occur. It is called
        in getDatabase() when a new database instance is created.
        '''
        url  = getParam('MCS.DbURL')
        echo = getParamAsBoolean('MCS.EchoSQL')

        _logger.info('Starting DB: %s' % url)

        self.createDatabase()

        connect_args = {'connect_timeout': 15} if usingPostgres() else {}

        self.engine = engine = create_engine(url, echo=echo, connect_args=connect_args,
                                             # poolclass=QueuePool
                                             #, pool_pre_ping=True
                                            )
        self.Session.configure(bind=engine)

        self.url = url

        if checkInit:
            # Load metadata from the existing database, not from the ORMBase,
            # to see if the "run" table exists. If not, initialize the DB.
            # We don't do this if calling from Runner.py, which requires that
            # the database be set up already.
            meta = MetaData(bind=engine, reflect=True)
            if 'run' not in meta.tables:
                self.initDb()


    def initDb(self, args=None):
        '''
        Initialize the database, including loading required inserts.
        '''
        _logger.info('Initializing DB: %s' % self.url)

        meta = ORMBase.metadata     # accesses declared tables
        meta.bind = self.engine
        meta.reflect()
        meta.drop_all()

        session = self.Session()
        meta.create_all()
        session.commit()

        if args and args.empty:
            return

        # Deprecated?
        _logger.debug('Adding standard codes')
        # Add standard app status codes
        session.add(Code(codeName=RUN_QUEUED,    description='Trial queued'))
        session.add(Code(codeName=RUN_RUNNING,   description='Trial running'))
        session.add(Code(codeName=RUN_SUCCEEDED, description='Trial succeeded'))
        session.add(Code(codeName=RUN_FAILED,    description='Trial failed'))
        session.add(Code(codeName=RUN_ABORTED,   description='Runtime error'))
        session.add(Code(codeName=RUN_KILLED,    description='System timeout'))
        session.add(Code(codeName=RUN_ALARMED,   description='Runner timeout.'))

        #session.add(Program(name=DFLT_PROGRAM, description='Program name used when none is specified'))
        _logger.debug('Committing standard codes')
        session.commit()

        initialData = [
            ['Program',    [{'name': GCAM_PROGRAM,
                             'description' : 'The GCAM executable program'}]],
        ]

        _logger.debug('Adding initial data')
        for key, value in initialData:
            # If no module is specified with the class name, it is
            # assumed to be in this module, otherwise everything
            # up to the last '.' is treated as the module name
            items     = key.rsplit('.', 1)
            modName   = items[0] if len(items) == 2 else __name__
            className = items[1] if len(items) == 2 else items[0]

            table = className.lower()
            if table in ORMBase.metadata.tables:
                module    = sys.modules[modName]
                dataClass = getattr(module, className)
                if not dataClass:
                    raise PygcamMcsSystemError("Table class %s not found in module %s" % (className, modName))

                for row in value:
                    session.add(dataClass(**row))
                    _logger.debug('committing row')
                    session.commit()                # commit each row so each can refer to prior rows
            else:
                raise KeyError(table)


    def createDatabase(self):
        '''
        Ensure that the database directory (in the case of sqlite3) or the database is available.
        '''
        if usingSqlite():
            # Make sure required directory exists
            dbDir = getParam('MCS.RunDbDir')
            U.mkdirs(dbDir)
            return

        if usingPostgres() and getParam('MCS.Postgres.CreateDbExe'):
            import subprocess, shlex, re
            from .error import PygcamMcsSystemError

            # Make sure required database exists
            dbName   = getSection()
            createdb = getParam('MCS.Postgres.CreateDbExe')
            argStr   = getParam('MCS.Postgres.CreateDbArgs')
            command  = "%s %s" % (createdb, argStr)
            _logger.debug("Trying command: %s" % command)
            args = shlex.split(command)

            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            if not proc:
                raise PygcamMcsSystemError("Could not run: %s" % command)

            status = proc.wait()      # wait for process to complete
            if status == 0:
                _logger.debug("Created postgres database '%s'", dbName)
            else:
                output = list(proc.stdout)
                existsMsg = 'database "%s" already exists' % dbName
                dbExists  = any(map(lambda line: re.search(existsMsg, line), output))

                if not dbExists:
                    raise PygcamMcsSystemError("%s failed: %s" % (command, dbExists))     # fail if unexpected error occurs

                _logger.debug("Postgres database '%s' already exists", dbName)

    def commitWithRetry(self, session, maxTries=10, maxSleep=2.0):
        # N.B. With master/worker architecture, this should no longer be necessary, but
        # there are still occasional failures due to inability to acquire file lock.
        # import sqlite3
        import random
        import time

        tries = 0

        done = False
        while not done:
            try:
                session.commit()
                done = True

            except Exception as e:
            # except sqlite3.OperationalError as e:
                _logger.debug('sqlite3 operational error: %s', e)

                if tries >= maxTries:
                    raise PygcamMcsSystemError("Failed to acquire database lock")

                delay = random.random() * maxSleep    # sleep for a random number of seconds up to maxSleep
                _logger.warn("Database locked (retry %d); sleeping %.1f sec" % (tries, delay))
                time.sleep(delay)
                tries += 1

            # except Exception as e:
            #     raise PygcamMcsSystemError("commitWithRetry error: %s" % e)


    def execute(self, sql):
        'Execute the given SQL string'
        _logger.debug('Executing SQL: %s' % sql)
        with self.sessionScope() as session:
            session.execute(sql)

    def executeScript(self, filename=None, text=None):
        if not (filename or text):
            raise PygcamMcsSystemError('Called executeScript with neither filename nor text')

        lines = parseSqlScript(filename=filename, text=text)

        with self.sessionScope() as session:
            for sql in lines:
                _logger.debug('Executing script SQL: %s' % sql)
                session.execute(sql)

    def dropAll(self):
        '''
        Drop all objects in the database, even those not defined in SqlAlchemy.
        '''
        with self.sessionScope() as session:
            engine  = session.get_bind()

            meta = MetaData(bind=engine)
            meta.reflect()

            if usingPostgres():
                self.dropAllPostgres(meta)
            else:
                meta.drop_all()

    def dropAllPostgres(self, meta):
        """
        Drop all postgres tables and sequences from schema 'public'
        """
        for type in ('table', 'sequence'):
            sql = "select {type}_name from information_schema.{type}s where {type}_schema='public'".format(type=type)
            names = [name for (name, ) in meta.execute(text(sql))]
            for name in names:
                try:
                    meta.execute(text("DROP %s %s CASCADE" % (type, name)))
                except SQLAlchemyError as e:
                    print(e)

    def getTable(self, tableClass, orderBy=None):
        '''
        Get all the contents of a table, optionally ordered by the given column.

        :param tableClass: (SqlAlchemy table class) the table to query
        :param orderBy: (SqlAlchemy table.col spec) optional column to order by
        :return: (list of elements of tableClass) the rows of the table
        '''
        with self.sessionScope() as session:
            query = session.query(tableClass)
            if orderBy:
                query = query.order_by(orderBy)

            rows = query.all()
            return rows

    def setSqlEcho(self, value=True):
        with self.sessionScope() as session:
            engine = session.get_bind()
            engine.echo = value

    def addColumns(self, tableClass, columns):
        '''
        Adds a new column or columns to an existing table, emitting an
        ALTER TABLE statement and updating the metadata.
        :param tableClass: the class defining the table to alter
        :param column: a Column instance describing the column to add
        :return: none
        '''
        if not isinstance(columns, Iterable):
            columns = [columns]

        with self.sessionScope() as session:
            engine  = session.get_bind()
            table   = tableClass.__table__
            tableName  = table.description
            for column in columns:
                table.append_column(column)                     # add it to the metadata
                setattr(tableClass, column.name, column)        # add attribute to class, which maps it to the column
                columnName = column.name                        # column.compile(dialect=engine.dialect)
                columnType = column.type.compile(engine.dialect)
                engine.execute('ALTER TABLE %s ADD COLUMN "%s" %s' % (tableName, columnName, columnType))

    def createOutput(self, name, description=None, program=DFLT_PROGRAM, unit=None, session=None):
        '''
        Create an Output record with the given arguments unless the record
        exists for this name and program. Uses caller's session if provided. If no
        session is provided, the row is committed and the new outputId is returned.
        If the caller passes a session, None is returned unless the object was found,
        in which case the outputId is returned.
        '''
        sess      = session or self.Session()
        programId = self.getProgramId(program)
        outputId  = sess.query(Output.outputId).filter_by(programId=programId, name=name).scalar()

        if outputId is None:
            output = Output(name=name, programId=programId, description=description, units=unit)
            sess.add(output)

            if not session:
                sess.commit()
                self.endSession(sess)
                outputId = output.outputId

        return outputId

    def getOutputIds(self, nameList):
        # cache on first call
        if not self.outputIds:
            with self.sessionScope() as session:
                rows = session.query(Output.name, Output.outputId).all()
                self.outputIds = dict(rows)

        # lookup ids in cache
        ids = [self.outputIds[name] for name in nameList]
        return ids
        # return zip(*ids)[0] if ids else []

    def getOutputs(self):
        rows = self.getTable(Output)
        return [obj.name for obj in rows]

    def getOutputUnits(self, name):
        with self.sessionScope() as session:
            query = session.query(Output.units).filter_by(name=name)
            row = query.one()
            units = row[0] if row else ''
            return units

    def getOutputsWithValues(self, simId, scenario):
        with self.sessionScope() as session:
            query = session.query(Output.name).\
                join(OutValue).join(Run).filter_by(simId=simId).\
                join(Experiment).filter_by(expName=scenario). \
                distinct(Output.name)
            rows = query.all()
            return [row[0] for row in rows]

    #
    # Very much like setAttrVal. So much so that perhaps the Result table can be
    # eliminated in favor of using the generic attribute/value system?
    #
    def setOutValue(self, runId, paramName, value, program=GCAM_PROGRAM, session=None):
        '''
        Set the given named output parameter to the given numeric value. Overwrite a
        previous value for this runId and attribute, if found, otherwise create a new value
        record. If session is not provided, one is allocated, and the transaction is
        committed. If a session is provided, the caller is responsible for calling commit.
        '''
        #_logger.debug('setOutValue(%s, %s, %s, session=%s', runId, paramName, value, session)
        sess = session or self.Session()

        outputId = sess.query(Output.outputId).filter_by(name=paramName).join(Program).filter_by(name=program).scalar()
        if not outputId:
            raise PygcamMcsSystemError("%s output %s was not found in the Output table" % (program, paramName))

        results = sess.query(OutValue).filter_by(runId=runId, outputId=outputId).all()

        # If previous value is found, overwrite it; otherwise create a new one
        if results:
            #_logger.debug("setOutValue: updating value for outputId=%d" % outputId)
            #result = resultQuery.one()
            result = results[0]
            result.value = value
        else:
            #_logger.debug("setOutValue: adding value for outputId=%d" % outputId)
            sess.add(OutValue(runId=runId, outputId=outputId, value=value))

        if session is None:
            self.commitWithRetry(sess)
            self.endSession(sess)

    def getOutValues(self, simId, expName, outputName, limit=None):
        '''
        Return a pandas DataFrame with columns trialNum and name outputName,
        for the given sim, exp, and output variable.
        '''
        from pandas import DataFrame

        session = self.Session()

        limit = MAXSIZE if limit is None or limit <= 0 else limit

        # This is essentially this query, but with "JOIN xx ON" syntax generated:
        #   select r.trialNum, v.value from run r, outvalue v, experiment e, output o
        #   where e.scenario='test exp' and r.expid=e.expid and r.simid=1 and
        #         o.name='p1' and o.outputid=v.outputid;
        query = session.query(Run.trialNum).add_columns(OutValue.value).filter_by(simId=simId).\
        join(Experiment).filter_by(expName=expName).join(OutValue).join(Output).filter_by(name=outputName).\
        order_by(Run.trialNum).limit(limit)

        #print "getOutValues query: %s" % str(query.statement.compile())

        rslt = query.all()
        self.endSession(session)

        if not rslt:
            return None

        resultDF = DataFrame.from_records(rslt, columns=['trialNum', outputName], index='trialNum')
        return resultDF

    def deleteRunResults(self, runId, outputIds=None, session=None):
        sess = session or self.Session()

        query = sess.query(OutValue).filter_by(runId=runId)
        if outputIds:
            query = query.filter(OutValue.outputId.in_(outputIds))

        #query.delete(synchronize_session='fetch')
        query.delete(synchronize_session=False)

        if session is None:
            self.commitWithRetry(sess)
            self.endSession(sess)

    # def queryToDataFrame(self, query):  # TBD: Not used anywhere yet...
    #     from pandas import DataFrame    # lazy import
    #
    #     session = self.Session()
    #     result = session.execute(query)
    #     columnNames = result.keys()
    #     values = result.fetchall()
    #     self.endSession(session)
    #     return DataFrame(values, columns=columnNames)

    def getParameterValues(self, simId, program='gcam', asDataFrame=False):
        from pandas import DataFrame    # lazy import
        session = self.Session()

        query = session.query(InValue.row, InValue.col, InValue.value, InValue.trialNum, Input.paramName).\
                 filter(InValue.simId == simId).join(Input).join(Program).filter(Program.name == program).order_by(InValue.trialNum)

        rslt = query.all()
        cols = [d['name'] for d in query.column_descriptions] if rslt else None
        self.endSession(session)

        if not rslt:
            return None

        if not asDataFrame:
            return rslt

        resultDF = DataFrame.from_records(rslt, columns=cols, index='trialNum')
        return resultDF

    def getParameterValues2(self, simId):
        from pandas import DataFrame    # lazy import
        session = self.Session()

        query = session.query(InValue.trialNum, InValue.value, Input.paramName).\
                 filter(InValue.simId == simId).join(Input).order_by(InValue.trialNum)

        rslt = query.all()
        self.endSession(session)

        if not rslt:
            return None

        cols = ['trialNum', 'value', 'paramName']
        resultDF = DataFrame.from_records(rslt, columns=cols)
        resultDF = resultDF.pivot(index='trialNum', columns='paramName', values='value')
        return resultDF

    def getParameters(self):
        with self.sessionScope() as session:
            query = session.query(Input.paramName, Input.inputId).order_by(Input.inputId)
            rslt = query.all()

        triples = [(name, 0, col-1) for name, col in rslt]
        return triples

    def getInputs(self):
        rows = self.getTable(Input, orderBy=Input.paramName)
        return [row.paramName for row in rows]

    def scenariosWithResults(self, simId):
        # Definition of view 'result':
        # select o."runId", r."simId", r."expId", r."trialNum", e."expName", op.name, o.value
        # from outvalue o, output op, run r, experiment e
        # where e."expId" = r."expId" and o."runId" = r."runId" and o."outputId" = op."outputId"
        try:
            with self.sessionScope() as session:
                query = session.query(Experiment.expName).join(Run).filter_by(simId=simId).\
                    join(OutValue).distinct(Experiment.expName)
                rows = query.all()
                names = [row[0] for row in rows]
        except Exception as e:
            _logger.error("scenariosWithResults failed: %s", e)
            names = []

        _logger.debug("scenariosWithResults returning %s", names)
        return names


    def createRun(self, simId, trialNum, expName=None, expId=None, status=RUN_NEW, session=None):
        """
        Create an entry for a single model run, initially in "new" state
        """
        assert (expName or expId), "Database createRun called with neither expName nor expId"

        sess = session or self.Session()
        if expId is None:
            exp = sess.query(Experiment.expId).filter_by(expName=expName).one()
            expId = exp.expId

        # if prior run record exists for this {simId, trialNum, expId} tuple, delete it
        with session.no_autoflush:
            sess.query(Run).filter_by(simId=simId, trialNum=trialNum, expId=expId).delete()

        run = Run(simId=simId, trialNum=trialNum, expId=expId, status=status, jobNum=None)
        sess.add(run)

        if not session:     # if we created the session locally, commit; else call must do so
            self.commitWithRetry(sess)
            self.endSession(sess)

        return run

    def getSim(self, simId):
        with self.sessionScope() as session:
            sim = session.query(Sim).filter_by(simId=simId).scalar()

            return sim    # N.B. scalar() returns None if no rows are found

    def getSims(self):
        rows = self.getTable(Sim, orderBy=Sim.simId)
        return rows

    def getRun(self, simId, trialNum, expName):
        with self.sessionScope() as session:
            run = session.query(Run).filter_by(simId=simId, trialNum=trialNum).\
                    join(Experiment).filter_by(expName=expName).scalar()

            return run

    def getRunByRunId(self, runId):
        with self.sessionScope() as session:
            run = session.query(Run).filter_by(runId=runId).scalar()
            return run

    def getRunFromContext(self, context):
        run = self.getRun(context.simId, context.trialNum, context.scenario)
        #_logger.debug("getRunIdFromContext returning runId %s", run.runId if run else None)
        return run

    def setRunStatus(self, runId, status, session=None):
        '''
        Set the runStatus to the value for the given string and
        optionally set the job number.'''
        sess = session or self.Session()
        try:
            run = sess.query(Run).filter_by(runId=runId).one()
            if run.status == status:
                return # nothing to do here

            run.status = status    # insert/update listener sets status code and timestamps

            if not session:
                self.commitWithRetry(sess)
            return

        except NoResultFound:
            _logger.warn("db.setRunStatus failed to find record for runId %d", runId)
            return

        finally:
            if not session:
                self.endSession(sess)

    def getRunsWithStatus(self, simId, expList, statusList):
        # Allow expList and statusList to be a single string,
        # which we convert to lists
        if isinstance(expList, string_types):
            expList = [expList]

        if isinstance(statusList, string_types):
            statusList = [statusList]

        session = self.Session()
        query = session.query(Run.trialNum).filter_by(simId=simId)

        if expList:
            query = query.join(Experiment).filter(Run.status.in_(statusList), Experiment.expName.in_(expList))

        rslt = query.order_by(Run.trialNum).all()
        self.endSession(session)

        if rslt:
            rslt = [r[0] for r in rslt] # collapse list of singleton tuples into a single list

        #_logger.debug("for simid=%d, expList=%s, status=%s, rslt=%s" % (simId, expList, status, rslt))
        return rslt

    def getRunsByStatus(self, simId, scenario, statusList, groupName=None, projectName=None):
        '''
        By default, returns tuples of (runId, trialNum) for the given scenario that have
        any of the statuses in statusList (which can be a single status string or a list
        of strings.) If groupName or projectName are not None, results are converted to
        a list of Context instances.
        '''
        from .context import Context

        if isinstance(statusList, string_types):
            statusList = [statusList]

        if len(statusList) == 0:
            return []

        with self.sessionScope() as session:

            # expId = self.getExpId(scenario, session=session)
            # query = session.query(Run.runId, Run.trialNum).filter_by(simId=simId, expId=expId).filter(Run.status.in_(statusList))

            # Return all data required to create Context (except projectName and groupName)
            query = session.query(Run.runId, Run.simId, Run.trialNum, Run.status).filter_by(simId=simId).filter(Run.status.in_(statusList))
            query = query.add_columns(Experiment.expName, Experiment.parent).join(Experiment).filter_by(expName=scenario)

            rslt = query.order_by(Run.trialNum).all()

        if groupName or projectName:
            rslt = [Context(runId=r[0], simId=r[1], trialNum=r[2], status=r[3], scenario=r[4],
                            baseline=r[5], groupName=groupName, projectName=projectName) for r in rslt]
        return rslt

    def createSim(self, trials, description, simId=None):
        '''
        Creates a new simulation with the given number of trials and description
        '''
        with self.sessionScope() as session:
            if simId is None:
                newSim = Sim(trials=trials, description=description)
            else:
                session.query(Sim).filter_by(simId=simId).delete()
                newSim = Sim(trials=trials, description=description, simId=simId)

            session.add(newSim)

        return newSim.simId

    def updateSimTrials(self, simId, trials):
        with self.sessionScope() as session:
           sim = session.query(Sim).filter_by(simId=simId).one()
           sim.trials = trials

    def getTrialCount(self, simId):
        with self.sessionScope() as session:
            trialCount = session.query(Sim.trials).filter_by(simId=simId).scalar()
            return trialCount

    def getMissingTrials(self, simId, scenario):
        """
        Return a list of trial numbers that are not present in the database
        for the given simId and scenario.

        :param simId: (int) simulation ID
        :param scenario: (str) scenario name
        :return: (list of int) trial numbers of missing trials
        """
        count = self.getTrialCount(simId)
        possible = set(xrange(count))

        df = self.getRunInfo(simId, scenario, includeSucceededRuns=True, asDataFrame=True)
        present = set() if df is None else set(df.trialNum)

        missing = possible - present
        return sorted(missing)

    def getRunInfo(self, simId, scenario, includeSucceededRuns=False, asDataFrame=False):
        """
        Return info for runs for the given simId and scenario, as a list of tuples
        or as a pandas.DataFrame.

        :param simId: (int) simulation ID
        :param scenario: (str) scenario name
        :param includeSucceededRuns: (bool) if True, runs of status 'succeeded' are
           included; by default they are not.
        :param asDataFrame: (bool) whether to return the result as a list of tuples
           (the default) or as a DataFrame
        :return:
        """
        from pandas import DataFrame

        with self.sessionScope() as session:
            q = session.query(Run.runId, Run.simId, Run.trialNum, Run.status).\
                    filter_by(simId=simId).join(Experiment).filter_by(expName=scenario)

            if not includeSucceededRuns:
                q = q.filter(Run.status != 'succeeded')

            rows = q.all()
            if asDataFrame:
                if rows:
                    cols = [d['name'] for d in q.column_descriptions]
                    df = DataFrame.from_records(rows, columns=cols, index='runId')
                    return df
                return None

            return rows

    def createExp(self, name, description=None):
        '''
        Insert a row for the given experiment
        '''
        with self.sessionScope() as session:
            exp = Experiment(expName=name, description=description)
            session.add(exp)
            return exp.expId

    def getExpId(self, expName, session=None):
        exp = self.getExp(expName, session)
        return exp.expId

    def getExp(self, expName, session=None, raiseError=True):
        sess = session or self.Session()

        try:
            exp = sess.query(Experiment).filter_by(expName=expName).one()

        except NoResultFound:
            msg = "The experiment '%s' is not defined" % expName
            if raiseError:
                _logger.fatal(msg)
                raise PygcamMcsUserError(msg)
            else:
                _logger.info(msg)
                exp = None

        finally:
            if session:
                self.endSession(session)

        return exp

    def addExperiments(self, scenarioNames, baseline, filename):
        from .error import PygcamMcsSystemError

        desc = 'Added from ' + filename

        for name in scenarioNames:
            parent = None if name == baseline else baseline
            try:
                self.createExp(name, description=desc, parent=parent)

            except Exception as e:
                raise PygcamMcsSystemError("Failed to create experiment: %s" % e)

    def getProgramId(self, program):
        with self.sessionScope() as session:
            programId = session.query(Program.programId).filter_by(name=program).scalar()
            return programId


class GcamDatabase(CoreDatabase):
    _yearColsAdded = False
    _expColsAdded = False

    instance = None     # singleton class

    def __init__(self):
        super(GcamDatabase, self).__init__()
        self.paramIds = {}                   # parameter IDs by name
        self.outputIds = None                # output IDs by name
        self.canonicalRegionMap = {}

        # Cache these to avoid database access in saveResults loop
        for regionName, regionId in RegionMap.items():
            canonName = canonicalizeRegion(regionName)
            self.canonicalRegionMap[canonName] = regionId

    @classmethod
    def getDatabase(cls, checkInit=True):
        if cls.instance is None:
            cls.instance = GcamDatabase()
            cls.instance.startDb(checkInit=checkInit)

        return cls.instance

    @classmethod
    def close(cls):
        if cls.instance:
            cls.instance.engine.dispose()
        cls.instance = None

    def initDb(self, args=None):
        'Add GCAM-specific tables to the database'
        super(GcamDatabase, self).initDb(args=args)

        self.addYearCols()
        self.addExpCols()

        if args and args.empty:
            return

        self.addRegions(RegionMap)

    def startDb(self, checkInit=True):
        super(GcamDatabase, self).startDb(checkInit=checkInit)
        self.addYearCols(alterTable=False)
        self.addExpCols(alterTable=False)

    def createExp(self, name, parent=None, description=None):
        '''
        Insert a row for the given experiment. Replaces superclass method
        to add 'parent' argument. Also, if it fails, updates existing row.
        '''
        from sqlalchemy.exc import IntegrityError

        session = self.Session()
        exp = Experiment(expId=None, expName=name, description=description)
        exp.parent = parent # not in Experiment's __init__ signature

        try:
            session.add(exp)
            session.commit()
            expId = exp.expId

        except IntegrityError:
            session.rollback()
            expId = self.updateExp(name, description=description, parent=parent, session=session)

        finally:
            self.endSession(session)

        return expId

    def updateExp(self, name, parent=None, description=None, session=None):
        sess = session or self.Session()
        exp = self.getExp(name, session=sess)
        exp.description = description
        exp.parent = parent
        sess.commit()

        if not session:
            self.endSession(sess)

        return exp.expId

    def getExp(self, expName, session=None, raiseError=True):
        sess = session or self.Session()

        try:
            exp = sess.query(Experiment).filter_by(expName=expName).one()

        except NoResultFound:
            msg = "The experiment '%s' is not defined" % expName
            if raiseError:
                raise PygcamMcsUserError(msg)
            else:
                _logger.info(msg)
                exp = None

        finally:
            if not session:
                self.endSession(sess)

        return exp

    def getExps(self):
        rows = self.getTable(Experiment, orderBy=Experiment.expName)
        return rows

    # TBD: generalize and add to CoreDatabase since often modified? Or just add to base schema.
    def addExpCols(self, alterTable=True):
        '''
        Add required columns to the Experiment table.
        '''
        if self._expColsAdded:
            return

        session = self.Session()
        engine = session.get_bind()
        meta = ORMBase.metadata
        meta.bind = engine
        meta.reflect()
        expTable = Experiment.__table__

        cols = [('parent', String)]

        for (colName, colType) in cols:
            if colName not in expTable.columns:
                column = Column(colName, colType)
                if alterTable:
                    self.addColumns(Experiment, column)
                else:
                    setattr(Experiment, column.name, column)        # just add the mapping

        self._expColsAdded = True
        self.endSession(session)

    @staticmethod
    def yearCols():
        from .util import activeYears, YEAR_COL_PREFIX

        # Create the time series table with years (as columns) specified in the config file.
        years = activeYears()
        cols = [YEAR_COL_PREFIX + y for y in years]
        return cols

    def addYearCols(self, alterTable=True):
        '''
        Define year columns (y1990, y2005, y2010, etc.) dynamically. If alterTable
        is True, the SQL table is altered to add the column; otherwise the column
        is just mapped to an attribute of the TimeSeries class.
        '''
        if self._yearColsAdded:
            return

        with self.sessionScope() as session:
            engine = session.get_bind()
            meta = ORMBase.metadata
            meta.bind = engine
            meta.reflect()

            colNames = self.yearCols()

            timeSeries = Table('timeseries', meta, autoload=True, autoload_with=engine)

            # Add columns for all the years used in this analysis
            for colName in colNames:
                if colName not in timeSeries.columns:
                    column = Column(colName, Float)
                    if alterTable:
                        self.addColumns(TimeSeries, column)
                    else:
                        setattr(TimeSeries, column.name, column)        # just add the mapping

            self._yearColsAdded = True

    def addRegions(self, regionMap):
        # TBD: read region map from file identified in config file, or use default values
        # For now, use default mapping
        with self.sessionScope() as session:
            for name, regId in iteritems(regionMap):
                self.addRegion(regId, name, session=session)

    def addRegion(self, regionId, name, session=None):
        sess = session or self.Session()
        obj = Region(regionId=regionId, displayName=name, canonName=canonicalizeRegion(name))
        sess.add(obj)

        if session:
            sess.commit()
            self.endSession(sess)

    def getRegionId(self, name):
        canonName = canonicalizeRegion(name)
        regionId = self.canonicalRegionMap[canonName]
        return regionId

    def getParamId(self, pname):
        return self.paramIds[pname]

    def createOutput(self, name, program=GCAM_PROGRAM, description=None, unit=None, session=None):
        _logger.debug("createOutput(%s)", name)
        return super(GcamDatabase, self).createOutput(name, program=program, description=description,
                                                      unit=unit, session=session)

    def saveParameterNames(self, tuples):
        '''
        Define parameter names in the database on the fly based on results of XPath queries.
        "tuples" is a list of (paramName, description) pairs.
        '''
        session = self.Session()
        programId = self.getProgramId(GCAM_PROGRAM)

        # TBD: The following code is subject to a race condition, but we don't expect multiple users to
        # TBD: generate simulations in the same model run dir simultaneously. If they do, this may break.
        # TBD: Could handle this with a lock...
        pnames = [tup[0] for tup in tuples]
        rows = session.query(Input).filter(Input.programId == programId, Input.paramName.in_(pnames)).all()
        found = [row.paramName for row in rows]

        descByName = dict(tuples)
        notFound = set(pnames) - set(found)

        # Construct list of tuples holding only the parameters that were
        # found, and whose description changed. These are updated automatically
        # when the session is committed.
        updTuples = []
        for row in rows:
            desc = descByName[row.paramName]
            if row.description != desc:
                row.description = desc
                updTuples.append(row)

        # Create a list of objects that need to be inserted, then add them all at once
        newInputs = [Input(programId=programId, paramName=name, description=descByName[name]) for name in notFound]
        session.add_all(newInputs)

        # Insert new parameter descriptions for these
        session.commit()

        # Cache all parameter IDs for faster lookup
        rows = session.query(Input.inputId, Input.paramName).all()
        for row in rows:
            self.paramIds[row.paramName] = row.inputId

        self.endSession(session)

    def saveParameterValues(self, simId, tuples):
        '''
        Save the value of the given parameter in the database. Tuples are
        of the format: (trialNum, paramId, value, varNum)
        '''
        with self.sessionScope() as session:
            for trialNum, paramId, value, varNum in tuples:
                # We save varNum to distinguish among independent values for the same variable name.
                # The only purpose this serves is to ensure uniqueness, enforced by the database.
                inValue = InValue(inputId=paramId, simId=simId, trialNum=trialNum,
                                  value=value, row=0, col=varNum)
                session.add(inValue)

    def deleteRunResults(self, runId, outputIds=None, session=None):
        """
        Augment core method by deleting timeseries data, too.
        """
        # _logger.debug("deleteRunResults: deleting results for runId %d, outputIds=%s" % (runId, outputIds))
        sess = session or self.Session()
        super(GcamDatabase, self).deleteRunResults(runId, outputIds=outputIds, session=sess)

        query = sess.query(TimeSeries).filter_by(runId=runId)

        if outputIds:
            query = query.filter(TimeSeries.outputId.in_(outputIds))

        query.delete(synchronize_session='fetch')

        if session is None:
            self.commitWithRetry(sess)
            self.endSession(sess)

    def saveTimeSeries(self, runId, regionId, paramName, values, units=None, session=None):
        sess = session or self.Session()

        programId = self.getProgramId(GCAM_PROGRAM)

        # one() raises error if 0 or more than 1 row is found, otherwise returns a tuple.
        try:
            row = sess.query(Output).filter(Output.programId == programId, Output.name == paramName).one()
        except Exception:
            _logger.error("Can't find param %s for %s", paramName, GCAM_PROGRAM)
            raise

        outputId = row.outputId

        ts = TimeSeries(runId=runId, outputId=outputId, regionId=regionId, units=units)

        for name, value in iteritems(values):  # Set the values for "year" columns
            setattr(ts, name, value)

        sess.add(ts)

        if not session:
            sess.commit()
            self.endSession(sess)

    def getTimeSeries(self, simId, paramName, expList):
        '''
        Retrieve all timeseries rows for the given simId and paramName.

        :param simId: simulation ID
        :param paramName: name of output parameter
        :param expList: (list of str) the names of the experiments to select
           results for.
        :return: list of TimeSeries tuples or None
        '''
        cols = ['seriesId', 'runId', 'outputId', 'units'] + self.yearCols()

        with self.sessionScope() as session:
            query = session.query(TimeSeries, Experiment.expName).options(load_only(*cols)). \
                join(Run).filter_by(simId=simId).filter_by(status='succeeded'). \
                join(Experiment).filter(Experiment.expName.in_(expList)). \
                join(Output).filter_by(name=paramName)

            rslt = query.all()
            return rslt


# Single instance of the class. Use 'getDatabase' constructor
# to ensure that this instance is returned if already created.
_DbInstance = None

def getDatabase(checkInit=True):
    '''
    Return the instantiated CoreDatabase, or created one and return it.
    The optional dbClass argument is provided to facilitate subclassing.
    '''
    return GcamDatabase.getDatabase(checkInit=checkInit)

def dropTable(tableName, meta):
    if tableName in meta.tables:
        # Drop the table if it exists and remove it from the metadata
        table = meta.tables[tableName]
        table.drop()
        meta.remove(table)

def canonicalizeRegion(name):
    '''
    Return the canonical name for a region, normalizing the use of capitalization
    and underscores.

    :param name: a GCAM region name
    :return: region name in canonical format, i.e., lowercase with underscores
       changed to spaces. (The use of underscores is inconsistent and thus hard
       to remember, e.g., 'South America_Northern')
    '''
    name = name.lower()
    if name in RegionAliases:
        name = RegionAliases[name]

    return name.replace('_', ' ')
