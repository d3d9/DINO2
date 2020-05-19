# -*- coding: utf-8 -*-
"""Functions for simple csv exports"""

from __future__ import annotations

from collections import defaultdict
from csv import writer
from datetime import date, datetime, timedelta
import itertools
import os
from sqlalchemy import tuple_
from sqlalchemy.orm import joinedload, load_only, Query, Load
from sqlalchemy.orm.session import Session
from typing import Optional, Set, Dict, Tuple, List

from ...model import Base, Version, calendar, fares, location, operational, network, schedule


def stops(session: Session, fname: str, version_id: Optional[int] = None) -> None:
    """Export csv file of all stops, one row per stop position"""
    rows = [
        (
            "version", "stopid", "stopname", "placename", "stopshortname",
            "stopifopt", "areaid", "areaname", "areaifopt",
            "posid", "posname", "posifopt", "X", "Y", "farezones"
        )]
    q = session.query(location.Stop).options(joinedload('points').joinedload('area'))
    if version_id is not None:
        q = q.filter_by(version_id=version_id)
    for stop in q.all():
        for point in stop.points:
            area_id, area_name, area_ifopt = (point.area.id, point.area.name, point.area.ifopt) if point.area is not None else (None, None, None)
            rows.append(
                (
                    stop.version_id, stop.id, stop.name, stop.place, stop.abbr,
                    stop.ifopt, area_id, area_name, area_ifopt,
                    point.id, point.name, point.ifopt, point.pos_x, point.pos_y,
                    ",".join(str(fzid) for fzid in stop.fare_zone_ids)
                ))
    with open(fname, 'w', encoding='utf-8') as f:
        writer(f, delimiter=";", lineterminator='\n').writerows(rows)


def courses(session: Session, path: str, line_ids: Optional[Set[int]] = None, export_full_name: bool = False, version_id: Optional[int] = None) -> None:
    """Export csv files of all course stops per trip"""
    q = session.query(network.Course).options(joinedload('stops').joinedload('stop'), joinedload('stops').joinedload('stop_point'))
    if version_id is not None:
        q = q.filter_by(version_id=version_id)
    if line_ids:
        q = q.filter(network.Course.line.in_(line_ids))
    for course in q.all():
        _from_stop, _to_stop = course.stops[0], course.stops[-1]

        def try_name(cs: network.CourseStop) -> str:
            name = cs.stop.name_noloc
            if name:
                return name.replace("/", "").replace(".", "")
            name = cs.stop.name
            try:
                return name.split(" ")[1].replace("/", "").replace(".", "")
            except IndexError:
                return name.replace("/", "").replace(".", "")
        _from, _to = try_name(_from_stop), try_name(_to_stop)
        fname = os.path.join(path, f"dino_{course.name}_{course.id}_{_from}_{_to}.csv")
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, 'w', encoding='utf-8') as f:
            writer(f, delimiter=";", lineterminator='\n').writerows([
                (
                    cs.consec_stop_nr,
                    (cs.stop_point.ifopt if (cs.stop_point is not None and cs.stop_point.ifopt) else cs.stop.ifopt),
                    (cs.stop.name if (export_full_name or not cs.stop.name_noloc) else cs.stop.name_noloc)
                ) for cs in course.stops])


def trips(session: Session, fname: str, date_: date, line_ids: Optional[Set[int]] = None, version_id: Optional[int] = None) -> None:
    """Export csv file of trips for a given date"""
    rows = [("lineid", "linesymbol", "from", "to", "startt", "endt", "tripid", "wkt")]
    q = schedule.Trip.query_for_date(session, date_)
    if version_id is not None:
        q = q.filter_by(version_id=version_id)
    if line_ids:
        q = q.filter(schedule.Trip.line.in_(line_ids))
    for trip in q.all():
        rows.append(
            (
                trip.line, trip.course.name, trip.dep_stop.name, trip.arr_stop.name,
                int(trip.departure_time.total_seconds()),
                int(trip.departure_time.total_seconds()+trip.duration.total_seconds()),
                trip.id, trip.wkt()
            ))
    with open(fname, 'w', encoding='utf-8') as f:
        writer(f, delimiter=";", lineterminator='\n').writerows(rows)


def line_stats(session: Session, fname: str, version_id: Optional[int] = None) -> None:
    """Line statistics with total year-kilometers per version->line->course"""
    lq = session.query(schedule.Trip, network.Course.length) \
        .order_by(schedule.Trip.version_id.asc(), schedule.Trip.line.asc(), schedule.Trip.line_dir.asc(), schedule.Trip.course_id.asc()) \
        .options(
            joinedload('course', innerjoin=True),
            joinedload('day_attribute', innerjoin=True),
            joinedload('restriction'),
            *(load_only(_) for _ in ('line', 'course_id', 'line_dir', 'day_attribute_id', 'restriction_id'))
        ).join(network.Course)
    if version_id is not None:
        lq = lq.filter_by(version_id=version_id)
    total = 0
    rows = [("version", "line", "course", "km")]
    for versionid, version_grouper in itertools.groupby(lq.all(), lambda t_l: t_l[0].version_id):
        version_total = 0
        for lineid, line_grouper in itertools.groupby(version_grouper, lambda t_l: t_l[0].line):
            line_total = 0
            for courseid, course_grouper in itertools.groupby(line_grouper, lambda t_l: t_l[0].course_id):
                course_total = 0
                for trip, length in course_grouper:
                    days = len(trip.dates)
                    km = days*(length/1000)
                    course_total += km
                rows.append((versionid, lineid, courseid, f"{course_total:.2f}"))
                line_total += course_total
            rows.append((versionid, lineid, "total", f"{line_total:.2f}"))
            version_total += line_total
        rows.append((versionid, "total", "", f"{version_total:.2f}"))
        total += version_total
    rows.append(("total", "", "", f"{total:.2f}"))
    with open(fname, 'w', encoding='utf-8') as f:
        writer(f, delimiter=";", lineterminator='\n').writerows(rows)


