# -*- coding: utf-8 -*-
"""DINO 2.1 network data"""

from __future__ import annotations

from datetime import timedelta, date
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, ForeignKeyConstraint, CheckConstraint, and_, case, select, func
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import relationship, RelationshipProperty, joinedload
from sqlalchemy.sql import ClauseElement
from time import mktime
from typing import Optional, Sequence, TYPE_CHECKING

from ..types import DinoDate, DinoTimeDelta, IntEnum
from . import Base, Version

if TYPE_CHECKING:
    from .location import Stop, StopPoint
    from .operational import Branch, Operator, OperatorBranchOffice, MeansOfTransportDesc, VehicleDestinationText
    from .schedule import Trip, TripVDT


class BikeRule(Enum):
    no_bicycle = -1
    vvs_rail = 0
    vvs_cityrail = 1
    mvv = 2
    db = 3
    gvh = 4
    ivb = 5
    tfl = 6
    vvs_end = 7
    always_allowed = 8
    regulated_per_journey = 9


class Course(Base):
    """
    Course ("line variant")

    A course is a specific combination of `CourseStop`s of a whole line.  
    There is no model class for a whole "line" (collection of `Course`s with the same `Course.line`).

    Primary key: `version_id` & `line` & `id` & `line_dir`
    """
    _din_file = "line.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    branch_id: Column[int] = Column("BRANCH_NR", Integer(), primary_key=False, nullable=False)
    """Branch id"""

    line: Column[int] = Column("LINE_NR", Integer(), primary_key=True)
    """Line id"""

    # nullable=True weggelassen.
    id: Column[str] = Column("STR_LINE_VAR", String(length=4), primary_key=True)
    """Course id"""

    name: Column[Optional[str]] = Column("LINE_NAME", String(length=40))
    """
    Published line name / number  
    (has to be equal for all `Course`s with the same `Course.line`)
    """

    # nullable=True weggelassen.
    line_dir: Column[int] = Column("LINE_DIR_NR", Integer(), CheckConstraint("LINE_DIR_NR in (1, 2)"), primary_key=True)
    """Line direction (1 or 2)"""

    last_mod: Column[Optional[str]] = Column("LAST_MODIFIED", String(length=20))
    """Last modified timestamp"""

    mot_id: Column[Optional[int]] = Column("MOT_NR", Integer())
    """
    Means of transport description id  
    (has to be equal for all `Course`s with the same `Course.line`)
    """

    valid_from: Column[Optional[date]] = Column("VALID_FROM", DinoDate)
    """Valid from date"""
    valid_to: Column[Optional[date]] = Column("VALID_TO", DinoDate)
    """Valid until date"""

    operator_id: Column[Optional[str]] = Column("OP_CODE", String(length=10))
    """Operator id"""
    operator_branch_office_id: Column[Optional[str]] = Column("OBO_SHORT_NAME", String(length=10))
    """Operator branch office id"""

    type: Column[Optional[int]] = Column("ROUTE_TYPE", Integer())
    """Route type (used with export of round trips)"""

    global_id: Column[Optional[str]] = Column("GLOBAL_ID", String(length=100))
    """DLID / global unique identifier of the line"""

    bike_rule: Column[Optional[BikeRule]] = Column("BIKE_RULE", IntEnum(BikeRule), info={'keep_minus_1': True})
    """Bicycle transport rules"""

    branch: RelationshipProperty[Branch] = relationship("Branch", viewonly=True)
    """`DINO2.model.operational.Branch`"""
    mot: RelationshipProperty[Optional[MeansOfTransportDesc]] = relationship("MeansOfTransportDesc", viewonly=True)
    """`DINO2.model.operational.MeansOfTransportDesc`"""
    operator: RelationshipProperty[Optional[Operator]] = relationship("Operator", viewonly=True)
    """`DINO2.model.operational.Operator`"""
    operator_branch_office: RelationshipProperty[Optional[OperatorBranchOffice]] = relationship("OperatorBranchOffice", viewonly=True)
    """`DINO2.model.operational.OperatorBranchOffice`"""
    stops: RelationshipProperty[Sequence[CourseStop]] = relationship("CourseStop", order_by="asc(CourseStop.consec_stop_nr)", back_populates="course")
    """`CourseStop`s of this course"""
    stop_timings: RelationshipProperty[Sequence[CourseStopTiming]] = relationship("CourseStopTiming", order_by="asc(CourseStopTiming.consec_stop_nr)", viewonly=True)
    """`CourseStopTiming`s of this course"""
    trips: RelationshipProperty[Sequence[Trip]] = relationship("Trip", viewonly=True)
    """`DINO2.model.schedule.Trip`s of this course"""
    trip_vdt_changes: RelationshipProperty[Sequence[TripVDT]] = relationship("TripVDT", order_by="asc(TripVDT.consec_stop_nr)", viewonly=True)
    """Trip vehicle destination text changes (`DINO2.model.schedule.TripVDT`) of this course"""
    vdts: RelationshipProperty[Sequence[VehicleDestinationText]] = relationship("VehicleDestinationText", order_by="asc(TripVDT.consec_stop_nr)", secondary="trip_vdt", viewonly=True)
    """`DINO2.model.operational.VehicleDestinationText`s used on this course"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="courses")
    """`DINO2.model.Version`"""

    @hybrid_property
    def length(self) -> int:
        """Get route length in m"""
        return sum(s.length for s in self.stops if s.length is not None)

    @length.expression
    def length(cls) -> ClauseElement:
        return select([func.sum(CourseStop.length)]).where(CourseStop.course.expression & (CourseStop.length != None)).label("length")

    @property
    def wkt(self) -> str:
        """Get WKT (well known text) representation of course"""
        text = "MULTILINESTRING ("
        from .location import Link
        for (s_f, s_t) in zip(self.stops, self.stops[1:]):
            link = self._session.query(Link).options(joinedload('geometry')).filter(and_(Link.from_point == s_f.stop_point, Link.to_point == s_t.stop_point)).one()
            # ...? falls link nicht gefunden.
            text += f"{link.wkt[11:]}, "
        return text[:-2] + ")"

    def wkt_m(self, timing_group: int, start_timedelta: Optional[timedelta] = None, start_day: Optional[date] = None) -> str:
        """Get WKT (well known text) representation with time measures for a timing group, optionally with specific start time&day"""
        text = "MULTILINESTRING M ("
        timings = tuple(filter(lambda t: t.timing_group == timing_group, self.stop_timings))
        assert len(timings) == len(self.stops)
        currenttime = start_timedelta or timedelta()

        def ts(td: timedelta) -> int:
            return (int(mktime(start_day.timetuple())) if start_day is not None else 0) + int(td.total_seconds())

        from .location import Link
        for from_timing, to_timing, s_f, s_t in zip(timings, timings[1:], self.stops, self.stops[1:]):
            # todo: time_to_stop None..
            currenttime += from_timing.time_to_stop + from_timing.stopping_time
            link = self._session.query(Link).options(joinedload('geometry')).filter(and_(Link.from_point == s_f.stop_point, Link.to_point == s_t.stop_point)).one()
            # ...? falls link nicht gefunden.
            text += f"{link.wkt_m(ts(currenttime), ts(currenttime + to_timing.time_to_stop))[13:]}, "
        return text[:-2] + ")"

    @hybrid_method
    def duration(self, timing_group: int) -> timedelta:
        """Get duration of whole course for a specific timing group"""
        return sum(
            (
                (s.time_to_stop + s.stopping_time)
                for s in self.stop_timings
                if s.timing_group == timing_group and s.time_to_stop is not None
            ), timedelta())

    @duration.expression
    def duration(cls, timing_group: int) -> ClauseElement:
        return select([func.sum(CourseStopTiming.time_to_stop + CourseStopTiming.stopping_time)]) \
            .where(
                CourseStopTiming.course.expression
                & (CourseStopTiming.timing_group == timing_group)
                & (CourseStopTiming.time_to_stop != None)
            ).label("duration")

    @hybrid_method
    def date_valid(self, date_obj: date) -> bool:
        """Whether a `datetime.date` is in the validity period of this line (alternatively: of its `DINO2.model.Version`)"""
        d_from = self.valid_from or self.version.date_from
        d_to = self.valid_to or self.version.date_to
        return (date_obj >= d_from if d_from is not None else True) and (date_obj <= d_to if d_to is not None else True)

    @date_valid.expression
    def date_valid(cls, date_obj: date) -> ClauseElement:
        d_from = case(
            [(cls.valid_from == None, select([Version.date_from]).where(Version.id == cls.version_id).scalar_subquery())],
            else_=cls.valid_from)
        d_to = case(
            [(cls.valid_to == None, select([Version.date_to]).where(Version.id == cls.version_id).scalar_subquery())],
            else_=cls.valid_to)
        return and_(
            case([(d_from == None, True)], else_=date_obj >= d_from),
            case([(d_to == None, True)], else_=date_obj <= d_to))

    __table_args__ = (
        ForeignKeyConstraint([version_id, branch_id], ["branch.VERSION", "branch.BRANCH_NR"]),
        ForeignKeyConstraint([version_id, mot_id], ["means_of_transport_desc.VERSION", "means_of_transport_desc.MOT_NR"]),
        ForeignKeyConstraint([version_id, operator_id], ["operator.VERSION", "operator.OP_CODE"]),
        ForeignKeyConstraint([version_id, operator_id, operator_branch_office_id], ["operator_branch_office.VERSION", "operator_branch_office.OP_CODE", "operator_branch_office.OBO_SHORT_NAME"])
    )

    def __repr__(self) -> str:
        return f"<Course(version_id={self.version_id}, branch_id={self.branch_id}, id={self.id}, name={self.name})>"

    __abstract__ = False


class StopPointType(Enum):
    no_stopping = -1
    standard = 0
    on_request = 1
    no_boarding = 2
    no_alighting = 3
    no_place_internal = 4
    no_passengers = 5


class CourseStop(Base):
    """
    Course stop

    A single stop on a `Course`.

    Primary key: `version_id` & `line` & `course_id` & `line_dir` & `consec_stop_nr`
    """
    _din_file = "route.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    line: Column[int] = Column("LINE_NR", Integer(), primary_key=True)
    """Line id"""

    course_id: Column[str] = Column("STR_LINE_VAR", String(length=4), primary_key=True)
    """Course id"""

    line_dir: Column[int] = Column("LINE_DIR_NR", Integer(), CheckConstraint("LINE_DIR_NR in (1, 2)"), primary_key=True)
    """Line direction (1 or 2)"""

    consec_stop_nr: Column[int] = Column("LINE_CONSEC_NR", Integer(), primary_key=True)
    """Consecutive stop number in route"""

    stop_id: Column[int] = Column("STOP_NR", Integer(), nullable=False)
    """Stop id"""
    stop_point_id: Column[int] = Column("STOPPING_POINT_NR", Integer(), nullable=False)
    """Stopping point id"""

    stop_point_type: Column[StopPointType] = Column("STOPPING_POINT_TYPE", IntEnum(StopPointType), nullable=False, info={'keep_minus_1': True})
    """Stopping point type"""

    length: Column[Optional[int]] = Column("LENGTH", Integer())
    """Distance to preceding stop (m)"""

    stop: RelationshipProperty[Stop] = relationship("Stop", viewonly=True)
    """`DINO2.model.location.Stop`"""
    stop_point: RelationshipProperty[StopPoint] = relationship("StopPoint", viewonly=True)
    """`DINO2.model.location.StopPoint`"""
    course: RelationshipProperty[Course] = relationship(Course, back_populates="stops")
    """`Course`"""
    timings: RelationshipProperty[Sequence[CourseStopTiming]] = relationship("CourseStopTiming", back_populates="course_stop")
    """`CourseStopTiming`s"""
    trip_vdt_changes: RelationshipProperty[Sequence[TripVDT]] = relationship("TripVDT", order_by="asc(TripVDT.consec_stop_nr)", viewonly=True)
    """Trip vehicle destination text changes (`DINO2.model.schedule.TripVDT`) at this course stop"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, line, course_id, line_dir], [Course.version_id, Course.line, Course.id, Course.line_dir]),
        ForeignKeyConstraint([version_id, stop_id], ["stop.VERSION", "stop.STOP_NR"]),
        ForeignKeyConstraint([version_id, stop_id, stop_point_id], ["stop_point.VERSION", "stop_point.STOP_NR", "stop_point.STOPPING_POINT_NR"])
    )

    def __repr__(self) -> str:
        return f"<CourseStop(version_id={self.version_id}, course={self.course}, consec_stop_nr={self.consec_stop_nr}, stop_point={self.stop_point})>"

    __abstract__ = False


