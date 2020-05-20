#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
"""Import DINO 2.1 data using the `DINO2.model`"""

from __future__ import annotations

from collections import namedtuple
from pandas import read_csv, Int64Dtype, isna, NA, Period, concat, to_datetime, DataFrame, Series
from sqlalchemy.orm.session import Session
import sys
from tqdm import tqdm
from typing import Dict, Union, Callable, Any, Collection, FrozenSet, Optional, List, Type

from .. import Database
from ..model import Base, Version, calendar, fares, location, operational, network, schedule

# https://stackoverflow.com/questions/31394998/using-sqlalchemy-to-load-csv-file-into-a-database
# https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html

encodings = {"WE8MSWIN1252": "windows-1252", None: "windows-1252"}


def imp(dinodir: str, classes: Collection[Type[Base]], session: Session, version_ids: Optional[Collection[int]] = None) -> None:
    """Import given tables for a version id (or all versions) of a DINO 2.1 dataset"""
    character_set = read_csv(f"{dinodir}/character_set.din", sep=";", header=0, index_col=False, dtype={"VERSION": 'Int64', "CHARACTER_SET": 'object'}, skipinitialspace=True, quotechar='"', encoding=encodings[None])
    encoding = encodings.get(next((r.CHARACTER_SET for r in character_set.itertuples(index=False) if (r.VERSION in version_ids if version_ids else True)), None))
    print(f"version_ids: {version_ids}\nclasses: {', '.join(cls.__name__ for cls in classes)}\nencoding: {encoding}\n")
    for ci, cls in enumerate(classes, start=1):
        print(f"[{ci}/{len(classes)}] importing {cls} (file {cls._din_file})")
        data = read_csv(f"{dinodir}/{cls._din_file}", sep=";", header=0, index_col=False, dtype=cls._dtypes(), skipinitialspace=True, quotechar='"', encoding=encoding)
        if version_ids:
            data = data[data.VERSION.isin(version_ids)]
        cls_col_names = cls._column_names()
        cls_parameters = cls._parameters()
        for col in data:
            if col not in cls_col_names:
                if col != f"Unnamed: {len(data.columns) - 1}":
                    print(f"--> warning: Unexpected column '{col}'")
                continue
            col_info = cls._col_info(cls_parameters[col])
            if data[col].dtype == 'object':
                data[col] = data[col].map(
                    lambda s: (
                        ('' if col_info.get('keep_empty_str') else NA)
                        if (isna(s) or (col.strip() == "-1" and col_info.get('str_minus_1_to_null')))
                        else s.strip()
                    ))
            elif isinstance(data[col].dtype, Int64Dtype) and not col_info.get('keep_minus_1'):
                data[col] = data[col].map(lambda i: NA if (not isna(i) and i == -1) else i)
        missing_cols = frozenset(ccol for ccol in cls_col_names if ccol not in data)
        for mcol in missing_cols:
            print(f"--> warning: Expected column '{mcol}' not in data")
        data.drop_duplicates(inplace=True)
        if cls._din_file == "stop.din":
            dupes = data[data.duplicated({'VERSION', 'STOP_NR'}, keep=False)]
            data.drop(dupes.index, inplace=True)
            deduped = DataFrame()

            def mask_fn(g: DataFrame) -> Series:
                """Mask for a group of a DataFrame, only keeps one row (the one that is valid today or the one that was valid most recently)"""
                # see https://pandas-docs.github.io/pandas-docs-travis/user_guide/timeseries.html#timeseries-oob
                v_f = g['VALID_FROM'].astype(int).apply(lambda s: Period(year=int(s) // 10000, month=int(s) // 100 % 100, day=int(s) % 100, freq='D'))
                v_t = g['VALID_TO'].astype(int).apply(lambda s: Period(year=int(s) // 10000, month=int(s) // 100 % 100, day=int(s) % 100, freq='D'))
                v_f_t = concat([v_f, v_t], axis=1)
                _today_dt = to_datetime('today')
                today = Period(year=_today_dt.year, month=_today_dt.month, day=_today_dt.day, freq='D')
                now = (today >= v_f_t['VALID_FROM']) & (v_f_t['VALID_TO'] >= today)
                if not now.any():
                    now.iloc[-1] = True
                return now

            grouped = dupes.groupby(['VERSION', 'STOP_NR'])
            for name, group in grouped:
                deduped = concat([deduped, group[mask_fn]])
            data = concat([data, deduped])
        objs: List[Base] = []

        def value(v: Optional[Any], par: str) -> Optional[Any]:
            if isna(v):
                v = None
            col_type = getattr(cls, par).type
            if hasattr(col_type, "process_result_value"):
                return col_type.process_result_value(v)
            return v

        mappings = []
        for r in tqdm(data.itertuples(index=False), total=data.shape[0]):
            mappings.append(
                {
                    _p: value(getattr(r, _c), _p)
                    for _c, _p in cls_parameters.items()
                    if _c not in missing_cols
                })
        session.bulk_insert_mappings(cls, mappings)
        print()


def main(argv: Collection[str]):
    """Parse `argv` and call `imp`"""
    if len(argv) != 4 or not (argv[3] in {"c", "a"} or all((c.isdigit() or c == ',') for c in argv[3])):
        raise ValueError("3 arguments (database url like `sqlite:///./DINO2.db`, data directory, and ('c' (clear), 'a' (all), or ','-separated versionids)) required")

    db = Database(argv[1])
    Base.metadata.create_all(db.engine)

    if argv[3] == "c":
        Base.metadata.drop_all(db.engine)
        Base.metadata.create_all(db.engine)
    else:
        session = db.Session()
        try:
            version_ids = set(int(v) for v in argv[3].split(',')) if argv[3] != "a" else None
            classes = [Version]
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
                    classes.append(cls)
            imp(argv[2], classes, session, version_ids)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


if __name__ == "__main__":
    main(sys.argv)
