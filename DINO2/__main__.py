#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

from . import Database
from .model import Base, Version, calendar, fares, location, operational, network, schedule

db = Database(fk=True)
db.engine.echo = True
Base.metadata.create_all(db.engine)
session = db.Session()

versions = {v.id: v for v in session.query(Version).all()}
print(versions)

# session.close()
