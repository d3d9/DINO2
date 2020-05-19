# -*- coding: utf-8 -*-
"""
Data model for DINO 2.1 data

### Structure
- `DINO2.model` --> `DinoBase`, **`Version`**
    - `DINO2.model.calendar` --> Day types/attributes, days, restrictions ..
    - `DINO2.model.fares` --> Fare zones
    - `DINO2.model.location` --> Stops, links ..
    - `DINO2.model.operational` --> Operational objects/descriptions ..
    - `DINO2.model.network` --> Courses, timings ..
    - `DINO2.model.schedule` --> Trips ..

### Graphs

#### Table graph created using database metadata (including `Version`: [here](./schema_db_withversion.png))
[<img src="./schema_db.png" width="400px"/>](./schema_db.png)

#### Model graph created using `DINO2.model` (including `Version`: [here](./schema_model_withversion.png))
[<img src="./schema_model.png" width="400px"/>](./schema_model.png)

"""

from __future__ import annotations

from datetime import date
from sqlalchemy import Column, String, Integer, Boolean, inspect
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.types import TypeEngine
from sqlalchemy.orm import relationship, RelationshipProperty
from sqlalchemy.orm.session import Session
from typing import Optional, Collection, Tuple, TYPE_CHECKING, Any, Dict

from ..types import DinoDate

if TYPE_CHECKING:
    from .calendar import DayType, DayAttribute, DayGrouping, CalendarDay, Restriction
    from .fares import FareZone, NeighbourFareZone
    from .location import Stop, StopAliasPlacename, StopAdditionalName, StopArea, StopPoint, Link, LinkGeometryPoint, LinkForcePoint
    from .operational import Branch, Operator, OperatorBranchOffice, MeansOfTransportDesc, VehicleType, VehicleDestinationText
    from .network import Course, CourseStop, CourseStopTiming
    from .schedule import Notice, Trip, StopConstraint, TripVDT


class DinoBase:
    """
    Used for declarative base class for DINO models.

    Sets `__tablename__` using class variable `_din_file: str`.

    Provides some helpers for easier access to column info for data import.
    """
    _din_file: str

    @declared_attr
    def __tablename__(cls):
        name = cls._din_file[:-4] if cls._din_file.endswith('.din') else cls._din_file
        if not name:
            raise ValueError(f"{cls}: _din_file required")
        return name

    @property
    def _session(self) -> Session:
        return Session.object_session(self)

    @classmethod
    def _column_names(cls) -> Tuple[str, ...]:
        return tuple(c.name for c in inspect(cls).columns.values())

    @classmethod
    def _dtypes(cls) -> Dict[str, Any]:
        def pandas_dtype(t: TypeEngine) -> str:
            if hasattr(t, 'impl'):
                t = t.impl
            if isinstance(t, (Integer, Boolean)):
                return 'Int64'
            if isinstance(t, String):
                return 'object'
            raise ValueError(f"Can't suggest a pandas dtype for {t}")
        return {c.name: pandas_dtype(c.type) for c in inspect(cls).columns.values()}

    @classmethod
    def _parameters(cls) -> Dict[str, str]:
        return {c.name: par for par, c in inspect(cls).columns.items()}

    @classmethod
    def _col_info(cls, col: str) -> Dict[Any, Any]:
        return inspect(cls).columns[col].info


Base = declarative_base(cls=DinoBase)


