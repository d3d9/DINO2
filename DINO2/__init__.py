# -*- coding: utf-8 -*-
"""
Process timetable data in the DINO 2.1 format

.. include:: ../README.md
"""

from dataclasses import dataclass, field
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


@dataclass
class Database:
    """
    Class for database connection.

    Provides `engine` and `Session` properties.
    """
    url: str = 'sqlite:///./DINO2.db'
    fk: bool = False
    engine: Engine = field(init=False)
    Session: sessionmaker = field(init=False)

    def __post_init__(self):
        self.engine = create_engine(self.url)
        if self.fk:
            # Foreign Keys auswerten. Quelle: https://stackoverflow.com/a/7831210
            event.listen(self.engine, 'connect', lambda dbapi_con, con_record: dbapi_con.execute('pragma foreign_keys=ON'))
        self.Session = sessionmaker()
        self.Session.configure(bind=self.engine)


from . import model, tools, types
