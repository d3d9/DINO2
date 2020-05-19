# -*- coding: utf-8 -*-
"""DINO 2.1 calendar data"""

from __future__ import annotations

from calendar import monthrange, month_abbr
from collections import UserString
from datetime import date, timedelta
from sqlalchemy import Column, String, Integer, ForeignKey, ForeignKeyConstraint, and_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import composite, CompositeProperty, relationship, RelationshipProperty
from typing import Optional, Tuple, Set, FrozenSet, TYPE_CHECKING, Sequence

from ..types import DinoDate
from . import Base, Version


class DayType(Base):
    """
    Day type description

    Usually one for each day of a week.

    Primary key: `version_id` & `id`
    """
    _din_file = "day_type.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""
    id: Column[int] = Column("DAY_TYPE_NR", Integer(), primary_key=True)
    """Day type id"""

    text: Column[Optional[str]] = Column("DAY_TYPE_TEXT", String(length=40))
    """Day type description"""
    abbr: Column[Optional[str]] = Column("STR_DAY_TYPE", String(length=2))
    """Day type abbreviation"""

    dayattrs: RelationshipProperty[Sequence[DayAttribute]] = relationship("DayAttribute", secondary="day_type_2_day_attribute", viewonly=True)
    """`DayAttribute` groups this day type is part of"""
    _daygroupings: RelationshipProperty[Sequence[DayGrouping]] = relationship("DayGrouping", viewonly=True)
    days: RelationshipProperty[Sequence[CalendarDay]] = relationship("CalendarDay", back_populates="daytype")
    """`CalendarDay`s with this day type"""
    version: RelationshipProperty[Version] = relationship("Version", back_populates="daytypes")
    """`DINO2.model.Version`"""

    def __repr__(self) -> str:
        return f"<DayType(version_id={self.version_id}, id={self.id}, text={self.text}, abbr={self.abbr})>"


class DayAttribute(Base):
    """
    Day attribute description (group of day types)

    For example a grouping called "weekend" of the day types for Saturday and Sunday.  
    Used in `DINO2.model.schedule.Trip`s to define the base set of days a trip is valid on, additionally restricted using `Restriction`s.

    Primary key: `version_id` & `id`
    """
    _din_file = "day_attribute.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""
    id: Column[int] = Column("DAY_ATTRIBUTE_NR", Integer(), primary_key=True)
    """Day attribute group id"""

    text: Column[str] = Column("DAY_ATTRIBUTE_TEXT", String(length=40), nullable=False)
    """Day attribute description"""
    abbr: Column[Optional[str]] = Column("STR_DAY_ATTRIBUTE", String(length=2))
    """Day attribute abbreviation"""

    daytypes: RelationshipProperty[Sequence[DayType]] = relationship("DayType", secondary="day_type_2_day_attribute", viewonly=True)
    """`DayType`s that belong to this day attribute group"""
    days: RelationshipProperty[Sequence[CalendarDay]] = relationship("CalendarDay", secondary="join(DayGrouping, DayType, and_(DayGrouping.version_id == DayType.version_id, DayGrouping.daytype_id == DayType.id))", viewonly=True)
    """`CalendarDay`s of the day types that belong to this day attribute grouping"""
    _daygroupings: RelationshipProperty[Sequence[DayGrouping]] = relationship("DayGrouping", viewonly=True)
    version: RelationshipProperty[Version] = relationship("Version", back_populates="dayattrs")
    """`DINO2.model.Version`"""

    @property
    def dates(self) -> FrozenSet[date]:
        """Valid dates of the day types that belong to this day attribute grouping"""
        return frozenset(cd.day for cd in self.days)

    def __repr__(self) -> str:
        return f"<DayAttribute(version_id={self.version_id}, id={self.id}, text={self.text}, abbr={self.abbr})>"


class DayGrouping(Base):
    """
    Association class for grouping day types as day attribute groups

    Primary key: `version_id` & `daytype_id` & `dayattr_id`
    """
    _din_file = "day_type_2_day_attribute.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""
    daytype_id: Column[int] = Column("DAY_TYPE_NR", Integer(), primary_key=True)
    """Day type id"""
    _daytype: RelationshipProperty[DayType] = relationship("DayType", viewonly=True)
    dayattr_id: Column[int] = Column("DAY_ATTRIBUTE_NR", Integer(), primary_key=True)
    """Day attribute id"""
    _dayattr: RelationshipProperty[DayAttribute] = relationship("DayAttribute", viewonly=True)

    version: RelationshipProperty[Version] = relationship("Version", back_populates="daygroupings")
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, daytype_id], [DayType.version_id, DayType.id]),
        ForeignKeyConstraint([version_id, dayattr_id], [DayAttribute.version_id, DayAttribute.id]),
    )

    def __repr__(self) -> str:
        return f"<DayGrouping(version_id={self.version_id}, daytype_id={self.daytype_id}, dayattr_id={self.dayattr_id})>"


class CalendarDay(Base):
    """
    Schedule day with its respective `DayType`

    Primary key: `version_id` & `day`
    """
    _din_file = "day_type_calendar.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""
    day: Column[date] = Column("DAY", DinoDate, primary_key=True)
    """Date of day"""

    daytype_id: Column[int] = Column("DAY_TYPE_NR", Integer(), nullable=False)
    """Day type id"""
    daytype: RelationshipProperty[DayType] = relationship("DayType", back_populates="days")
    """Day type"""

    text: Column[Optional[str]] = Column("DAY_TEXT", String(length=40))
    """Day description"""

    version: RelationshipProperty[Version] = relationship("Version", viewonly=True)
    """`DINO2.model.Version`"""

    __table_args__ = (
        ForeignKeyConstraint([version_id, daytype_id], [DayType.version_id, DayType.id]),
    )

    def __repr__(self) -> str:
        return f"<CalendarDay(version_id={self.version_id}, day={self.day}, daytype={self.daytype}, text={self.text})>"


