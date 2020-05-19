#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""Create graphs using `DINO2.model` and using database `MetaData`"""

from ._sqlalchemy_schemadisplay import create_uml_graph, create_schema_graph
from sqlalchemy.orm import class_mapper
from sqlalchemy import MetaData
from sys import argv

from .. import Database
from ..model import Base, Version, calendar, fares, location, operational, network, schedule

def schema_graph(path: str, noversion: bool):
    # https://github.com/sqlalchemy/sqlalchemy/wiki/SchemaDisplay
    # create the pydot graph object by autoloading all tables via a bound metadata object
    graph = create_schema_graph(metadata=MetaData('sqlite:///./dino2.1.db'),
       show_datatypes=True, # The image would get nasty big if we'd show the datatypes
       show_indexes=False, # ditto for indexes
       rankdir='LR', # From left to right (instead of top to bottom)
       concentrate=False, # Don't try to join the relation lines together
       show_column_keys=True,
       hide_tables=("version",) if noversion else None
    )
    graph.write_png(f'{path}/schema_db.png') # write out the file

    mappers = []
    if not noversion:
        mappers.append(class_mapper(Version))
    for module in (calendar, fares, location, operational, network, schedule):
        for attr in dir(module):
            cls = getattr(module, attr)
            if (not isinstance(cls, type)
                or cls == Base
                or cls == Version
                or not issubclass(cls, Base)
                or getattr(cls, '__abstract__', False)
                or attr[0] == '_'
                ): continue
            try:
                mappers.append(class_mapper(cls))
            except Exception as e:
                print(e)
                pass

    # pass them to the function and set some formatting options
    graph = create_uml_graph(mappers,
        show_operations=False, # not necessary in this case
        show_multiplicity_one=True # some people like to see the ones, some don't
    )
    graph.write_png(f'{path}/schema_model.png') # write out the file

def main():
    db = Database()
    Base.metadata.create_all(db.engine)
    path = argv[1]
    noversion = True
    if len(argv) > 2:
        noversion = bool(int(argv[2])) if argv[2].isdigit() else (argv[2].lower() == "true")
    schema_graph(path, noversion)

if __name__ == "__main__":
    main()
