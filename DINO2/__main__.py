#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

from sys import argv

from . import Database
from .model import Base, Version, calendar, fares, location, operational, network, schedule

_db_args = dict(url=(argv[1] if len(argv) > 1 else None), fk=True)
db = Database(**{k: v for k, v in _db_args.items() if v is not None})
db.engine.echo = True
Base.metadata.create_all(db.engine)
session = db.Session()

versions = {v.id: v for v in session.query(Version).all()}
print(versions)

# session.close()