class RestrictionText(UserString):
    """
    Class for composite restriction text column

    Method `from_columns` is used for creation from five separate columns.
    Length is limited to 60 characters per column.
    """
    CompositeTuple = Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]

    def __init__(self, text: Optional[str]):
        self.data = text or ''

    @classmethod
    def from_columns(cls, rt1: Optional[str], rt2: Optional[str], rt3: Optional[str], rt4: Optional[str], rt5: Optional[str]):
        def _n(s: Optional[str]) -> str:
            v = s or ''
            assert len(v) <= 60
            return v
        return cls(_n(rt1) + _n(rt2) + _n(rt3) + _n(rt4) + _n(rt5))

    @staticmethod
    def split_text(text: str) -> CompositeTuple:
        return tuple((text[_:_+60] or None) for _ in range(0, 60*5, 60))

    def __composite_values__(self) -> CompositeTuple:
        return self.__class__.split_text(self.data)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return other.__composite_values__() == self.__composite_values__()
        elif isinstance(other, UserString):
            return other.data == self.data
        else:
            return other == self.data

    def __ne__(self, other):
        return not self.__eq__(other)


class _RTComparator(CompositeProperty.Comparator):
    # todo: nicht nur eq; und bessere vorgehensweise
    def __eq__(self, other):
        if hasattr(other, '__composite_values__'):
            values = other.__composite_values__()
        else:
            values = RestrictionText.split_text(other or '')
        return and_(*(s == o for s, o in zip(self.__clause_element__().clauses, values)))


class Restriction(Base):
    """
    Restriction of service

    Used additionally to `DayAttribute` groups for `DINO2.model.schedule.Trip`s.  
    Used for example for special services operating only for a specific time period, or services not operating in vacation times.

    Primary key: `version_id` & `id` & _`line`_
    """
    _din_file = "service_restriction.din"

    version_id: Column[int] = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
    """Version id"""
    id: Column[str] = Column("RESTRICTION", String(length=5), primary_key=True)
    """Restriction id"""

    _rt1: Column[Optional[str]] = Column("RESTRICT_TEXT1", String(length=60))
    _rt2: Column[Optional[str]] = Column("RESTRICT_TEXT2", String(length=60))
    _rt3: Column[Optional[str]] = Column("RESTRICT_TEXT3", String(length=60))
    _rt4: Column[Optional[str]] = Column("RESTRICT_TEXT4", String(length=60))
    _rt5: Column[Optional[str]] = Column("RESTRICT_TEXT5", String(length=60))

    text: CompositeProperty = composite(RestrictionText.from_columns, _rt1, _rt2, _rt3, _rt4, _rt5, comparator_factory=_RTComparator)
    """Restriction description"""

    daystring: Column[str] = Column("RESTRICTION_DAYS", String(length=192), nullable=False)

    @staticmethod
    def calc_dateset(daystring: str, date_from: date, date_until: date) -> FrozenSet[date]:
        """Get valid dates for given restriction string and start/end date"""
        dates: Set[date] = set()
        currentyear, currentmonth = date_from.year, date_from.month
        firstday, lastday = date_from.day, date_until.day
        for o in range(0, len(daystring), 8):
            bits = bin(int(daystring[o:o+8], 16))[2:].zfill(32)[1:][::-1]
            if currentmonth == 13:
                currentmonth = 1
                currentyear += 1
            daysinmonth = monthrange(currentyear, currentmonth)[1]
            for x in range(1, daysinmonth+1):
                if not (((not o) and x < firstday) or (o == len(daystring) - 8 and x > lastday)) and bool(int(bits[x-1])):
                    dates.add(date(currentyear, currentmonth, x))
            currentmonth += 1
        return frozenset(dates)

    _dates: Optional[Tuple[str, FrozenSet[date]]] = None

    @property
    def dates(self) -> FrozenSet[date]:
        """Valid dates"""
        if self._dates is None or self._dates[0] != self.daystring:
            self._dates = self.daystring, self.__class__.calc_dateset(self.daystring, self.date_from, self.date_until)
        return self._dates[1]

    date_from: Column[date] = Column("DATE_FROM", DinoDate, nullable=False)
    """Date of the beginning of the restriction"""
    date_until: Column[date] = Column("DATE_UNTIL", DinoDate, nullable=False)
    """Date of last day of the restriction"""

    line: Column[Optional[int]] = Column("LINE_NR", Integer(), primary_key=True, nullable=True)
    """Line for which this restriction is valid"""

    version: RelationshipProperty[Version] = relationship("Version", back_populates="restrictions")
    """`DINO2.model.Version`"""

    def __repr__(self) -> str:
        return f"<Restriction(version_id={self.version_id}, id={self.id}, text={self.text}, daystring={self.daystring}, date_from={self.date_from}, date_until={self.date_until}, line={self.line})>"

    def textcalendar(self) -> str:
        """Human readable calendar of valid days"""
        text = "\t  0        1         2         3 \n" \
               "\t  1234567890123456789012345678901\n" \
               "\t   | | | | | | | | | | | | | | | "
        currdate = self.date_from.replace(day=1)
        while currdate <= self.date_until:
            if currdate.day == 1:
                text += f"\n{month_abbr[currdate.month]} {currdate.year}  "
            text += " " if currdate < self.date_from else ("1" if currdate in self.dates else "0")
            currdate += timedelta(days=1)
        return text
