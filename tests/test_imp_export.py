import pytest

from datetime import date, timedelta
from enum import Enum
from filecmp import cmp, dircmp
import os
from shutil import rmtree
from sqlalchemy.exc import IntegrityError

from DINO2 import Database
from DINO2.model import Version
from DINO2.model.location import Stop
from DINO2.model.schedule import Trip
from DINO2.tools.imp import main
from DINO2.tools.export import csv, wikitable
from DINO2.types import DinoDate, DinoTimeDelta, TypeEnum, IntEnum

def test_import_clear():
    argv = [None, None, "c"]
    main(argv)

def test_import_success():
    argv = [None, "./tests/data/2020-05-15-version-9", "a"]
    main(argv)

def test_import_integrityerror():
    with pytest.raises(IntegrityError):
        test_import_success()

def test_dataset_counts():
    db = Database()
    session = db.Session()
    assert session.query(Version).count() == 1
    version = session.query(Version).one()
    assert len(version.daytypes) == 7
    assert len(version.day_type_calendar) == 207
    assert len(version.stops) == 528
    assert len(version.courses) == 265
    assert len(version.trips) == 4938
    session.close()

def test_wikitable():
    db = Database()
    session = db.Session()
    fn = "./tests/data/_test_wiki-9.txt"
    if os.path.exists(fn):
        raise Exception(f"{fn} already exists, won't delete")
    wikitable.wikitable(session, fn)
    equal = cmp(fn, "./tests/data/wiki-9.txt")
    os.remove(fn)
    session.close()
    assert equal

def test_stops():
    db = Database()
    session = db.Session()
    fn = "./tests/data/_test_stops-9.csv"
    if os.path.exists(fn):
        raise Exception(f"{fn} already exists, won't delete")
    csv.stops(session, fn)
    equal = cmp(fn, "./tests/data/stops-9.csv")
    os.remove(fn)
    session.close()
    assert equal

def test_courses():
    db = Database()
    session = db.Session()
    fp = "./tests/data/_test_courses-9/"
    if os.path.exists(fp):
        raise Exception(f"{fp} already exists, won't delete")
    csv.courses(session, fp)
    dc = dircmp(fp, "./tests/data/courses-9/")
    equal = not dc.diff_files and not dc.funny_files
    rmtree(fp)
    session.close()
    assert equal

def test_trips():
    db = Database()
    session = db.Session()
    fn = "./tests/data/_test_trips-9-50514-2020-06-14.csv"
    if os.path.exists(fn):
        raise Exception(f"{fn} already exists, won't delete")
    csv.trips(session, fn, date(2020, 6, 14), line_ids={50514})
    equal = cmp(fn, "./tests/data/trips-9-50514-2020-06-14.csv")
    os.remove(fn)
    session.close()
    assert equal

def test_line_stats():
    db = Database()
    session = db.Session()
    fn = "./tests/data/_test_line_stats-9.csv"
    if os.path.exists(fn):
        raise Exception(f"{fn} already exists, won't delete")
    csv.line_stats(session, fn)
    equal = cmp(fn, "./tests/data/line_stats-9.csv")
    os.remove(fn)
    session.close()
    assert equal

def test_departure_stats():
    db = Database()
    session = db.Session()
    tq = Trip.query_for_date(session, date(2020,6,15))
    assert tq.count() == 2038
    fn = "./tests/data/_test_departure_stats-9-2020-06-15.csv"
    if os.path.exists(fn):
        raise Exception(f"{fn} already exists, won't delete")
    csv.departure_stats(tq, fn)
    equal = cmp(fn, "./tests/data/departure_stats-9-2020-06-15.csv")
    os.remove(fn)
    session.close()
    assert equal

def test_departures():
    db = Database()
    session = db.Session()
    fw = session.query(Stop).filter_by(version_id=9, id=2216).one()
    assert fw.name == "Hagen Feuerwache"
    fn = "./tests/data/_test_departures-9-2216-2020-06-14+8.csv"
    if os.path.exists(fn):
        raise Exception(f"{fn} already exists, won't delete")
    csv.departures(fw, date(2020, 6, 14), fn, days=8)
    equal = cmp(fn, "./tests/data/departures-9-2216-2020-06-14+8.csv")
    os.remove(fn)
    session.close()
    assert equal
