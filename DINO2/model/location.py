# -*- coding: utf-8 -*-
"""DINO 2.1 location data"""

from __future__ import annotations

from collections import UserList
from datetime import date
import decimal
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.types import DECIMAL
from sqlalchemy.orm import relationship, RelationshipProperty
from typing import Optional, FrozenSet, TYPE_CHECKING, Sequence, Union

from ..types import DinoDate, IntEnum
from . import Base, Version

if TYPE_CHECKING:
    from .fares import FareZone
    from .operational import Branch
    from .network import Course


class StopType(Enum):
    standard = 0
    on_request = 1
    alighting_only = 2
    hail_and_ride = 3
    on_request_outside_net = 4
    transition_tarif = 7
    ein_aus_bringer = 8
    outside_net = 9
    time_pos = 10
    school = 12
    undocumented_type_19 = 19


class Stop(Base):
    """
    Stop

    Main model class for stops.  
    `Stop.valid_from` is supposed to be used to select a single `Stop` object from an importable DINO dataset,
    because of possible ambiguous objects in case of e. g. a name change during a period.

    Primary key: `version_id` & `id`
    """
    _din_file = "stop.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    id: Column[int] = Column("STOP_NR", Integer(), primary_key=True)
    """Stop id"""

    type: Column[Optional[StopType]] = Column("STOP_TYPE", IntEnum(StopType))
    """Stop type"""
    name: Column[str] = Column("STOP_NAME", String(length=50), nullable=False)
    """Stop name (including place name)"""
    name_noloc: Column[Optional[str]] = Column("STOP_NAME_WITHOUT_LOCALITY", String(length=50))
    """Stop name without place name"""
    abbr: Column[Optional[str]] = Column("STOP_SHORTNAME", String(length=8))
    """Short name / abbreviation of stop"""

    pos_x: Column[Optional[str]] = Column("STOP_POS_X", String(length=12), info={'str_minus_1_to_null': True})
    """Stop X coordinate (WGS84)"""
    pos_y: Column[Optional[str]] = Column("STOP_POS_Y", String(length=12), info={'str_minus_1_to_null': True})
    """Stop Y coordinate (WGS84)"""

    place: Column[Optional[str]] = Column("PLACE", String(length=20))
    """Place name (deprecated)"""

    occ: Column[Optional[int]] = Column("OCC", Integer())
    """Official community code / Amtliche Gemeindekennziffer"""

    fz1id: Column[Optional[int]] = Column("FARE_ZONE1_NR", Integer())
    """Fare zone id 1"""
    fz2id: Column[Optional[int]] = Column("FARE_ZONE2_NR", Integer())
    fz3id: Column[Optional[int]] = Column("FARE_ZONE3_NR", Integer())
    fz4id: Column[Optional[int]] = Column("FARE_ZONE4_NR", Integer())
    fz5id: Column[Optional[int]] = Column("FARE_ZONE5_NR", Integer())
    fz6id: Column[Optional[int]] = Column("FARE_ZONE6_NR", Integer())

    ifopt: Column[Optional[str]] = Column("GLOBAL_ID", String(length=100))
    """IFOPT / global id"""

    valid_from: Column[Optional[date]] = Column("VALID_FROM", DinoDate)
    """Valid from date (used in import, primary keys may occur multiple times with different validity periods)"""
    valid_to: Column[Optional[date]] = Column("VALID_TO", DinoDate)
    """Valid until date"""

    place_id: Column[Optional[str]] = Column("PLACE_ID", String(length=50))
    """unique place ID"""
    gis_mot_flag: Column[Optional[int]] = Column("GIS_MOT_FLAG", Integer())
    """GIS MOT bit flags"""
    is_central_stop: Column[Optional[bool]] = Column("IS_CENTRAL_STOP", Boolean())
    """Whether stop is central stop"""
    is_responsible_stop: Column[Optional[bool]] = Column("IS_RESPONSIBLE_STOP", Boolean())
    """Whether this stop object is the main/'responsible' one between multiple subnets"""
    interchange_quality: Column[Optional[int]] = Column("INTERCHANGE_QUALITY", Integer())
    """Interchange quality (higher is better)"""

    fz1: RelationshipProperty[Optional[FareZone]] = relationship("FareZone", foreign_keys="[Stop.version_id, Stop.fz1id]", viewonly=True)
    """`DINO2.model.fares.FareZone` 1"""
    fz2: RelationshipProperty[Optional[FareZone]] = relationship("FareZone", foreign_keys="[Stop.version_id, Stop.fz2id]", viewonly=True)
    fz3: RelationshipProperty[Optional[FareZone]] = relationship("FareZone", foreign_keys="[Stop.version_id, Stop.fz3id]", viewonly=True)
    fz4: RelationshipProperty[Optional[FareZone]] = relationship("FareZone", foreign_keys="[Stop.version_id, Stop.fz4id]", viewonly=True)
    fz5: RelationshipProperty[Optional[FareZone]] = relationship("FareZone", foreign_keys="[Stop.version_id, Stop.fz5id]", viewonly=True)
    fz6: RelationshipProperty[Optional[FareZone]] = relationship("FareZone", foreign_keys="[Stop.version_id, Stop.fz6id]", viewonly=True)
    stop_alias_placenames: RelationshipProperty[Sequence[StopAliasPlacename]] = relationship("StopAliasPlacename", back_populates="stop")
    """`DINO2.model.location.StopAliasPlacename`s of this stop"""
    stop_additional_names: RelationshipProperty[Sequence[StopAdditionalName]] = relationship("StopAdditionalName", back_populates="stop")
    """`DINO2.model.location.StopAdditionalName`s of this stop"""
    areas: RelationshipProperty[Sequence[StopArea]] = relationship("StopArea", back_populates="stop")
    """`DINO2.model.location.StopArea`s of this stop"""
    points: RelationshipProperty[Sequence[StopPoint]] = relationship("StopPoint", back_populates="stop")
    """`DINO2.model.location.StopPoint`s of this stop"""
    links_from: RelationshipProperty[Sequence[Link]] = relationship("Link", foreign_keys="[Link.version_id, Link.from_stop_id]", viewonly=True)
    """`DINO2.model.location.Link`s from this stop"""
    links_to: RelationshipProperty[Sequence[Link]] = relationship("Link", foreign_keys="[Link.version_id, Link.to_stop_id]", viewonly=True)
    """`DINO2.model.location.Link`s to this stop"""
    courses: RelationshipProperty[Sequence[Course]] = relationship("Course", secondary="route", viewonly=True)
    """`DINO2.model.network.Course`s with this stop on route"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="stops")
    """`DINO2.model.Version`"""

    @property
    def fare_zone_ids(self) -> FrozenSet[int]:
        """Set of ids of `DINO2.model.fares.FareZone`s of this stop"""
        return frozenset(filter(None, (self.fz1id, self.fz2id, self.fz3id, self.fz4id, self.fz5id, self.fz6id)))

    @property
    def fare_zones(self) -> FrozenSet[FareZone]:
        """Set of `DINO2.model.fares.FareZone`s this stop is in"""
        return frozenset(filter(None, (self.fz1, self.fz2, self.fz3, self.fz4, self.fz5, self.fz6)))

    __table_args__ = (
        ForeignKeyConstraint([version_id, fz1id], ["fare_zone.VERSION", "fare_zone.FARE_ZONE_NR"]),
        ForeignKeyConstraint([version_id, fz2id], ["fare_zone.VERSION", "fare_zone.FARE_ZONE_NR"]),
        ForeignKeyConstraint([version_id, fz3id], ["fare_zone.VERSION", "fare_zone.FARE_ZONE_NR"]),
        ForeignKeyConstraint([version_id, fz4id], ["fare_zone.VERSION", "fare_zone.FARE_ZONE_NR"]),
        ForeignKeyConstraint([version_id, fz5id], ["fare_zone.VERSION", "fare_zone.FARE_ZONE_NR"]),
        ForeignKeyConstraint([version_id, fz6id], ["fare_zone.VERSION", "fare_zone.FARE_ZONE_NR"])
    )

    def __repr__(self) -> str:
        return f"<Stop(version_id={self.version_id}, id={self.id}, name={self.name}, type={self.type}, ifopt={self.ifopt})>"

    __abstract__ = False


class StopAliasPlacename(Base):
    """
    Stop alias place name

    Primary key: `version_id` & `stop_id` & `alias_place` & `alias_occ`
    """
    _din_file = "stop_alias_placename.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    stop_id: Column[int] = Column("STOP_NR", Integer(), primary_key=True)
    """Stop id"""

    alias_place: Column[str] = Column("ALIAS_PLACE", String(length=20), primary_key=True)
    """Name of place"""

    alias_occ: Column[int] = Column("ALIAS_OCC", Integer(), primary_key=True)
    """OCC of place"""

    stop: RelationshipProperty[Stop] = relationship(Stop, back_populates="stop_alias_placenames")
    """`Stop`"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, stop_id], [Stop.version_id, Stop.id]),
    )

    def __repr__(self) -> str:
        return f"<StopAliasPlacename(version_id={self.version_id}, stop={self.stop}, alias_place={self.alias_place}, alias_occ={self.alias_occ})>"

    __abstract__ = False


