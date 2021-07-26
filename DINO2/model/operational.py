# -*- coding: utf-8 -*-
"""DINO 2.1 operational data"""

from __future__ import annotations

from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.orm import relationship, RelationshipProperty
from typing import Optional, Sequence, TYPE_CHECKING

from ..types import IntEnum
from . import Base, Version

if TYPE_CHECKING:
    from .location import Link
    from .network import Course, CourseStop
    from .schedule import Trip


class Branch(Base):
    """
    Operational branch

    Primary key: `version_id` & `id`
    """
    _din_file = "branch.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    id: Column[int] = Column("BRANCH_NR", Integer(), primary_key=True)
    """Branch id"""

    abbr: Column[Optional[str]] = Column("STR_BRANCH_NAME", String(length=6))
    """Short branch name"""
    name: Column[str] = Column("BRANCH_NAME", String(length=40), nullable=False)
    """Branch name"""

    links: RelationshipProperty[Sequence[Link]] = relationship("Link", viewonly=True)
    """`DINO2.model.location.Link`s of this branch"""
    vehicle_destination_texts: RelationshipProperty[Sequence[VehicleDestinationText]] = relationship("VehicleDestinationText", viewonly=True)
    """`VehicleDestinationText`s of this branch"""
    default_branch_operators: RelationshipProperty[Sequence[Operator]] = relationship("Operator", viewonly=True)
    """`Operator`s that have this branch as default branch"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="branches")
    """`DINO2.model.Version`"""

    def __repr__(self) -> str:
        return f"<Branch(version_id={self.version_id}, id={self.id}, abbr={self.abbr}, name={self.name})>"

    __abstract__ = False


class Operator(Base):
    """
    Operator

    Primary key: `version_id` & `id`
    """
    _din_file = "operator.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    id: Column[str] = Column("OP_CODE", String(length=10), primary_key=True)
    """Operator number"""

    default_branch_id: Column[Optional[int]] = Column("OP_BRANCH_NR", Integer())
    """Default branch id"""

    abbr: Column[Optional[str]] = Column("OP_SHORT_NAME", String(length=7))
    """Short operator name"""
    name: Column[str] = Column("OP_LONG_NAME", String(length=255), nullable=False)
    """Operator name"""
    pub_abbr: Column[Optional[str]] = Column("OP_PUBLIC_SHORT_NAME", String(length=7))
    """Public operator abbreviation"""
    full_name: Column[Optional[str]] = Column("OP_LICENCE_NAME", String(length=255))
    """Operator full/licensed name"""
    trading_name: Column[Optional[str]] = Column("OP_TRADING_NAME", String(length=255))
    """Operator trading name"""
    vat_registered: Column[Optional[bool]] = Column("OP_VAT_REGISTERED_FLAG", Boolean())
    """Whether operator is VAT registered"""

    default_branch: RelationshipProperty[Optional[Branch]] = relationship(Branch, viewonly=True)
    """Default `Branch`"""
    branch_offices: RelationshipProperty[Sequence[OperatorBranchOffice]] = relationship("OperatorBranchOffice", back_populates="operator")
    """`OperatorBranchOffice`s of this operator"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="operators")
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, default_branch_id], [Branch.version_id, Branch.id]),
    )

    def __repr__(self) -> str:
        return f"<Operator(version_id={self.version_id}, id={self.id}, abbr={self.abbr}, name={self.name})>"

    __abstract__ = False


