# -*- coding: utf-8 -*-
"""Export data to a wikitable"""

from __future__ import annotations

from datetime import timedelta
import itertools
from sqlalchemy.orm import joinedload, load_only, contains_eager
from sqlalchemy.orm.session import Session
from typing import Optional, Set, Collection

from ...model import Base, Version, calendar, fares, location, operational, network, schedule


# todo: ersetzen, es sollte kontext verstehen
def stopclean(name, placelist, ignoreif=["Hauptbahnhof", "Hbf", "Bahnhof", "Bf"]):
    for s in ignoreif:
        if s in name:
            return name
    for place in placelist:
        name = name.replace(place, "", 1)
    return name


def timestr(secs):
    return (str(secs//3600).zfill(2)+":"+str((secs//60) % 60).zfill(2)+":"+str(secs % 60).zfill(2)).rstrip("00").rstrip(":")


def mins(td):
    return ("%f" % (td.total_seconds()/60)).rstrip("0").rstrip(".")


def rowspan(e):
    return (1 if not e else sum(rowspan(x[1]) for x in e))


def takt(a, min_alle=3):
    r = []
    nexttime = timedelta(seconds=-9999)
    nexttd = timedelta(seconds=-9999)
    takt = timedelta(seconds=0)
    taktc = 0

    for i, s in enumerate(a):
        td = s if type(s) == timedelta else timedelta(seconds=s)
        if i < len(a) - 1:
            n = a[i+1]
            nexttime = n if type(n) == timedelta else timedelta(seconds=n)
        else:
            nexttime = timedelta(seconds=-9999)
        tdiff = nexttime - td

        if tdiff == nexttd:
            takt = tdiff
            taktc += 1
        else:
            if taktc:
                if not takt:
                    for _ in range(taktc):
                        r.append(timestr(int(td.total_seconds())))
                elif taktc < min_alle:
                    for t in range(taktc, 0, -1):
                        r.append(timestr(int((td-t*takt).total_seconds())))
                else:
                    r.append("alle " + mins(takt) + " min")
            takt = timedelta(0)
            taktc = 0
            r.append(timestr(int(td.total_seconds())))
        nexttd = tdiff
        nexttime = td

    rtext = ""
    for ri, re in enumerate(r):
        rtext += re
        if re.startswith("alle"):
            sep = " --"
        elif ri < len(r) - 1 and r[ri+1].startswith("alle"):
            sep = "-- "
        else:
            sep = ", "
        if ri < len(r) - 1:
            rtext += sep

    return rtext


def fahrplanarray(session: Session, courses: Collection[network.Course]):
    a = []
    # todo: network.Course.duration & length benutzen..
    # tmp
    placelist = ["Hagen ", "HA-", "Hagen, "]
    for lineid, line_courses_grouper in itertools.groupby(courses, lambda c: c.line):
        line_courses = list(line_courses_grouper)
        assert all(lc.name == line_courses[0].name for lc in line_courses)
        a_l = [[f"'''{line_courses[0].name}'''"], []]
        for lc in sorted(line_courses, key=lambda _lc: (_lc.line_dir, stopclean(_lc.stops[0].stop.name, placelist), -len(_lc.stops), -_lc.length)):
            stopcontent = f"<span style=\"text-decoration: underline dotted;\" title=\"{'-'.join(s.stop.abbr for s in lc.stops)}\">{len(lc.stops)}</span>"
            a_c = [[f"'''{stopclean(lc.stops[0].stop.name, placelist)}'''&nbsp;→ '''{stopclean(lc.stops[-1].stop.name, placelist)}'''", stopcontent, str(round(lc.length/1000, 1)).replace(".", ",").rstrip("0").rstrip(",") + " km"], []]
            fahrzeiten = {}
            for timing_group_nr in set(_st.timing_group for _st in lc.stop_timings):
                fahrzeit = f"{mins(lc.duration(timing_group_nr))} min"
                if fahrzeit not in fahrzeiten:
                    fahrzeiten[fahrzeit] = [timing_group_nr]
                else:
                    # zeiten, die insgesamt gleich sind werden zusammengetan
                    fahrzeiten[fahrzeit].append(timing_group_nr)
            for fahrzeit in fahrzeiten:
                a_fz = [[fahrzeit], []]
                restrictions = {}
                for trip in session.query(schedule.Trip) \
                        .options(
                            load_only('day_attribute_id', 'restriction_id', 'departure_time'),
                            joinedload('day_attribute'),
                            joinedload('restriction')
                        ).filter(schedule.Trip.course==lc) \
                        .filter(schedule.Trip.timing_group.in_(fahrzeiten[fahrzeit])) \
                        .all():
                    restrictiontext = "keine" if trip.restriction_id is None else str(trip.restriction.text)
                    day_attr = trip.day_attribute
                    starttime = int(trip.departure_time.total_seconds())
                    # todo: auch schauen ob die kalender an sich gleich sind, nicht nur der text!
                    if restrictiontext not in restrictions:
                        restrictions[restrictiontext] = {day_attr: [starttime]}
                    elif day_attr not in restrictions[restrictiontext]:
                        restrictions[restrictiontext][day_attr] = [starttime]
                    elif starttime not in restrictions[restrictiontext][day_attr]:
                        restrictions[restrictiontext][day_attr].append(starttime)
                    else:
                        restrictions[restrictiontext][day_attr].append(starttime)
                        print("Warnung, gleichzeitige gleiche Abfahrt:", lc, fahrzeit, restrictiontext, day_attr, timestr(starttime))
                for restrictiontext in restrictions:
                    a_r = [[restrictiontext], []]
                    for day_attr in restrictions[restrictiontext]:
                        dttext = day_attr.text
                        takttext = takt(sorted(restrictions[restrictiontext][day_attr]))
                        a_r[1].append([[dttext, takttext], []])
                    a_r[1].sort(key=lambda dt: dt[0][0])
                    a_fz[1].append(a_r)
                a_fz[1].sort(key=lambda r: r[0][0])
                a_c[1].append(a_fz)
            a_c[1].sort(reverse=True, key=lambda fz: fz[0][0])
            a_l[1].append(a_c)
        a.append(a_l)
    return a


def stoparray(stops: Collection[location.Stop]):
    a = []
    vocoords = lambda x, y, name, dim: f"{{{{Coordinate|NS={y.rstrip('0')}|EW={x.rstrip('0')}|dim={dim}|type=landmark|region=DE-NW|simple=y|name={name}}}}}" if (x and y) else ""
    sortf = lambda s: ((s.name or ""), (s.ifopt or ""))
    for stop in sorted(stops, key=sortf):
        a_s = [[f"'''{stop.name}'''", stop.ifopt or "", vocoords(stop.pos_x, stop.pos_y, stop.name, "120"), ", ".join(str(fzid) for fzid in sorted(stop.fare_zone_ids)), stop.abbr], []]
        # 0-areas?
        for area in sorted(stop.areas, key=sortf):
            a_a = [[area.name, area.ifopt or ""], []]
            for pos in sorted(area.points, key=sortf):
                a_p = [[pos.name or "", pos.ifopt or "", vocoords(pos.pos_x, pos.pos_y, stop.name+" "+(pos.name or ""), "20")], []]
                a_a[1].append(a_p)
            if not a_a[1]:
                a_a[1].append([["", "", ""], []])
            a_s[1].append(a_a)
        if not a_s[1]:
            a_s[1].append([["", ""], [[["", "", ""], []]]])
        a.append(a_s)
    return a


def tableatext(a, i, labels):
    text = ""
    for x, y in a:
        text += str(rowspan(y)) + " "
        text += "-"*i
        for ei, ex in enumerate(x):
            text += "\""+labels[i][ei]+"\": " + str(ex)
            if ei < len(x) - 1:
                text += " | "
            else:
                text += "\n"

        if y:
            text += tableatext(y, i+1, labels)
    return text


def tablerows(a, tfirstpre=""):
    text = ""
    for x in a:
        rs = rowspan(x[1])
        # ändern!
        if tfirstpre:
            prerowspan = (f" rowspan=\"{rs}\"" if rs > 1 else "")
            pre = ((tfirstpre + prerowspan + " | ") if tfirstpre or prerowspan else "")
            for i, y in enumerate(x[0]):
                text += "| " + (pre if not i else "") + str(y) + "\n"
        else:
            for y in x[0]:
                text += "| " + (f" rowspan=\"{rs}\" | " if rs > 1 else "") + str(y) + "\n"
        if x[1]:
            text += tablerows(x[1])
        else:
            text += "|-\n"
    return text


def to_table(a, ttitle, tref, tcols,
              tfirstpre="",
              tclass="wikitable sortable mw-collapsible mw-collapsed",
              tstyle="width:100%; text-align:left; font-size:90%;",
              theadclass="hintergrundfarbe6"):
    wikitext = "{| class=\"" + tclass + "\" style=\"" + tstyle + "\"\n|-\n"
    wikitext += "|+ " + ttitle + tref + "\n|- class=\"" + theadclass + "\"\n"
    for colname, colsort in tcols:
        wikitext += "! "
        if colsort:
            if colsort == "unsortable":
                wikitext += "class=\"unsortable\" | "
            else:
                wikitext += "data-sort-type=\"" + colsort + "\" | "
        wikitext += colname + "\n"
    wikitext += "\n|-\n"
    wikitext += tablerows(a, tfirstpre)
    wikitext += "\n|}\n"
    return wikitext


def wikitable(session: Session, fname: str, line_ids: Optional[Set[int]] = None, export_stops: bool = True, version_id: Optional[int] = None) -> None:
    cq = session.query(network.Course).join(network.Course.stops).join(network.Course.stop_timings).options(contains_eager('stops'), contains_eager('stop_timings'))
    if version_id is not None:
        cq = cq.filter_by(version_id=version_id)
    if line_ids:
        cq = cq.filter(network.Course.line.in_(line_ids))
    a = fahrplanarray(session, cq.all())

    tref = "<ref name=\"VRR\">Basierend auf Fahrplandaten vom [[Verkehrsverbund Rhein-Ruhr]] ([https://www.openvrr.de/ OpenVRR]): "
    vq = session.query(Version)
    if version_id is not None:
        vq = vq.filter_by(id=version_id)
    for version in vq.all():
        tref += f"{version.net} {version.period_name} ({{{{FormatDate|{version.date_from.strftime('%Y-%m-%d')}|M}}}}–{{{{FormatDate|{version.date_to.strftime('%Y-%m-%d')}|M}}}})"
    tref += "</ref>"
    # name, sort type/unsortable
    linientcols = (("Linie", "text"),
                   ("Linienverlauf", "text"),
                   ("Haltestellen", "number"),
                   ("Strecke", "number"),
                   ("Fahrzeit", "number"),
                   ("Einschränkung", "text"),
                   ("Wochentage", "text"),
                   ("Abfahrtszeiten", "number"),
                   )
    linienfirstpre = "align=\"center\" style=\"background-color:#B404AE; color:white;\""

    wikitext = "Diese Seite wurde komplett aus DINO-Fahrplandaten vom [[Verkehrsverbund Rhein-Ruhr|VRR]] generiert<ref>https://github.com/d3d9/DINO2/</ref> und ist sehr experimentell.\n\n"
    if export_stops:
        wikitext += "{{All Coordinates|pos=inline|section=Haltestellenliste}}\n\n"
    wikitext += "== Busverkehr ==\n=== Liniennetz ===\n==== Alles ====\n"
    wikitext += to_table(a, "Linien", tref, linientcols, linienfirstpre)
    wikitext += "\n==== Anmerkungen zu den Linien ====\n<references group=\"AnmL\"/>\n\n"

    if export_stops:
        sq = session.query(location.Stop).options(joinedload('areas').joinedload('points'))  # ggf. anpassen, 0-areas undso
        if version_id is not None:
            sq = sq.filter_by(version_id=version_id)
        stopa = stoparray(sq.all())
        stoptcols = (("Haltestelle", "text"),
                     ("IFOPT", "text"),
                     ("Koordinaten", "unsortable"),
                     ("Waben", "number"),
                     ("Kürzel", "text"),
                     ("Bereich", "text"),
                     ("IFOPT", "text"),
                     ("Steig", "number"),
                     ("IFOPT", "text"),
                     ("Koordinaten", "unsortable"),
                     )
        wikitext += "== Haltestellen ==\n=== Haltestellenliste ===\n"
        wikitext += to_table(stopa, "Haltestellen", "<ref name=\"VRR\" />", stoptcols)
        wikitext += "\n==== Anmerkungen zu den Haltestellen ====\n<references group=\"AnmH\"/>\n\n"

    wikitext += "== Einzelnachweise ==\n<references />\n"

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(wikitext)