class Version(Base):
    """
    Central class for timetable base versions.
    All other model classes refer to this class.

    `Version`s are usually seperate and usable on their own,
    e. g. one `Version` for one whole timetable period of one transport operator.  
    In some cases, multiple `Version`s have to be processed by applications,
    for example a `Version` with a higher `Version.priority` than another of the same operator,
    having overlapping validity periods, which may be the case for a special event, vacation time, or a pandemic.

    Primary key: `id`
    """
    _din_file = "version.din"

    id: Column[int] = Column("VERSION", Integer(), primary_key=True)
    """Version id"""

    desc: Column[Optional[str]] = Column("VERSION_TEXT", String(length=70))
    """Description"""
    period: Column[Optional[str]] = Column("TIMETABLE_PERIOD", String(length=4))
    """Timetable period abbreviation"""
    period_name: Column[Optional[str]] = Column("TT_PERIOD_NAME", String(length=40))
    """Timetable period name"""

    date_from: Column[Optional[date]] = Column("PERIOD_DATE_FROM", DinoDate)
    """Date of the beginning of the period"""
    date_to: Column[Optional[date]] = Column("PERIOD_DATE_TO", DinoDate)
    """Date of the last day of the period"""

    net: Column[Optional[str]] = Column("NET_ID", String(length=3))
    """Network abbreviation"""
    priority: Column[Optional[int]] = Column("PERIOD_PRIORITY", Integer())
    """Priority of timetable, if there are overlapping timetable versions (for example a timetable limited to the time of a large event in the city)"""

    daytypes: RelationshipProperty[Collection[DayType]] = relationship("DayType", back_populates="version")
    """List of `calendar.DayType`s of this version"""
    dayattrs: RelationshipProperty[Collection[DayAttribute]] = relationship("DayAttribute", back_populates="version")
    """List of `calendar.DayAttribute`s of this version"""
    daygroupings: RelationshipProperty[Collection[DayGrouping]] = relationship("DayGrouping", back_populates="version")
    """List of `calendar.DayGrouping`s of this version"""
    day_type_calendar: RelationshipProperty[Collection[CalendarDay]] = relationship("CalendarDay", viewonly=True)
    """List of `calendar.CalendarDay`s of this version"""
    restrictions: RelationshipProperty[Collection[Restriction]] = relationship("Restriction", back_populates="version")
    """List of `calendar.Restriction`s of this version"""

    farezones: RelationshipProperty[Collection[FareZone]] = relationship("FareZone", back_populates="version")
    """List of `fares.FareZone`s of this version"""
    farezonegroupings: RelationshipProperty[Collection[NeighbourFareZone]] = relationship("NeighbourFareZone", back_populates="version")
    """List of `fares.NeighbourFareZone`s of this version"""

    stops: RelationshipProperty[Collection[Stop]] = relationship("Stop", back_populates="version")
    """List of `location.Stop`s of this version"""
    stop_alias_placenames: RelationshipProperty[Collection[StopAliasPlacename]] = relationship("StopAliasPlacename", viewonly=True)
    """List of `location.StopAliasPlacename`s of this version"""
    stop_additional_names: RelationshipProperty[Collection[StopAdditionalName]] = relationship("StopAdditionalName", viewonly=True)
    """List of `location.StopAdditionalName`s of this version"""
    stop_areas: RelationshipProperty[Collection[StopArea]] = relationship("StopArea", viewonly=True)
    """List of `location.StopArea`s of this version"""
    stop_points: RelationshipProperty[Collection[StopPoint]] = relationship("StopPoint", viewonly=True)
    """List of `location.StopPoint`s of this version"""
    links: RelationshipProperty[Collection[Link]] = relationship("Link", back_populates="version")
    """List of `location.Link`s of this version"""
    link_geometry_points: RelationshipProperty[Collection[LinkGeometryPoint]] = relationship("LinkGeometryPoint", viewonly=True)
    """List of `location.LinkGeometryPoint`s of this version"""
    link_force_points: RelationshipProperty[Collection[LinkForcePoint]] = relationship("LinkForcePoint", viewonly=True)
    """List of `location.LinkForcePoint`s of this version"""

    branches: RelationshipProperty[Collection[Branch]] = relationship("Branch", back_populates="version")
    """List of `operational.Branch`es of this version"""
    operators: RelationshipProperty[Collection[Operator]] = relationship("Operator", back_populates="version")
    """List of `operational.Operator`s of this version"""
    operator_branch_offices: RelationshipProperty[Collection[OperatorBranchOffice]] = relationship("OperatorBranchOffice", viewonly=True)
    """List of `operational.OperatorBranchOffice`s of this version"""
    means_of_transport: RelationshipProperty[Collection[MeansOfTransportDesc]] = relationship("MeansOfTransportDesc", back_populates="version")
    """List of `operational.MeansOfTransportDesc`s of this version"""
    vehicle_types: RelationshipProperty[Collection[VehicleType]] = relationship("VehicleType", back_populates="version")
    """List of `operational.VehicleType`s of this version"""
    vehicle_destination_texts: RelationshipProperty[Collection[VehicleDestinationText]] = relationship("VehicleDestinationText", back_populates="version")
    """List of `operational.VehicleDestinationText`s of this version"""

    courses: RelationshipProperty[Collection[Course]] = relationship("Course", back_populates="version")
    """List of `network.Course`s of this version"""
    course_stops: RelationshipProperty[Collection[CourseStop]] = relationship("CourseStop", viewonly=True)
    """List of `network.CourseStop`s of this version"""
    stop_timings: RelationshipProperty[Collection[CourseStopTiming]] = relationship("CourseStopTiming", viewonly=True)
    """List of `network.CourseStopTiming`s of this version"""

    notices: RelationshipProperty[Collection[Notice]] = relationship("Notice", back_populates="version")
    """List of `schedule.Notice`s of this version"""
    trips: RelationshipProperty[Collection[Trip]] = relationship("Trip", back_populates="version")
    """List of `schedule.Trip`s of this version"""
    constraints: RelationshipProperty[Collection[StopConstraint]] = relationship("StopConstraint", viewonly=True)
    """List of `schedule.StopConstraint`s of this version"""
    trip_vdts: RelationshipProperty[Collection[TripVDT]] = relationship("TripVDT", viewonly=True)
    """List of `schedule.TripVDT`s of this version"""

    def __repr__(self) -> str:
        return f"<Version(id={self.id}, desc={self.desc}, period={self.period}, period_name={self.period_name}, date_from={self.date_from}, date_to={self.date_to}, net={self.net}, priority={self.priority})>"


from . import calendar, fares, location, operational, network, schedule
