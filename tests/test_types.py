import pytest

from datetime import date, timedelta
from enum import Enum

from DINO2.types import DinoDate, DinoTimeDelta, TypeEnum, IntEnum

def test_dinodate_prv():
    dd = DinoDate()
    assert dd.process_result_value(None) == None
    assert dd.process_result_value('') == None
    assert dd.process_result_value('19700101') == date(1970, 1, 1)
    assert dd.process_result_value('20200229') == date(2020, 2, 29)
    with pytest.raises(TypeError):
        dd.process_result_value(2000)

def test_dinodate_pbp():
    dd = DinoDate()
    assert dd.process_bind_param(None) == None
    assert dd.process_bind_param(date(1970, 1, 1)) == '19700101'
    assert dd.process_bind_param(date(2020, 2, 29)) == '20200229'
    with pytest.raises(ValueError):
        dd.process_bind_param(2000)

def test_dinotd_prv():
    dtd = DinoTimeDelta()
    assert dtd.process_result_value(None) == None
    assert dtd.process_result_value(-1) == timedelta(seconds=-1)
    assert dtd.process_result_value(60) == timedelta(minutes=1)
    # import
    assert dtd.process_result_value('1') == timedelta(seconds=1)

def test_dinotd_pbp():
    dtd = DinoTimeDelta()
    assert dtd.process_bind_param(None) == None
    assert dtd.process_bind_param(timedelta(seconds=-1)) == -1
    assert dtd.process_bind_param(timedelta(seconds=60)) == 60
    with pytest.raises(ValueError):
        dtd.process_bind_param('1') == 1

def test_dinotd_m1_prv():
    dtd = DinoTimeDelta(True)
    assert dtd.process_result_value(None) == None
    assert dtd.process_result_value(-1) == None
    assert dtd.process_result_value(60) == timedelta(minutes=1)
    # import
    assert dtd.process_result_value('1') == timedelta(seconds=1)

def test_dinotd_m1_pbp():
    dtd = DinoTimeDelta(True)
    assert dtd.process_bind_param(None) == -1
    assert dtd.process_bind_param(timedelta(seconds=-1)) == -1
    assert dtd.process_bind_param(timedelta(seconds=60)) == 60
    with pytest.raises(ValueError):
        dtd.process_bind_param('1')

def test_typeenum():
    class TestEnum(Enum):
        default = 0
        normal = 1
        higher = 2
    with pytest.raises(NotImplementedError):
        te = TypeEnum(TestEnum)
    te = IntEnum(TestEnum)
    assert te.process_result_value(None) == None
    assert te.process_result_value(1) == TestEnum.normal
    with pytest.raises(ValueError):
        te.process_result_value(10)
    assert te.process_bind_param(None) == None
    assert te.process_bind_param(TestEnum.normal) == 1
    with pytest.raises(ValueError):
        te.process_bind_param("normal")