class StopAdditionalName(Base):
    """
    Stop additional name

    Primary key: `version_id` & `stop_id` & `name` & `name_noloc`
    """
    _din_file = "stop_additional_name.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    stop_id: Column[int] = Column("STOP_NR", Integer(), primary_key=True)
    """Stop id"""

    name: Column[str] = Column("ADD_STOP_NAME_WITH_LOCALITY", String(length=255), primary_key=True)
    """Additional stop name with place name"""

    name_noloc: Column[str] = Column("ADD_STOP_NAME_WITHOUT_LOCALITY", String(length=255), primary_key=True, info={'keep_empty_str': True})
    """Additional stop name without place name"""

    stop: RelationshipProperty[Stop] = relationship(Stop, back_populates="stop_additional_names")
    """`Stop`"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, stop_id], [Stop.version_id, Stop.id]),
    )

    def __repr__(self) -> str:
        return f"<StopAdditionalName(version_id={self.version_id}, stop={self.stop}, name={self.name}, name_noloc={self.name_noloc})>"

    __abstract__ = False


class StopAreaType(Enum):
    entrance_and_pt = 0
    pt = 1
    p_r = 2
    b_r = 3
    taxi = 4
    entrance = 5
    airport_terminal = 6
    entrance_and_b_r = 7
    entrance_pt_and_b_r = 8
    entrance_and_taxi = 9
    entrance_pt_and_taxi = 10
    mezzanine = 11
    hail_and_ride = 12


class StopArea(Base):
    """
    Stop area

    Used to group `StopPoint`s, especially for working with transfer data.

    Primary key: `version_id` & `stop_id` & `id`
    """
    _din_file = "stop_area.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    stop_id: Column[int] = Column("STOP_NR", Integer(), primary_key=True)
    """Stop id"""

    id: Column[int] = Column("STOP_AREA_NR", Integer(), primary_key=True)
    """Stop area id"""

    pos_x: Column[Optional[str]] = Column("STOP_AREA_POS_X", String(length=12), info={'str_minus_1_to_null': True})
    """Stop area X coordinate (WGS84)"""
    pos_y: Column[Optional[str]] = Column("STOP_AREA_POS_Y", String(length=12), info={'str_minus_1_to_null': True})
    """Stop area Y coordinate (WGS84)"""

    abbr: Column[Optional[str]] = Column("STOP_AREA_SHORT_NAME", String(length=5))
    """Stop area abbreviation"""
    name: Column[str] = Column("STOP_AREA_LONG_NAME", String(length=20), nullable=False, info={'keep_empty_str': True})
    """Stop area name"""
    level: Column[Optional[int]] = Column("STOP_AREA_LEVEL", Integer())
    """Stop area level information"""

    type: Column[Optional[StopAreaType]] = Column("STOP_AREA_TYPE", IntEnum(StopAreaType))
    """Stop area type"""

    ifopt: Column[Optional[str]] = Column("GLOBAL_ID", String(length=100))
    """IFOPT / global id"""

    gis_mot_flag: Column[Optional[int]] = Column("GIS_MOT_FLAG", Integer())
    """GIS MOT bit flags"""

    valid_from: Column[Optional[date]] = Column("VALID_FROM", DinoDate)
    """Valid from date"""
    valid_to: Column[Optional[date]] = Column("VALID_TO", DinoDate)
    """Valid until date"""

    stop: RelationshipProperty[Stop] = relationship(Stop, back_populates="areas")
    """`Stop`"""
    points: RelationshipProperty[Sequence[StopPoint]] = relationship("StopPoint", viewonly=True)
    """`StopPoint`s of this stop area"""
    links_from: RelationshipProperty[Sequence[Link]] = relationship("Link", foreign_keys="[Link.version_id, Link.from_stop_id, Link.from_area_id]", viewonly=True)
    """`Link`s from this stop area"""
    links_to: RelationshipProperty[Sequence[Link]] = relationship("Link", foreign_keys="[Link.version_id, Link.to_stop_id, Link.to_area_id]", viewonly=True)
    """`Link`s to this stop area"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, stop_id], [Stop.version_id, Stop.id]),
    )

    def __repr__(self) -> str:
        return f"<StopArea(version_id={self.version_id}, stop_id={self.stop_id} ({self.stop.name}), id={self.id}, name={self.name}, type={self.type}, ifopt={self.ifopt})>"

    __abstract__ = False