class CourseStopTiming(Base):
    """
    Course stop timing

    A `Course` can have multiple "timing groups" depicting a specific combination of travel times between its `CourseStop`s.  
    For example the same `Course` can have a different travel time depending on time or day (rush hour, night, weekend, ..).

    Primary key: `version_id` & `line` & `course_id` & `line_dir` & `consec_stop_nr` & `timing_group`
    """
    _din_file = "timing_pattern.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    line: Column[int] = Column("LINE_NR", Integer(), primary_key=True)
    """Line id"""

    course_id: Column[str] = Column("STR_LINE_VAR", String(length=4), primary_key=True)
    """Course id"""

    line_dir: Column[int] = Column("LINE_DIR_NR", Integer(), CheckConstraint("LINE_DIR_NR in (1, 2)"), primary_key=True)
    """Line direction (1 or 2)"""

    consec_stop_nr: Column[int] = Column("LINE_CONSEC_NR", Integer(), primary_key=True)
    """Consecutive stop number in route"""

    timing_group: Column[int] = Column("TIMING_GROUP_NR", Integer(), primary_key=True)
    """Timing group id"""

    time_to_stop: Column[Optional[timedelta]] = Column("TT_REL", DinoTimeDelta(minus_1_none=True), nullable=False, info={'keep_minus_1': True})
    """Travel time from previous course stop (None = passes through stop)"""
    stopping_time: Column[timedelta] = Column("STOPPING_TIME", DinoTimeDelta(), nullable=False)
    """Stopping/waiting time at this course stop"""

    course_stop: RelationshipProperty[CourseStop] = relationship(CourseStop, back_populates="timings")
    """`CourseStop`"""
    course: RelationshipProperty[Course] = relationship(Course, viewonly=True)
    """`Course`"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, line, course_id, line_dir], [Course.version_id, Course.line, Course.id, Course.line_dir]),
        ForeignKeyConstraint([version_id, line, course_id, line_dir, consec_stop_nr], [CourseStop.version_id, CourseStop.line, CourseStop.course_id, CourseStop.line_dir, CourseStop.consec_stop_nr])
    )

    def __repr__(self) -> str:
        return f"<CourseStopTiming(version_id={self.version_id}, course_stop={self.course_stop}, time_to_stop={self.time_to_stop}, stopping_time={self.stopping_time})>"

    __abstract__ = False
