import pytest

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from DINO2.types import DinoDate  # as an example
from DINO2.model import Base, Version

def test_dinobase():
    _test_col_info = {"test": True, "oops": 999}
    class TestTable(Base):
        _din_file = "test.din"
        version_id = Column("VERSION", Integer(), ForeignKey(Version.id), primary_key=True)
        id = Column("TEST_NR", Integer(), primary_key=True)
        name = Column("TEST_NAME", String(length=20), nullable=False)
        nice = Column("NICE", Boolean, info=_test_col_info)
        date = Column("DATE", DinoDate)
        version = relationship("Version")

    assert TestTable.__tablename__ == "test"
    assert TestTable._column_names() == ("VERSION", "TEST_NR", "TEST_NAME", "NICE", "DATE")
    assert TestTable._dtypes() == {
        "VERSION": 'Int64',
        "TEST_NR": 'Int64',
        "TEST_NAME": 'object',
        "NICE": 'Int64',
        "DATE": 'object'
    }
    assert TestTable._parameters() == {
        "VERSION": "version_id",
        "TEST_NR": "id",
        "TEST_NAME": "name",
        "NICE": "nice",
        "DATE": "date"
    }
    assert TestTable._col_info("nice") == _test_col_info
