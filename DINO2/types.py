# -*- coding: utf-8 -*-
"""Custom types"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum
from sqlalchemy import String, Integer, cast, func
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine
from typing import Optional, Type, Tuple, Any, Union


# https://stackoverflow.com/q/35209650
class DinoDate(TypeDecorator):
    """Column type for date strings in yyyymmdd format, converted to `datetime.date` objects"""
    impl = String(length=8)

    def coerce_compared_value(self, op, value):
        if isinstance(value, str):
            return self.impl
        return self

    class comparator_factory(TypeDecorator.Comparator, impl.comparator_factory):
        @property
        def year(self):
            return cast(func.substr(self.expr, 1, 4), Integer)

        @property
        def month(self):
            return cast(func.substr(self.expr, 5, 2), Integer)

        @property
        def day(self):
            return cast(func.substr(self.expr, 7, 2), Integer)

    def process_bind_param(self, value: Optional[date], dialect: Optional[Dialect] = None) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, date):
            return '%04d%02d%02d' % (value.year, value.month, value.day)
        raise ValueError(f"expected datetime.date, got {value.__class__.__name__}")

    def process_result_value(self, value: Optional[str], dialect: Optional[Dialect] = None) -> Optional[date]:
        if value:
            return date(year=int(value[0:4]), month=int(value[4:6]), day=int(value[6:8]))
        return None


class DinoTimeDelta(TypeDecorator):
    """Column type for timedeltas saved as int in the database, converted to `datetime.timedelta` objects"""
    impl = Integer
    should_evaluate_none = True

    def __init__(self, minus_1_none: bool = False):
        super().__init__()
        self.minus_1_none = minus_1_none

    # do not coerce None to "is NULL" automatically
    coerce_to_is_types: Tuple[Type, ...] = tuple()

    def coerce_compared_value(self, op, value):
        if isinstance(value, int):
            return self.impl
        return self

    class comparator_factory(TypeDecorator.Comparator, impl.comparator_factory):
        @property
        def total_seconds(self):
            return cast(self.expr, Integer)

    def process_bind_param(self, value: Optional[timedelta], dialect: Optional[Dialect] = None) -> Optional[int]:
        if value is None:
            return -1 if self.minus_1_none else None
        if isinstance(value, timedelta):
            return int(value.total_seconds())
        raise ValueError(f"expected datetime.timedelta, got {value.__class__.__name__}")

    def process_result_value(self, value: Optional[int], dialect: Optional[Dialect] = None) -> Optional[timedelta]:
        if (value is None) or (value == -1 and self.minus_1_none):
            return None
        return timedelta(seconds=int(value))

    def copy(self, **kwargs):
        return DinoTimeDelta(self.minus_1_none)


# https://stackoverflow.com/a/38786737
class TypeEnum(TypeDecorator):
    """Column type for python `enum.Enum`s stored in the database"""
    impl: Union[TypeEngine, Type[TypeEngine]] = TypeEngine

    def __init__(self, enum_type: Type[Enum]):
        if self.__class__ == TypeEnum:
            raise NotImplementedError(f"Do not use {self.__class__} directly")
        super().__init__()
        self.enum_type = enum_type

    def process_bind_param(self, value: Optional[Enum], dialect: Optional[Dialect] = None) -> Optional[Any]:
        if value is None:
            return None
        if isinstance(value, self.enum_type):
            return value.value
        raise ValueError(f'expected {self.enum_type.__name__} value, got {value.__class__.__name__}')

    def process_result_value(self, value: Optional[Any], dialect: Optional[Dialect] = None) -> Optional[Enum]:
        if value is None:
            return None
        return self.enum_type(value)

    def copy(self, **kwargs):
        return self.__class__(self.enum_type)


class IntEnum(TypeEnum):
    """Column type for python `enum.Enum`s stored as int in the database"""
    impl = Integer

    def coerce_compared_value(self, op, value):
        if isinstance(value, int):
            return self.impl
        return self


class CharEnum(TypeEnum):
    """Column type for python `enum.Enum`s stored as a single character in the database"""
    impl = String(length=1)

    def coerce_compared_value(self, op, value):
        if isinstance(value, str):
            return self.impl
        return self
