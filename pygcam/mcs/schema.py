from datetime import datetime
from sqlalchemy import (Column, Integer, String, Float, Boolean,
                        ForeignKey, DateTime, UniqueConstraint, Index)
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from pygcam.log import getLogger

_logger = getLogger(__name__)

#
# Object-relational mapping; defines database tables
#
ORMBase = declarative_base()

class CoreMCSMixin(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

class Code(CoreMCSMixin, ORMBase):
    #codeId      = Column(Integer, primary_key=True, autoincrement=False)
    codeName    = Column(String(15), primary_key=True)
    description = Column(String(256))

# TBD: add parent here so it doesn't need to be kludged in later
class Experiment(CoreMCSMixin, ORMBase):
    expId       = Column(Integer, primary_key=True)
    expName     = Column(String(30))
    description = Column(String(256))
    __table_args__ = (Index("experiment_index1", "expName", unique=True),)


class Input(CoreMCSMixin, ORMBase):
    __table_args__ = (UniqueConstraint('programId', 'paramName'),)

    inputId     = Column(Integer, primary_key=True)
    programId   = Column(Integer, ForeignKey('program.programId', ondelete="CASCADE"))
    paramName   = Column(String)
    description = Column(String, nullable=True)


# TBD: add a variableNumber column to be used in cases like GCAM that aren't matrix oriented?
class InValue(CoreMCSMixin, ORMBase):
    inputId  = Column(Integer, ForeignKey('input.inputId', ondelete="CASCADE"), primary_key=True)
    simId    = Column(Integer, ForeignKey('sim.simId', ondelete="CASCADE"), primary_key=True)
    trialNum = Column(Integer, primary_key=True)
    row      = Column(Integer, primary_key=True)    # TBD: drop?
    col      = Column(Integer, primary_key=True)    # TBD: drop?
    value    = Column(Float)
    __table_args__ = (Index("invalue_index1", "inputId", unique=False),)


class Output(CoreMCSMixin, ORMBase):
    outputId    = Column(Integer, primary_key=True)
    programId   = Column(Integer, ForeignKey('program.programId', ondelete="CASCADE"))
    name        = Column(String)
    timeseries  = Column(Boolean, default=False)    # TBD: use this!
    description = Column(String, nullable=True)
    units       = Column(String, nullable=True)


class OutValue(CoreMCSMixin, ORMBase):
    outputId = Column(Integer, ForeignKey('output.outputId', ondelete="CASCADE"), primary_key=True)
    runId    = Column(Integer, ForeignKey('run.runId', ondelete="CASCADE"), primary_key=True)
    value    = Column(Float)

# deprecated
class Program(CoreMCSMixin, ORMBase):
    programId   = Column(Integer, primary_key=True)
    name        = Column(String)
    description = Column(String, nullable=True)


class Run(CoreMCSMixin, ORMBase):
    runId     = Column(Integer, primary_key=True)
    simId     = Column(Integer, ForeignKey('sim.simId', ondelete="CASCADE"))
    expId     = Column(Integer, ForeignKey('experiment.expId', ondelete="CASCADE"))
    trialNum  = Column(Integer)
    jobNum    = Column(String,   nullable=True)
    queueTime = Column(DateTime, default=datetime.now)
    startTime = Column(DateTime, nullable=True)
    endTime   = Column(DateTime, nullable=True)
    duration  = Column(Integer,  nullable=True)
    status    = Column(String,   nullable=True)
    __table_args__ = (Index("run_index1", "simId", "trialNum", "expId", unique=True),)

class Sim(CoreMCSMixin, ORMBase):
    simId       = Column(Integer, primary_key=True)
    trials      = Column(Integer)
    description = Column(String, nullable=True)
    stamp       = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# Map region numbers to region names. Both ids and names must be unique.
class Region(CoreMCSMixin, ORMBase):
    regionId = Column(Integer, primary_key=True, autoincrement=False)
    canonName = Column(String)        # canonical name for lookup (lowercase, "_" changed to " ")
    displayName = Column(String)        # display name
    __table_args__ = (Index("region_index1", "canonName", unique=True),)


class TimeSeries(CoreMCSMixin, ORMBase):
    '''
    N.B. Columns representing the years of interest are added dynamically as
    "y2005", "y2010", etc.
    '''
    seriesId = Column(Integer, primary_key=True)
    runId = Column(Integer, ForeignKey('run.runId', ondelete="CASCADE"))
    regionId = Column(Integer, ForeignKey('region.regionId', ondelete="CASCADE"))
    outputId = Column(Integer, ForeignKey('output.outputId', ondelete="CASCADE"))
    units = Column(String)
