# -*- coding: utf-8 -*-
"""DINO 2.1 schedule data"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, ForeignKeyConstraint, CheckConstraint, and_, or_, tuple_
from sqlalchemy.orm import relationship, RelationshipProperty, joinedload, Query
from typing import Optional, Tuple, FrozenSet, Sequence, TYPE_CHECKING

from ..types import DinoTimeDelta, IntEnum, CharEnum
from . import Base, Version

if TYPE_CHECKING:
    from .calendar import DayAttribute, Restriction
    from .location import Stop, StopPoint
    from .operational import Operator, OperatorBranchOffice, VehicleType, VehicleDestinationText
    from .network import Course, CourseStop, CourseStopTiming


class NoticeContentType(Enum):
    general = 0
    train_name = 1
    on_demand_phone = 2
    bicycle = 3
    track = 4


class NoticeDisplayType(Enum):
    always = 0
    on_boarding = 1
    on_alighting = 2
    on_board = 4
    # DINO docs are extremely ambiguous here (DE / EN)
    on_boarding_or_alighting = 5
    on_board_or_alighting = 8


class Notice(Base):
    """
    Operational notice

    Primary key: `version_id` & _`line`_ & `id`
    """
    _din_file = "notice.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    line: Column[Optional[int]] = Column("LINE_NR", Integer(), primary_key=True, nullable=True)
    """Line number (if None, valid for all lines)"""

    id: Column[str] = Column("NOTICE", String(length=5), primary_key=True)
    """Notice id"""

    text: Column[str] = Column("NOTICE_TEXT", String(length=1000), nullable=False)
    """Notice text"""

    content_type: Column[Optional[NoticeContentType]] = Column("CONTENT_TYPE", IntEnum(NoticeContentType))
    """Content type"""

    display_type: Column[Optional[NoticeDisplayType]] = Column("DISPLAY_TYPE", IntEnum(NoticeDisplayType))
    """Display type"""

    trips: RelationshipProperty[Sequence[Trip]] = relationship("Trip", primaryjoin="and_(Notice.version_id==Trip.version_id, or_(Notice.id==Trip.notice1id, Notice.id==Trip.notice2id, Notice.id==Trip.notice3id, Notice.id==Trip.notice4id, Notice.id==Trip.notice5id), or_(Notice.line==Trip.line, Notice.line==None))", viewonly=True)
    """`Trip`s that refer to this this notice"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="notices")
    """`DINO2.model.Version`"""

    def __repr__(self) -> str:
        return f"<Notice(version_id={self.version_id}, id={self.id}, line={self.line}, text={self.text})>"

    __abstract__ = False


@dataclass(frozen=True)
class TripStop:
    """A single trip stop including constraint, destination text, and time information"""
    trip: Trip
    stop: Stop
    stop_point: StopPoint
    course_stop: CourseStop
    stop_timing: CourseStopTiming
    constraints: Optional[FrozenSet[StopConstraint]]
    vdt_before: Optional[VehicleDestinationText]
    vdt_after: Optional[VehicleDestinationText]
    arr_time: Optional[timedelta]
    dep_time: Optional[timedelta]
    distance_travelled: Optional[int]

    def __repr__(self) -> str:
        return f"<TripStop(trip={self.trip}, stop_timing={self.stop_timing}, arr_time={self.arr_time}, dep_time={self.dep_time})>"