class StreetAccess(Enum):
    unknown = 0
    level = 1
    small_step = 2
    large_step = 3


class StopPoint(Base):
    """
    Stopping point

    Depicts a platform of a `Stop` a vehicle can stop at.

    Primary key: `version_id` & `stop_id` & `id`
    """
    _din_file = "stop_point.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    stop_id: Column[int] = Column("STOP_NR", Integer(), primary_key=True)
    """Stop id"""

    area_id: Column[int] = Column("STOP_AREA_NR", Integer(), primary_key=False, nullable=False)
    """Stop area id"""

    id: Column[int] = Column("STOPPING_POINT_NR", Integer(), primary_key=True)
    """Stop point id"""

    pos_x: Column[Optional[str]] = Column("STOPPING_POINT_POS_X", String(length=12), info={'str_minus_1_to_null': True})
    """Stop point X coordinate (WGS84)"""
    pos_y: Column[Optional[str]] = Column("STOPPING_POINT_POS_Y", String(length=12), info={'str_minus_1_to_null': True})
    """Stop point Y coordinate (WGS84)"""

    gis_segment_id: Column[Optional[int]] = Column("SEGMENT_ID", Integer())
    """ID of GIS segment"""
    gis_segment_dist: Column[Optional[int]] = Column("SEGMENT_DIST", Integer())
    """Distance from first segment node (m)"""

    stop_rbl_nr: Column[Optional[int]] = Column("STOP_RBL_NR", Integer())
    """VDV 454 RBL stopping point number"""

    name: Column[Optional[str]] = Column("STOPPING_POINT_SHORTNAME", String(length=255))
    """Stop point name"""

    purpose_ttb: Column[Optional[bool]] = Column("PURPOSE_TTB", Boolean())
    """Purpose: timetable book"""
    purpose_stt: Column[Optional[bool]] = Column("PURPOSE_STT", Boolean())
    """Purpose: stop time table"""
    purpose_jp: Column[Optional[bool]] = Column("PURPOSE_JP", Boolean())
    """Purpose: journey planner"""
    purpose_cbs: Column[Optional[bool]] = Column("PURPOSE_CBS", Boolean())
    """Purpose: central station"""

    ifopt: Column[Optional[str]] = Column("GLOBAL_ID", String(length=100))
    """IFOPT / global id"""

    gis_mot_flag: Column[Optional[int]] = Column("GIS_MOT_FLAG", Integer())
    """GIS MOT bit flags"""

    valid_from: Column[Optional[date]] = Column("VALID_FROM", DinoDate)
    """Valid from date"""
    valid_to: Column[Optional[date]] = Column("VALID_TO", DinoDate)
    """Valid until date"""

    platform_height: Column[Optional[int]] = Column("PLATFORM_HEIGHT", Integer())
    """Platform height in mm above rail/street surface"""
    rail_centre_dist: Column[Optional[int]] = Column("DISTANCE_TO_RAIL_CENTRE", Integer())
    """Horizontal distance of platform edge to rail centre"""
    has_mobile_ramp: Column[Optional[bool]] = Column("HAS_MOBILE_RAMP", Boolean())
    """Whether the platform has a mobile ramp"""
    boarding_space: Column[Optional[int]] = Column("BOARDING_SPACE", Integer())
    """Space in mm provided on pavement for operating the equipment"""

    street_access: Column[Optional[StreetAccess]] = Column("STREET_ACCESS", IntEnum(StreetAccess))
    """Accessibility of platform from street (unknown/level/small/large step)"""

    stop: RelationshipProperty[Stop] = relationship(Stop, back_populates="points")
    """`Stop`"""
    area: RelationshipProperty[StopArea] = relationship(StopArea, viewonly=True)
    """`StopArea` this stop point is in"""
    links_from: RelationshipProperty[Sequence[Link]] = relationship("Link", foreign_keys="[Link.version_id, Link.from_stop_id, Link.from_point_id]", viewonly=True)
    """`Link`s from this stop point"""
    links_to: RelationshipProperty[Sequence[Link]] = relationship("Link", foreign_keys="[Link.version_id, Link.to_stop_id, Link.to_point_id]", viewonly=True)
    """`Link`s to this stop point"""
    courses: RelationshipProperty[Sequence[Course]] = relationship("Course", secondary="route", viewonly=True)
    """`DINO2.model.network.Course`s with this stop point on route"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, stop_id], [Stop.version_id, Stop.id]),
        ForeignKeyConstraint([version_id, stop_id, area_id], [StopArea.version_id, StopArea.stop_id, StopArea.id]),
    )

    def __repr__(self) -> str:
        return f"<StopPoint(version_id={self.version_id}, stop={self.stop}, area={self.area}, id={self.id}, name={self.name}, ifopt={self.ifopt})>"

    __abstract__ = False


class Link(Base):
    """
    Link -- for way geometry between `Stop`/`StopArea`/`StopPoint` objects

    Only one link per branch is allowed between two specific elements.

    Primary key: `version_id` & `id` & `branch_id` & `from_stop_id` & _`from_area_id`_ & `to_stop_id` & _`to_area_id`_ & _`to_point_id`_
    """
    _din_file = "link.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    id: Column[int] = Column("LINK_ID", Integer(), primary_key=True)
    """Link id"""

    branch_id: Column[int] = Column("BRANCH_NR", Integer(), primary_key=True)
    """Branch id"""

    from_stop_id: Column[int] = Column("ORIG_STOP_NR", Integer(), primary_key=True)
    """From stop id"""
    from_area_id: Column[Optional[int]] = Column("ORIG_STOP_AREA_NR", Integer(), primary_key=True, nullable=True)
    """From stop area id"""
    from_point_id: Column[Optional[int]] = Column("STOPPING_POINT_NR", Integer(), primary_key=False, nullable=True)
    """From stop point id"""

    to_stop_id: Column[int] = Column("DEST_STOP_NR", Integer(), primary_key=True)
    """To stop id"""
    to_area_id: Column[Optional[int]] = Column("DEST_STOP_AREA_NR", Integer(), primary_key=True, nullable=True)
    """To stop area id"""
    to_point_id: Column[Optional[int]] = Column("DEST_STOPPING_POINT_NR", Integer(), primary_key=True, nullable=True)
    """To stop point id"""

    length: Column[Optional[int]] = Column("LENGTH", Integer())
    """Length (m)"""
    gis_length: Column[Optional[int]] = Column("GIS_LENGTH", Integer())
    """GIS Length (m)"""

    from_stop: RelationshipProperty[Stop] = relationship(Stop, foreign_keys="[Link.version_id, Link.from_stop_id]", viewonly=True)
    """From `Stop`"""
    from_area: RelationshipProperty[Optional[StopArea]] = relationship(StopArea, foreign_keys="[Link.version_id, Link.from_stop_id, Link.from_area_id]", viewonly=True)
    """From `StopArea`"""
    from_point: RelationshipProperty[Optional[StopPoint]] = relationship(StopPoint, foreign_keys="[Link.version_id, Link.from_stop_id, Link.from_point_id]", viewonly=True)
    """From `StopPoint`"""
    to_stop: RelationshipProperty[Stop] = relationship(Stop, foreign_keys="[Link.version_id, Link.to_stop_id]", viewonly=True)
    """To `Stop`"""
    to_area: RelationshipProperty[Optional[StopArea]] = relationship(StopArea, foreign_keys="[Link.version_id, Link.to_stop_id, Link.to_area_id]", viewonly=True)
    """To `StopArea`"""
    to_point: RelationshipProperty[Optional[StopPoint]] = relationship(StopPoint, foreign_keys="[Link.version_id, Link.to_stop_id, Link.to_point_id]", viewonly=True)
    """To `StopPoint`"""
    geometry: RelationshipProperty[Sequence[LinkGeometryPoint]] = relationship("LinkGeometryPoint", order_by="asc(LinkGeometryPoint.consec_pt_nr)", back_populates="link")
    """`LinkGeometryPoint`s of this link"""
    force_points: RelationshipProperty[Sequence[LinkForcePoint]] = relationship("LinkForcePoint", order_by="asc(LinkForcePoint.consec_pt_nr)", back_populates="link")
    """`LinkForcePoint`s of this link"""
    branch: RelationshipProperty[Branch] = relationship("Branch", viewonly=True)
    """`DINO2.model.operational.Branch`"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="links")
    """`DINO2.model.Version`"""

    @property
    def wkt(self) -> str:
        """Get WKT (well known text) representation of link geometry"""
        text = "LINESTRING ("
        geomlist: Sequence[LinkPoint] = self.geometry or self.force_points
        for p in geomlist:
            text += f"{p.pos_x} {p.pos_y}, "
        return text[:-2] + ")"

    def wkt_m(self, ts_start: int, ts_end: int) -> str:
        """Get WKT representation with time measures for specific start and end timestamp"""
        text = "LINESTRING M ("
        geomlist: Sequence[LinkPoint] = self.geometry or self.force_points
        # todo: distance statt index..
        for i, p in enumerate(geomlist):
            m = int(ts_start + i * (ts_end - ts_start) / (len(geomlist) - 1))
            text += f"{p.pos_x} {p.pos_y} {m}, "
        return text[:-2] + ")"

    __table_args__ = (
        ForeignKeyConstraint([version_id, branch_id], ["branch.VERSION", "branch.BRANCH_NR"]),
        ForeignKeyConstraint([version_id, from_stop_id], [Stop.version_id, Stop.id]),
        ForeignKeyConstraint([version_id, from_stop_id, from_area_id], [StopArea.version_id, StopArea.stop_id, StopArea.id]),
        ForeignKeyConstraint([version_id, from_stop_id, from_point_id], [StopPoint.version_id, StopPoint.stop_id, StopPoint.id]),
        ForeignKeyConstraint([version_id, to_stop_id], [Stop.version_id, Stop.id]),
        ForeignKeyConstraint([version_id, to_stop_id, to_area_id], [StopArea.version_id, StopArea.stop_id, StopArea.id]),
        ForeignKeyConstraint([version_id, to_stop_id, to_point_id], [StopPoint.version_id, StopPoint.stop_id, StopPoint.id]),
    )

    def __repr__(self) -> str:
        return f"<Link(version_id={self.version_id}, id={self.id}, from_stop_id={self.from_stop_id}, from_area_id={self.from_area_id}, from_point_id={self.from_point_id}, to_stop_id={self.to_stop_id}, to_area_id={self.to_area_id}, to_point_id={self.to_point_id})>"

    __abstract__ = False