def departure_stats(tripquery: Query, fname: str) -> None:
    """Departures from->to, between, and from stops."""
    tripquery = tripquery.options(
        load_only('version_id'), load_only('line'), load_only('id'), load_only('course_id'), load_only('line_dir'),
        joinedload('course', innerjoin=True).load_only('version_id').load_only('line').load_only('id').load_only('line_dir')
        .joinedload('stops', innerjoin=True).load_only('version_id').load_only('line').load_only('course_id').load_only('line_dir').load_only('consec_stop_nr')
        .joinedload('stop', innerjoin=True).load_only('version_id').load_only('ifopt').load_only('name'))

    pairs: Dict[Tuple[location.Stop, location.Stop], int] = defaultdict(int)
    for trip in tripquery.all():
        for _stopi, cstop in enumerate(trip.course.stops):
            if cstop.consec_stop_nr != len(trip.course.stops):
                pairs[(cstop.stop, trip.course.stops[_stopi+1].stop)] += 1

    # todo: ggf. version "ignorieren", stops version-uebergreifend zuordnen?
    rows = [("type", "version", "from/A", "l-ifopt", "to/B", "r-ifopt", "count")]
    for (sf, st), dc in sorted(pairs.items(), key=lambda i: -i[1]):
        rows.append(("from-to", sf.version_id, sf.name, sf.ifopt, st.name, st.ifopt, dc))

    pairsbidi = {}
    for (sf, st), dc in pairs.items():
        if (sf, st) not in pairsbidi and (st, sf) not in pairsbidi:
            pairsbidi[(sf, st)] = dc
            if (st, sf) in pairs and (sf, st) != (st, sf):
                pairsbidi[(sf, st)] += pairs[(st, sf)]

    for (sf, st), dc in sorted(pairsbidi.items(), key=lambda i: -i[1]):
        rows.append(("between", sf.version_id, sf.name, sf.ifopt, st.name, st.ifopt, dc))

    stopdeps = {stop: sum(dc for ((sf, st), dc) in pairs.items() if stop == sf) for (stop, _) in pairs}
    for stop, dc in sorted(stopdeps.items(), key=lambda i: -i[1]):
        rows.append(("from", sf.version_id, stop.name, stop.ifopt, "", "", dc))

    with open(fname, 'w', encoding='utf-8') as f:
        writer(f, delimiter=";", lineterminator='\n').writerows(rows)


def departures(stop: location.Stop, day: date, fname: str, days: int = 1) -> None:
    """Departures from a given stop for a given date (range)"""
    servinglines = set((c.line, c.id) for c in stop.courses)
    deps: List[Tuple[datetime, schedule.TripStop]] = []
    for currdate in (day + timedelta(days=n) for n in range(days)):
        tripquery = schedule.Trip.query_for_date(stop._session, currdate) \
            .filter(
                (schedule.Trip.version_id == stop.version_id)
                & tuple_(schedule.Trip.line, schedule.Trip.course_id).in_(servinglines)
            ).options(
                load_only('version_id'), load_only('line'), load_only('id'), load_only('course_id'), load_only('line_dir'), load_only('timing_group'), load_only('departure_time'), load_only('arr_stop_id'),
                joinedload('course', innerjoin=True).load_only('version_id').load_only('line').load_only('id').load_only('line_dir').load_only('name'),
                joinedload('arr_stop').load_only('name')
            )
        trips = [(t, t.trip_stops(simple=True)) for t in tripquery.all()]
        # todo: eventuell mal das trip_stops sich sparen koennen.
        for trip, tripstops in trips:
            deps.extend(
                (datetime.combine(currdate, datetime.min.time()) + ts.dep_time, ts)
                for n, ts
                in filter(
                    lambda n_ts: n_ts[1].stop == stop and n_ts[0] != len(tripstops),
                    enumerate(tripstops, start=1)
                ))
    rows = [("date", "time", "plat", "linenum", "direction")]
    rows.extend(
        (
            deptime.strftime("%Y-%m-%d"), deptime.strftime("%H:%M:%S"),
            ts.stop_point.name if ts.stop_point is not None else "",
            ts.trip.course.name, ts.trip.arr_stop.name
        ) for deptime, ts in sorted(deps, key=lambda d: d[0]))
    with open(fname, 'w', encoding='utf-8') as f:
        writer(f, delimiter=";", lineterminator='\n').writerows(rows)