class OperatorBranchOffice(Base):
    """
    Operator branch office.

    At least one per operator is required.

    Primary key: `version_id` & `operator_id` & `id`
    """
    _din_file = "operator_branch_office.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    operator_id: Column[str] = Column("OP_CODE", String(length=10), primary_key=True)
    """Operator number"""

    id: Column[str] = Column("OBO_SHORT_NAME", String(length=10), primary_key=True)
    """Operator branch office id / short name"""

    internal_phone: Column[Optional[str]] = Column("OBO_INTERNAL_PHONE", String(length=50))
    """Internal phone number"""
    public_phone: Column[Optional[str]] = Column("OBO_PUBLIC_PHONE", String(length=50))
    """Public phone number"""
    fax: Column[Optional[str]] = Column("OBO_FAX_NR", String(length=50))
    """Internal phone number"""
    address: Column[Optional[str]] = Column("OBO_ADDRESS", String(length=500))
    """Street address of office"""
    contact_address: Column[Optional[str]] = Column("OBO_CONTAC_ADDRESS", String(length=500))
    """Contact address of office"""
    url: Column[Optional[str]] = Column("OBO_URL", String(length=255))
    """URL of office"""

    operator: RelationshipProperty[Operator] = relationship(Operator, back_populates="branch_offices")
    """`Operator`"""
    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, operator_id], [Operator.version_id, Operator.id]),
    )

    def __repr__(self) -> str:
        return f"<OperatorBranchOffice(version_id={self.version_id}, id={self.id})>"

    __abstract__ = False


class TransferMOT(Enum):
    """
    "Transfer" means of transport

    Used to group `MeansOfTransportDesc` to more general MOT descriptions for usage for transfer times
    """
    train = 0
    commuter_rail = 1
    underground = 2
    suburban_rail = 3
    tram = 4
    city_bus = 5
    regional_bus = 6
    express_bus = 7
    cable_or_cog_wheel = 8
    ship = 9
    shared_taxi = 10
    other = 11
    aircraft = 12


class MeansOfTransportDesc(Base):
    """
    Means of transport (_MOT_)

    Primary key: `version_id` & `id`
    """
    _din_file = "means_of_transport_desc.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    id: Column[int] = Column("MOT_NR", Integer(), primary_key=True)
    """MOT id"""

    name: Column[str] = Column("MOT_NAME", String(length=20), nullable=False)
    """MOT name"""

    tmot: Column[TransferMOT] = Column("TMOT_NR", IntEnum(TransferMOT), nullable=False)
    """Transfer MOT number"""

    version: RelationshipProperty[Version] = relationship("Version", back_populates="means_of_transport")
    """`DINO2.model.Version`"""

    def __repr__(self) -> str:
        return f"<MeansOfTransportDesc(version_id={self.version_id}, id={self.id}, name={self.name}, tmot={self.tmot})>"

    __abstract__ = False


class AccessibilityEquipment(Enum):
    no_lift = 0
    lift = 1
    lift_or_ramp = 2


class VehicleType(Base):
    """
    Vehicle type

    Primary key: `version_id` & `id`
    """
    _din_file = "vehicle_type.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    id: Column[int] = Column("VEH_TYPE_NR", Integer(), primary_key=True)
    """Vehicle type id"""

    seats: Column[Optional[int]] = Column("VEH_TYPE_SEATS", Integer())
    """Number of seats"""
    straps: Column[Optional[int]] = Column("VEH_TYPE_STRAPS", Integer())
    """Number of straps"""
    places_for_disabled: Column[Optional[int]] = Column("PLACES_FOR_DISABLED_PERSONS", Integer())
    """Number of places for disabled persons"""

    desc: Column[Optional[str]] = Column("VEH_TYPE_TEXT", String(length=40))
    """Vehicle type description"""
    abbr: Column[Optional[str]] = Column("STR_VEH_TYPE", String(length=4))
    """Vehicle type abbreviation"""

    door_width: Column[Optional[int]] = Column("VEH_TYPE_DOOR_WIDTH", Integer())
    """Width of vehicle doors (mm)"""
    width: Column[Optional[int]] = Column("VEH_TYPE_WIDTH", Integer())
    """Width of vehicle(mm)"""
    height: Column[Optional[int]] = Column("VEH_TYPE_HEIGHT", Integer())
    """Height of floor above rail/street surface (mm)"""

    accessibility_equipment: Column[Optional[AccessibilityEquipment]] = Column("VEH_TYPE_ACCESS_EQUIP", IntEnum(AccessibilityEquipment))
    """Accessibility equipment"""

    version: RelationshipProperty[Version] = relationship("Version", back_populates="vehicle_types")
    """`DINO2.model.Version`"""

    def __repr__(self) -> str:
        return f"<VehicleType(version_id={self.version_id}, id={self.id}, desc={self.desc}, abbr={self.abbr})>"

    __abstract__ = False