class LinkPoint(Base):
    """
    Abstract base class for points of `Link`s.
    """
    __abstract__ = True

    @declared_attr
    def version_id(cls) -> Column[int]:
        """Version id"""
        return Column("VERSION", Integer(), ForeignKey(Version.id), nullable=False)

    link_id: Column[int] = Column("LINK_ID", Integer(), nullable=False)
    """Link id"""

    consec_pt_nr: Column[int] = Column("LINK_CONSEC_PT_NR", Integer(), nullable=False)
    """Consecutive point number"""

    pos_x: Column[str] = Column("LINK_PT_X", String(length=11), nullable=False, info={'str_minus_1_to_null': True})
    """Point X coordinate (WGS84)"""
    pos_y: Column[str] = Column("LINK_PT_Y", String(length=11), nullable=False, info={'str_minus_1_to_null': True})
    """Point Y coordinate (WGS84)"""

    _link_bp_name: str
    @declared_attr
    def link(cls) -> RelationshipProperty[Link]:
        """`Link`"""
        return relationship(Link, back_populates=cls._link_bp_name)

    @declared_attr
    def version(cls) -> RelationshipProperty[Version]:
        """`DINO2.model.Version`"""
        return relationship("Version", viewonly=True)

    @declared_attr
    def __table_args__(cls):
        return (
            PrimaryKeyConstraint(cls.version_id, cls.link_id, cls.consec_pt_nr),
            ForeignKeyConstraint([cls.version_id, cls.link_id], [Link.version_id, Link.id])
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(version_id={self.version_id}, link_id={self.link_id}, consec_pt_nr={self.consec_pt_nr}, pos_x={self.pos_x}, pos_y={self.pos_y})>"


class LinkGeometryPoint(LinkPoint):
    """
    Coordinates of a point on a `Link` geometry.

    Primary key: `version_id` & `link_id` & `consec_pt_nr`
    """
    __abstract__ = False
    _din_file = "link_geometry.din"
    _link_bp_name = "geometry"


class LinkForcePoint(LinkPoint):
    """
    Coordinates of a force point of a `Link` geometry.

    Primary key: `version_id` & `link_id` & `consec_pt_nr`
    """
    __abstract__ = False
    _din_file = "link_force_point.din"
    _link_bp_name = "force_points"
