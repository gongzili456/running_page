import argparse
import json
import os
import time
from collections import namedtuple
from datetime import datetime, timedelta
from logging import log

import gpxpy
import polyline
import requests
from config import (BASE_TIMEZONE, GPX_FOLDER, JSON_FILE, SQL_FILE, run_map,
                    start_point)
from generator import Generator

from utils import adjust_time

LOGIN_API = "http://iapp.i-cbao.com/account/login"
DETAIL_API = "http://iapp.i-cbao.com/app/jk/trajectory-detail"
DAY_API = "http://iapp.i-cbao.com/app/jk/trajectory-summary"
CAR_INFO_API = "http://iapp.i-cbao.com/app/jk/timelys"
CAR_ID = ""


def login(session, mobile, password, sign):
    headers = {
        "User-Agent": "App1031/4.1.8 (iPhone; iOS 15.1; Scale/3.00)",
        "Content-Type": "application/json",
    }
    data = {"Account": mobile, "Password": password, "sign": sign}
    r = session.post(LOGIN_API, headers=headers, json=data)
    if r.ok:
        code = r.json()["code"]
        if code != 0:
            raise NameError("iChebao Login Error")
        token = r.json()["data"]
        headers["Authorization"] = f"acb {token}"

        rr = session.post(CAR_INFO_API, headers=headers)
        global CAR_ID
        CAR_ID = rr.json()["data"][0]["id"]
        return session, headers


def parse_raw_data_to_nametuple(run_data, old_gpx_ids, with_download_gpx=False):
    points = run_data["points"]
    run_points_data = [[p["lat"], p["lon"]] for p in points]
    polyline_str = polyline.encode(run_points_data) if run_points_data else ""
    start_latlng = start_point(
        *run_points_data[0]) if run_points_data else None
    start_date = datetime.utcfromtimestamp(run_data["startTime"] / 1000)
    end = datetime.utcfromtimestamp(run_data["endTime"] / 1000)
    start_date_local = adjust_time(start_date, BASE_TIMEZONE)
    end_local = adjust_time(end, BASE_TIMEZONE)
    d = {
        "id": int(run_data["startTime"]),
        "name": "run from ichebao",
        "type": "Run",
        "start_date": datetime.strftime(start_date, "%Y-%m-%d %H:%M:%S"),
        "end": datetime.strftime(end, "%Y-%m-%d %H:%M:%S"),
        "start_date_local": datetime.strftime(start_date_local, "%Y-%m-%d %H:%M:%S"),
        "end_local": datetime.strftime(end_local, "%Y-%m-%d %H:%M:%S"),
        "length": run_data["mileage"] * 1000,
        "average_heartrate": None,
        "map": run_map(polyline_str),
        "start_latlng": start_latlng,
        "distance": run_data["mileage"] * 1000,
        "moving_time": timedelta(seconds=(run_data["duration"]*1000)),
        "elapsed_time": timedelta(
            seconds=int((run_data["endTime"] - run_data["startTime"]) / 1000)
        ),
        "average_speed": run_data["speedAvg"],
        "max_speed": run_data["maxSpeed"],
        "location_country": "",
    }

    if with_download_gpx:
        gpx_data = parse_points_to_gpx(points, run_data["startTime"])
        download_ichebao_gpx(gpx_data, str(run_data["startTime"]), run_data)

    return namedtuple("x", d.keys())(*d.values())


def download_ichebao_gpx(gpx_data, ichebao_id, raw_data):
    try:
        print(f"downloading ichebao_id {str(ichebao_id)} gpx")
        file_path = os.path.join(GPX_FOLDER, str(ichebao_id) + ".gpx")
        with open(file_path, "w") as fb:
            fb.write(gpx_data)

        print(f"downloading ichebao_id {str(ichebao_id)} raw data")
        raw_file_path = os.path.join(GPX_FOLDER, str(ichebao_id) + ".json")
        with open(raw_file_path, "w") as fw:
            fw.write(str(raw_data))
    except:
        print(f"wrong id {ichebao_id}")
        pass


def parse_points_to_gpx(run_points_data, start_time):
    points_dict_list = []
    for point in run_points_data:
        points_dict = {
            "latitude": point["lat"],
            "longitude": point["lon"],
            "time": datetime.utcfromtimestamp(
                (point["time"] + start_time) / 1000
            ),
        }
        points_dict_list.append(points_dict)
    gpx = gpxpy.gpx.GPX()
    gpx.nsmap["gpxtpx"] = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.name = "gpx from keep"
    gpx.tracks.append(gpx_track)
    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    for p in points_dict_list:
        point = gpxpy.gpx.GPXTrackPoint(**p)
        gpx_segment.points.append(point)

    return gpx.to_xml()


def get_all_ichebao_tracks(email, password, old_tracks_ids, with_download_gpx=False, with_all=False, sign=""):
    if with_download_gpx and not os.path.exists(GPX_FOLDER):
        os.mkdir(GPX_FOLDER)
    s = requests.Session()
    s, headers = login(s, email, password, sign)
    tracks = []
    today = datetime.today()
    startDay = today - timedelta(days=60 if with_all else 1)
    startDay = datetime(startDay.year, startDay.month,
                        1 if with_all else startDay.day, 0, 0)
    duration = (today - startDay).days
    while duration >= 0:
        d = today - timedelta(days=duration)
        duration = duration - 1
        begin = datetime(d.year, d.month, d.day, 0, 0)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)
        data = {"beginTime": begin.timestamp() * 1000, "endTime": end.timestamp()
                * 1000, "vehicleId": CAR_ID}
        r = s.post(DAY_API, headers=headers, json=data)
        if not r.json()["data"]:
            continue
        run = r.json()["data"][0]
        r = s.post(DETAIL_API, headers=headers, json=data)
        run["points"] = r.json()["data"]
        track = parse_raw_data_to_nametuple(
            run, old_tracks_ids, with_download_gpx)
        tracks.append(track)

        print(f"parse done {datetime.fromtimestamp(track.id/1000)}")
        time.sleep(1)
    return tracks


def run_ichebao_sync(email, password, with_download_gpx=False, with_all=False, sign=""):
    generator = Generator(SQL_FILE)
    old_tracks_ids = generator.get_old_tracks_ids()
    new_tracks = get_all_ichebao_tracks(
        email, password, old_tracks_ids, with_download_gpx, with_all, sign)
    generator.sync_from_app(new_tracks)
    activities_list = generator.load()
    with open(JSON_FILE, "w") as f:
        json.dump(activities_list, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phone_number", help="i-chebao login phone number")
    parser.add_argument("password", help="i-chebao login password")
    parser.add_argument("sign", help="i-chebao login sign")
    parser.add_argument(
        "--with-gpx",
        dest="with_gpx",
        action="store_true",
        help="get all keep data to gpx and download",
    )
    parser.add_argument(
        "--all",
        dest="all",
        action="store_true",
        help="get all day data"
    )

    options = parser.parse_args()
    print("options: ", options)

    run_ichebao_sync(options.phone_number, options.password,
                     options.with_gpx, options.all, options.sign)