class Trip(Base):
    """
    Trip

    A trip of a `DINO2.model.network.Course` with a specific "timing group".  
    Valid days defined using `Trip.day_attribute` and `Trip.restriction`.

    Primary key: `version_id` & `line` & `id`
    """
    _din_file = "trip.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    line: Column[int] = Column("LINE_NR", Integer(), primary_key=True)
    """Line id"""

    course_id: Column[str] = Column("STR_LINE_VAR", String(length=4), primary_key=False, nullable=False)
    """Course id"""

    line_dir: Column[int] = Column("LINE_DIR_NR", Integer(), CheckConstraint("LINE_DIR_NR in (1, 2)"), primary_key=False, nullable=False)
    """Line direction (1 or 2)"""

    # todo: ggf. noch zusaetzlich trigger oderso als check dass timing_group auch existiert??
    timing_group: Column[int] = Column("TIMING_GROUP_NR", Integer(), primary_key=False, nullable=False)
    """Timing group id"""

    id: Column[int] = Column("TRIP_ID", Integer(), primary_key=True)
    """Trip id"""

    id_printing: Column[Optional[int]] = Column("TRIP_ID_PRINTING", Integer())
    """Trip id for presentation"""

    departure_time: Column[timedelta] = Column("DEPARTURE_TIME", DinoTimeDelta(), nullable=False)
    """Departure time as timedelta"""

    dep_stop_id: Column[int] = Column("DEP_STOP_NR", Integer(), nullable=False)
    """Departure stop id"""
    dep_stop_point_id: Column[int] = Column("DEP_STOPPING_POINT_NR", Integer(), nullable=False)
    """Departure stop point id"""
    arr_stop_id: Column[int] = Column("ARR_STOP_NR", Integer(), nullable=False)
    """Arrival stop id"""
    arr_stop_point_id: Column[int] = Column("ARR_STOPPING_POINT_NR", Integer(), nullable=False)
    """Arrival stop point id"""

    vehicle_type_id: Column[Optional[int]] = Column("VEH_TYPE_NR", Integer())
    """Vehicle type id"""

    day_attribute_id: Column[int] = Column("DAY_ATTRIBUTE_NR", Integer(), nullable=False)
    """Day attribute grouping id"""
    restriction_id: Column[Optional[str]] = Column("RESTRICTION", String(length=5))
    """Restriction id"""

    notice1id: Column[Optional[str]] = Column("NOTICE", String(length=5))
    """Notice id 1"""
    notice2id: Column[Optional[str]] = Column("NOTICE_2", String(length=5))
    notice3id: Column[Optional[str]] = Column("NOTICE_3", String(length=5))
    notice4id: Column[Optional[str]] = Column("NOTICE_4", String(length=5))
    notice5id: Column[Optional[str]] = Column("NOTICE_5", String(length=5))

    round_trip_id: Column[Optional[int]] = Column("ROUND_TRIP_ID", Integer())
    """
    Round trip id.
    Supposed to be primary key, but not implemented here.
    Also, the column name seems to be wrong in the documentation ("ROUND_TRIP_NR")
    """
    train_id: Column[Optional[int]] = Column("TRAIN_NR", Integer())
    train_category_abbr: Column[Optional[str]] = Column("TRAIN_CATEGORY_SHORT_NAME", String(length=10))

    operator_id: Column[Optional[str]] = Column("OP_CODE", String(length=10))
    """Operator id"""
    operator_branch_office_id: Column[Optional[str]] = Column("OBO_SHORT_NAME", String(length=10))
    """Operator branch office id"""

    global_id: Column[Optional[str]] = Column("GLOBAL_ID", String(length=100))
    """Global trip id"""
    bike_allowed: Column[Optional[bool]] = Column("BIKE_ALLOWED", Boolean())
    """Whether bikes are allowed on this trip"""
    purpose_id: Column[Optional[int]] = Column("PURPOSE_NR", Integer())
    """FK to trip purpose (not implemented yet, internal)"""

    dep_stop: RelationshipProperty[Stop] = relationship("Stop", foreign_keys="[Trip.version_id, Trip.dep_stop_id]", viewonly=True)
    """
    Departure `DINO2.model.location.Stop`

    It is unclear what these four attributes are used for.  
    They can't be used to 'slice' the `DINO2.model.network.Course`; there is no 'stop index' in case a stop is stopped at multiple times.  
    They might just be simple helpful "shortcuts".
    """
    # evtl. todo (query machen)
    dep_stop_point: RelationshipProperty[StopPoint] = relationship("StopPoint", foreign_keys="[Trip.version_id, Trip.dep_stop_id, Trip.dep_stop_point_id]", viewonly=True)
    """Departure `DINO2.model.location.StopPoint`"""
    arr_stop: RelationshipProperty[Stop] = relationship("Stop", foreign_keys="[Trip.version_id, Trip.arr_stop_id]", viewonly=True)
    """Arrival `DINO2.model.location.Stop`"""
    arr_stop_point: RelationshipProperty[StopPoint] = relationship("StopPoint", foreign_keys="[Trip.version_id, Trip.arr_stop_id, Trip.arr_stop_point_id]", viewonly=True)
    """Arrival `DINO2.model.location.StopPoint`"""

    vehicle_type: RelationshipProperty[Optional[VehicleType]] = relationship("VehicleType", viewonly=True)
    """`DINO2.model.operational.VehicleType`"""
    day_attribute: RelationshipProperty[DayAttribute] = relationship("DayAttribute", viewonly=True)
    """`DINO2.model.calendar.DayAttribute`"""
    restriction: RelationshipProperty[Optional[Restriction]] = relationship("Restriction", primaryjoin="and_(Restriction.version_id==Trip.version_id, Restriction.id==Trip.restriction_id, or_(Restriction.line==Trip.line, Restriction.line==None))", viewonly=True)
    """`DINO2.model.calendar.Restriction`"""
    notice1: RelationshipProperty[Optional[Notice]] = relationship(Notice, primaryjoin="and_(Notice.version_id==Trip.version_id, Notice.id==Trip.notice1id, or_(Notice.line==Trip.line, Notice.line==None))", viewonly=True)
    """`Notice` 1"""
    notice2: RelationshipProperty[Optional[Notice]] = relationship(Notice, primaryjoin="and_(Notice.version_id==Trip.version_id, Notice.id==Trip.notice2id, or_(Notice.line==Trip.line, Notice.line==None))", viewonly=True)
    notice3: RelationshipProperty[Optional[Notice]] = relationship(Notice, primaryjoin="and_(Notice.version_id==Trip.version_id, Notice.id==Trip.notice3id, or_(Notice.line==Trip.line, Notice.line==None))", viewonly=True)
    notice4: RelationshipProperty[Optional[Notice]] = relationship(Notice, primaryjoin="and_(Notice.version_id==Trip.version_id, Notice.id==Trip.notice4id, or_(Notice.line==Trip.line, Notice.line==None))", viewonly=True)
    notice5: RelationshipProperty[Optional[Notice]] = relationship(Notice, primaryjoin="and_(Notice.version_id==Trip.version_id, Notice.id==Trip.notice5id, or_(Notice.line==Trip.line, Notice.line==None))", viewonly=True)
    operator: RelationshipProperty[Optional[Operator]] = relationship("Operator", viewonly=True)
    """`DINO2.model.operational.Operator`"""
    operator_branch_office: RelationshipProperty[Optional[OperatorBranchOffice]] = relationship("OperatorBranchOffice", viewonly=True)
    """`DINO2.model.operational.OperatorBranchOffice`"""
    stop_timings: RelationshipProperty[Sequence[CourseStopTiming]] = relationship("CourseStopTiming", primaryjoin="and_(CourseStopTiming.version_id==Trip.version_id, CourseStopTiming.line==Trip.line, CourseStopTiming.course_id==Trip.course_id, CourseStopTiming.line_dir==Trip.line_dir, CourseStopTiming.timing_group==Trip.timing_group)", order_by="asc(CourseStopTiming.consec_stop_nr)", foreign_keys=[version_id, line, course_id, line_dir, timing_group], viewonly=True, uselist=True)
    """`DINO2.model.network.CourseStopTiming`s"""
    course: RelationshipProperty[Course] = relationship("Course", viewonly=True)
    """`DINO2.model.network.Course`"""
    constraints: RelationshipProperty[Sequence[StopConstraint]] = relationship("StopConstraint", back_populates="trip")
    """`StopConstraint`s of this trip"""
    vdt_changes: RelationshipProperty[Sequence[TripVDT]] = relationship("TripVDT", order_by="asc(TripVDT.consec_stop_nr)", back_populates="trip")
    """Vehicle destination text changes (`TripVDT`) on this trip"""
    vdts: RelationshipProperty[Sequence[VehicleDestinationText]] = relationship("VehicleDestinationText", order_by="asc(TripVDT.consec_stop_nr)", secondary="trip_vdt", viewonly=True)
    """`DINO2.model.operational.VehicleDestinationText`s used on this trip"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="trips")
    """`DINO2.model.Version`"""

    @property
    def notices(self) -> FrozenSet[Notice]:
        """Set of `Notice`s of this trip"""
        return frozenset(filter(None, (self.notice1, self.notice2, self.notice3, self.notice4, self.notice5)))

    __table_args__ = (
        ForeignKeyConstraint([version_id, line, course_id, line_dir], ["line.VERSION", "line.LINE_NR",  "line.STR_LINE_VAR", "line.LINE_DIR_NR"]),
        ForeignKeyConstraint([version_id, dep_stop_id], ["stop.VERSION", "stop.STOP_NR"]),
        ForeignKeyConstraint([version_id, dep_stop_id, dep_stop_point_id], ["stop_point.VERSION", "stop_point.STOP_NR", "stop_point.STOPPING_POINT_NR"]),
        ForeignKeyConstraint([version_id, arr_stop_id], ["stop.VERSION", "stop.STOP_NR"]),
        ForeignKeyConstraint([version_id, arr_stop_id, arr_stop_point_id], ["stop_point.VERSION", "stop_point.STOP_NR", "stop_point.STOPPING_POINT_NR"]),
        ForeignKeyConstraint([version_id, vehicle_type_id], ["vehicle_type.VERSION", "vehicle_type.VEH_TYPE_NR"]),
        ForeignKeyConstraint([version_id, day_attribute_id], ["day_attribute.VERSION", "day_attribute.DAY_ATTRIBUTE_NR"]),
        ForeignKeyConstraint([version_id, restriction_id], ["service_restriction.VERSION", "service_restriction.RESTRICTION"]),
        ForeignKeyConstraint([version_id, restriction_id, line], ["service_restriction.VERSION", "service_restriction.RESTRICTION", "service_restriction.LINE_NR"]),
        ForeignKeyConstraint([version_id, notice1id], ["notice.VERSION", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, notice2id], ["notice.VERSION", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, notice3id], ["notice.VERSION", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, notice4id], ["notice.VERSION", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, notice5id], ["notice.VERSION", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, line, notice1id], ["notice.VERSION", "notice.LINE_NR", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, line, notice2id], ["notice.VERSION", "notice.LINE_NR", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, line, notice3id], ["notice.VERSION", "notice.LINE_NR", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, line, notice4id], ["notice.VERSION", "notice.LINE_NR", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, line, notice5id], ["notice.VERSION", "notice.LINE_NR", "notice.NOTICE"]),
        ForeignKeyConstraint([version_id, operator_id], ["operator.VERSION", "operator.OP_CODE"]),
        ForeignKeyConstraint([version_id, operator_id, operator_branch_office_id], ["operator_branch_office.VERSION", "operator_branch_office.OP_CODE", "operator_branch_office.OBO_SHORT_NAME"])
    )

    def trip_stops(self, simple: bool = False) -> Tuple[TripStop, ...]:
        """All trip stops as `TripStop` objects"""
        tstops = []
        currenttime = self.departure_time
        current_Tvdt: Optional[TripVDT] = None
        d_t: Optional[int] = None
        for timing in self.stop_timings:
            if timing.time_to_stop is not None:
                # None: passes through stop
                currenttime += timing.time_to_stop
            if not simple and timing.course_stop.length is not None:
                d_t = (d_t or 0) + timing.course_stop.length
            prev_Tvdt = current_Tvdt
            if not simple:
                current_Tvdt = next(filter(lambda c: c.consec_stop_nr == timing.consec_stop_nr, self.vdt_changes), None) or prev_Tvdt
            tstops.append(
                TripStop(
                    trip=self,
                    stop=timing.course_stop.stop,
                    stop_point=timing.course_stop.stop_point,
                    course_stop=timing.course_stop,
                    stop_timing=timing,
                    constraints=frozenset(filter(lambda c: c.consec_stop_nr == timing.consec_stop_nr, self.constraints)) if not simple else None,
                    vdt_before=prev_Tvdt.vdt if prev_Tvdt else None,
                    vdt_after=current_Tvdt.vdt if current_Tvdt else None,
                    arr_time=None if timing.time_to_stop is None else currenttime,
                    dep_time=None if timing.time_to_stop is None else (currenttime + timing.stopping_time),
                    distance_travelled=d_t
                ))
            if timing.time_to_stop is not None:
                currenttime += timing.stopping_time
        return tuple(tstops)

    def wkt(self, day: Optional[date] = None) -> str:
        """Get WKT (well known text) representation with time measures of this trip"""
        return self.course.wkt_m(self.timing_group, self.departure_time, day)

    @property
    def duration(self) -> timedelta:
        """Trip duration"""
        return self.course.duration(self.timing_group)

    @property
    def dates(self) -> FrozenSet[date]:
        """Valid dates"""
        ds = self.day_attribute.dates if self.restriction is None else (self.day_attribute.dates & self.restriction.dates)
        return frozenset(filter(self.course.date_valid, ds))

    @staticmethod
    def query_for_date(session, date_obj: date) -> Query:
        """Query for all trips valid on a specific `datetime.date`. Does not check for `DINO2.model.Version.priority`!"""
        from .calendar import Restriction, DayAttribute, CalendarDay
        from .network import Course
        restrictions = set((r.version_id, r.id) for r in session.query(Restriction).all() if date_obj in r.dates)
        # todo: ist Restriction.line zu beachten?
        attrs = session.query(DayAttribute).join('days').filter(CalendarDay.day == date_obj).subquery()
        return session.query(Trip).options(joinedload('course', innerjoin=True)).join(attrs) \
            .filter(Trip.course.has(criterion=Course.date_valid(date_obj))) \
            .filter((Trip.restriction_id == None) | (tuple_(Trip.version_id, Trip.restriction_id).in_(restrictions)))

    def __repr__(self) -> str:
        return f"<Trip(version_id={self.version_id}, line={self.line}, id={self.id}, departure_time={self.departure_time}, day_attribute={self.day_attribute}, restriction_id={self.restriction_id})>"

    __abstract__ = False


class StopConstraintType(Enum):
    only_alighting = 'A'
    only_boarding = 'E'
    no_place_internal = 'I'
    undocumented_type_B = 'B'


class StopConstraint(Base):
    """
    Stopping constraint

    Primary key: `version_id` & `line` & `trip_id` & `consec_stop_nr` & `constraint`
    """
    _din_file = "service_constraint.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    line: Column[int] = Column("LINE_NR", Integer(), primary_key=True)
    """Line id"""

    course_id: Column[Optional[str]] = Column("STR_LINE_VAR", String(length=4))
    """Course id"""

    line_dir: Column[Optional[int]] = Column("LINE_DIR_NR", Integer(), CheckConstraint("LINE_DIR_NR in (1, 2)"))
    """Line direction (1 or 2)"""

    trip_id: Column[int] = Column("TRIP_ID", Integer(), primary_key=True)
    """Trip id"""

    consec_stop_nr: Column[int] = Column("LINE_CONSEC_NR", Integer(), primary_key=True)
    """Consecutive stop number in route"""

    stop_id: Column[Optional[int]] = Column("STOP_NR", Integer())
    """Stop id"""
    stop_point_id: Column[Optional[int]] = Column("STOPPING_POINT_NR", Integer())
    """Stopping point id"""

    constraint: Column[StopConstraintType] = Column("SERVICE_INTERDICTION_CODE", CharEnum(StopConstraintType), primary_key=True)
    """Stopping constraint"""

    course: RelationshipProperty[Optional[Course]] = relationship("Course", viewonly=True)
    """`DINO2.model.network.Course`"""
    course_stop: RelationshipProperty[Optional[CourseStop]] = relationship("CourseStop", viewonly=True)
    """`DINO2.model.network.CourseStop`"""
    trip: RelationshipProperty[Trip] = relationship(Trip, back_populates="constraints")
    """`Trip`"""
    stop: RelationshipProperty[Optional[Stop]] = relationship("Stop", viewonly=True)
    """`DINO2.model.location.Stop`"""
    stop_point: RelationshipProperty[Optional[StopPoint]] = relationship("StopPoint", viewonly=True)
    """`DINO2.model.location.StopPoint`"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, line, course_id, line_dir], ["line.VERSION", "line.LINE_NR", "line.STR_LINE_VAR", "line.LINE_DIR_NR"]),
        ForeignKeyConstraint([version_id, line, course_id, line_dir, consec_stop_nr], ["route.VERSION", "route.LINE_NR", "route.STR_LINE_VAR", "route.LINE_DIR_NR", "route.LINE_CONSEC_NR"]),
        ForeignKeyConstraint([version_id, line, trip_id], [Trip.version_id, Trip.line, Trip.id]),
        ForeignKeyConstraint([version_id, stop_id], ["stop.VERSION", "stop.STOP_NR"]),
        ForeignKeyConstraint([version_id, stop_id, stop_point_id], ["stop_point.VERSION", "stop_point.STOP_NR", "stop_point.STOPPING_POINT_NR"])
    )

    def __repr__(self) -> str:
        return f"<StopConstraint(version_id={self.version_id}, line={self.line}, trip_id={self.trip_id}, consec_stop_nr={self.consec_stop_nr}, constraint={self.constraint})>"

    __abstract__ = False


