# -*- coding: utf-8 -*-
"""DINO 2.1 fare zone data"""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship, RelationshipProperty
from typing import Optional, Sequence, TYPE_CHECKING

from . import Base, Version

if TYPE_CHECKING:
    from .location import Stop


class FareZone(Base):
    """
    Fare zone

    Primary key: `version_id` & `id`
    """
    _din_file = "fare_zone.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    id: Column[int] = Column("FARE_ZONE_NR", Integer(), primary_key=True)
    """Fare zone id"""

    name: Column[Optional[str]] = Column("FARE_ZONE_LONG_NAME", String(length=50))
    """Fare zone long name"""
    neutral: Column[Optional[bool]] = Column("FARE_ZONE_TYPE", Boolean())
    """Fare zone type/neutrality (False = normal)"""
    color: Column[Optional[int]] = Column("FARE_ZONE_COLOR", Integer())
    """Fare zone color (RGB 3x8 bit)"""

    stops: RelationshipProperty[Sequence[Stop]] = relationship("Stop", primaryjoin="and_(FareZone.version_id==Stop.version_id, or_(FareZone.id==Stop.fz1id,FareZone.id==Stop.fz2id,FareZone.id==Stop.fz3id,FareZone.id==Stop.fz4id,FareZone.id==Stop.fz5id,FareZone.id==Stop.fz6id))", viewonly=True)
    """`DINO2.model.location.Stop`s in this fare zone"""
    _neighbourgroupingsF = relationship("NeighbourFareZone", foreign_keys="[NeighbourFareZone.version_id, NeighbourFareZone.farezone_id]", viewonly=True)
    _neighbourgroupingsN = relationship("NeighbourFareZone", foreign_keys="[NeighbourFareZone.version_id, NeighbourFareZone.neighbour_id]", viewonly=True)
    neighbours: RelationshipProperty[Sequence[FareZone]] = relationship("FareZone", secondary="neighbour_fare_zone", primaryjoin="and_(FareZone.version_id==NeighbourFareZone.version_id, FareZone.id==NeighbourFareZone.farezone_id)", secondaryjoin="and_(FareZone.version_id==NeighbourFareZone.version_id, FareZone.id==NeighbourFareZone.neighbour_id)", back_populates="neighbours")
    """Neighbour `FareZone`s"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="farezones")
    """`DINO2.model.Version`"""

    def __repr__(self) -> str:
        return f"<FareZone(version_id={self.version_id}, id={self.id}, name={self.name}, neutral={self.neutral}, color={self.color})>"


class NeighbourFareZone(Base):
    """
    Neighbour fare zone grouping

    Primary key: `version_id` & `farezone_id` & _`neighbour_id`_
    """
    _din_file = "neighbour_fare_zone.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""

    farezone_id: Column[int] = Column("FARE_ZONE", Integer(), primary_key=True)
    """Fare zone id"""

    neighbour_id: Column[Optional[int]] = Column("NEIGHBOUR_FARE_ZONE", Integer(), primary_key=True, nullable=True)
    """Neighbour fare zone id (can be None)"""

    farezone: RelationshipProperty[FareZone] = relationship("FareZone", foreign_keys=[version_id, farezone_id], viewonly=True)
    """`FareZone`"""
    neighbour: RelationshipProperty[Optional[FareZone]] = relationship("FareZone", foreign_keys=[version_id, neighbour_id], viewonly=True)
    """Neighbour `FareZone`"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="farezonegroupings")
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, farezone_id], [FareZone.version_id, FareZone.id]),
        ForeignKeyConstraint([version_id, neighbour_id], [FareZone.version_id, FareZone.id])
    )

    def __repr__(self) -> str:
        return f"<NeighbourFareZone(version_id={self.version_id}, farezone_id={self.farezone_id}, neighbour_id={self.neighbour_id})>"