class VehicleDestinationText(Base):
    """
    Vehicle destination text (_VDT_)

    Primary key: `version_id` & _`branch_id`_ & `id`
    """
    _din_file = "vehicle_destination_text.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    branch_id: Column[Optional[int]] = Column("BRANCH_NR", Integer(), primary_key=True, nullable=True)
    """Branch id"""

    id: Column[int] = Column("VDT_NR", Integer(), primary_key=True)
    """VDT id"""

    driver_text1: Column[Optional[str]] = Column("VDT_TEXT_DRIVER1", String(length=160))
    """First row of text shown to driver"""
    driver_text2: Column[Optional[str]] = Column("VDT_TEXT_DRIVER2", String(length=160))
    """Second row of text shown to driver"""

    front_text1: Column[Optional[str]] = Column("VDT_TEXT_FRONT1", String(length=160))
    """First row of vehicle front text"""
    front_text2: Column[Optional[str]] = Column("VDT_TEXT_FRONT2", String(length=160))
    """Second row of vehicle front text"""
    front_text3: Column[Optional[str]] = Column("VDT_TEXT_FRONT3", String(length=160))
    """
    First row of alternative vehicle front text (displays usually switch between `front_text1`+`front_text2` and `front_text3`+`front_text4`)
    """
    front_text4: Column[Optional[str]] = Column("VDT_TEXT_FRONT4", String(length=160))
    """Second row of alternative vehicle front text"""

    side_text1: Column[Optional[str]] = Column("VDT_TEXT_SIDE1", String(length=160))
    """First row of vehicle side text"""
    side_text2: Column[Optional[str]] = Column("VDT_TEXT_SIDE2", String(length=160))
    """Second row of vehicle side text"""
    side_text3: Column[Optional[str]] = Column("VDT_TEXT_SIDE3", String(length=160))
    """
    First row of alternative vehicle side text (displays usually switch between `side_text1`+`side_text2` and `side_text3`+`side_text4`)
    """
    side_text4: Column[Optional[str]] = Column("VDT_TEXT_SIDE4", String(length=160))
    """Second row of alternative vehicle side text"""

    name: Column[Optional[str]] = Column("VDT_LONG_NAME", String(length=160))
    """VDT name"""
    short_name: Column[Optional[str]] = Column("VDT_SHORT_NAME", String(length=68))
    """VDT short name"""

    branch: RelationshipProperty[Optional[Branch]] = relationship(Branch, viewonly=True)
    """`Branch`"""
    trips: RelationshipProperty[Sequence[Trip]] = relationship("Trip", secondary="trip_vdt", viewonly=True)
    """`DINO2.model.schedule.Trip`s this vehicle destination text is used on"""
    courses: RelationshipProperty[Sequence[Course]] = relationship("Course", secondary="trip_vdt", viewonly=True)
    """`DINO2.model.network.Course`s this vehicle destination text is used on"""
    course_stops: RelationshipProperty[Sequence[CourseStop]] = relationship("CourseStop", secondary="trip_vdt", viewonly=True)
    """`DINO2.model.network.CourseStop`s this vehicle destination text is changed to at"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="vehicle_destination_texts")
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, branch_id], [Branch.version_id, Branch.id]),
    )

    def __repr__(self) -> str:
        return f"<VehicleDestinationText(version_id={self.version_id}, branch_id={self.branch_id}, id={self.id}, name={self.name}, short_name={self.short_name})>"

    __abstract__ = False