class TripVDT(Base):
    """
    Destination text for a `Trip`

    Primary key contains `TripVDT.trip_id` instead of `TripVDT.course_id` and `TripVDT.line_dir`..

    Primary key: `version_id` & _`period`_ & `line` & ~~`course_id`~~ & ~~`line_dir`~~ & ++`trip_id`++ & `consec_stop_nr`
    """
    _din_file = "trip_vdt.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    period: Column[Optional[str]] = Column("TIMETABLE_PERIOD", String(length=4), primary_key=True, nullable=True)
    """Timetable period abbreviation"""

    line: Column[int] = Column("LINE_NR", Integer(), primary_key=True)
    """Line id"""

    # course_id: Column[Optional[str]] = Column("STR_LINE_VAR", String(length=4), primary_key=True, nullable=True)
    course_id: Column[Optional[str]] = Column("STR_LINE_VAR", String(length=4), primary_key=False)
    """Course id"""

    # line_dir: Column[Optional[int]] = Column("LINE_DIR_NR", Integer(), CheckConstraint("LINE_DIR_NR in (1, 2)"), primary_key=True, nullable=True)
    line_dir: Column[Optional[int]] = Column("LINE_DIR_NR", Integer(), CheckConstraint("LINE_DIR_NR in (1, 2)"), primary_key=False)
    """Line direction (1 or 2)"""

    # trip_id: Column[int] = Column("TRIP_ID", Integer(), nullable=False)
    trip_id: Column[int] = Column("TRIP_ID", Integer(), primary_key=True)
    """Trip id"""

    consec_stop_nr: Column[int] = Column("LINE_CONSEC_NR", Integer(), primary_key=True)
    """Consecutive stop number in route"""

    vdt_id: Column[int] = Column("VDT_NR", Integer(), nullable=False)
    """Vehicle destination text id"""

    course_stop: RelationshipProperty[Optional[CourseStop]] = relationship("CourseStop", viewonly=True)
    """`DINO2.model.network.CourseStop`"""
    trip: RelationshipProperty[Trip] = relationship(Trip, back_populates="vdt_changes")
    """`Trip`"""
    vdt: RelationshipProperty[VehicleDestinationText] = relationship("VehicleDestinationText", viewonly=True)
    """`DINO2.model.operational.VehicleDestinationText`"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, line, course_id, line_dir], ["line.VERSION", "line.LINE_NR", "line.STR_LINE_VAR", "line.LINE_DIR_NR"]),
        ForeignKeyConstraint([version_id, line, course_id, line_dir, consec_stop_nr], ["route.VERSION", "route.LINE_NR", "route.STR_LINE_VAR", "route.LINE_DIR_NR", "route.LINE_CONSEC_NR"]),
        ForeignKeyConstraint([version_id, line, trip_id], [Trip.version_id, Trip.line, Trip.id]),
        # ohne branch. line & trip_id sind zusammen eindeutig.. ?
        ForeignKeyConstraint([version_id, vdt_id], ["vehicle_destination_text.VERSION", "vehicle_destination_text.VDT_NR"])
    )

    def __repr__(self) -> str:
        return f"<TripVDT(version_id={self.version_id}, line={self.line}, trip_id={self.trip_id}, consec_stop_nr={self.consec_stop_nr}, vdt={self.vdt})>"

    __abstract__ = False
