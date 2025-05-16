"""
Schweizmobil.ch Direct GPX Downloader

This script:
- Authenticates to schweizmobil.ch with your username and password
- Downloads your list of tracks
- For a selected track, fetches detailed information
- Converts the track profile and via points from Swiss LV03 to WGS84 coordinates
- Exports the track as a GPX file, including waypoints for all via points

Usage:
    python Schweizmobil_direct_GPX_downloader.py --username <USERNAME> --password <PASSWORD> --track "<TRACK NAME>"

If no arguments are given, the script will prompt for them interactively.

Features:
- If multiple tracks have the same name, you will be prompted to select the correct one, with additional info (filter name, creation/modification date).
- If the track is not found, all available tracks are listed.
- Coordinates are automatically converted from Swiss LV03 to WGS84 for GPX export.

Requirements:
- requests
- pyproj

Author Philipp Kündig, 16. May 2025
"""

import requests
import json
import argparse
import getpass
from pyproj import Transformer
import datetime
import os

def lv03_to_wgs84(easting, northing, transformer):
    """
    Convert Swiss LV03 coordinates to WGS84 (lat, lon).
    """
    lon, lat = transformer.transform(easting, northing)
    return lat, lon

def parse_profile(profile_str):
    """
    Parse the 'profile' string from the API, which is a list of [easting, northing, elevation, distance].
    """
    return json.loads(profile_str.replace("'", '"'))

def write_gpx(track_name, points, via_points, output_file, transformer):
    """
    Write the track and via points to a GPX file.
    - track_name: Name of the track
    - points: List of [easting, northing, elevation, distance]
    - via_points: List of [easting, northing]
    - output_file: Output GPX filename
    - transformer: pyproj Transformer for LV03->WGS84
    """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<gpx version="1.1" creator="schweizmobil.ch-API converter">\n')
        f.write(f'  <metadata><name>{track_name}</name></metadata>\n')
        # Write via_points as waypoints
        for idx, pt in enumerate(via_points):
            easting, northing = pt
            lat, lon = lv03_to_wgs84(easting, northing, transformer)
            name = "Starting point" if idx == 0 else ("Destination" if idx == len(via_points) - 1 else "Waypoint")
            f.write(f'  <wpt lat="{lat:.10f}" lon="{lon:.10f}">\n')
            f.write(f'    <ele></ele>\n')
            f.write(f'    <name>{name}</name>\n')
            f.write('  </wpt>\n')
        # Write track points
        f.write(f'  <trk><name>{track_name}</name><trkseg>\n')
        for pt in points:
            easting, northing, elevation, _ = pt
            lat, lon = lv03_to_wgs84(easting, northing, transformer)
            f.write(f'    <trkpt lat="{lat:.10f}" lon="{lon:.10f}"><ele>{elevation:.1f}</ele></trkpt>\n')
        f.write('  </trkseg></trk>\n')
        f.write('</gpx>\n')

def load_credentials_from_file(filepath):
    """
    Load credentials from a file.
    The file should contain two lines:
        username=your_username
        password=your_password

    Returns a dict with 'username' and 'password', or None if missing or malformed.
    """
    creds = {}
    if not os.path.isfile(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                creds[key.strip()] = value.strip()
    # Check for missing or empty values and extra keys
    if (
        "username" in creds and creds["username"]
        and "password" in creds and creds["password"]
        and len(creds) == 2
    ):
        return creds
    print(
        f"Credentials file '{filepath}' is missing required fields or is malformed.\n"
        "It should contain exactly two lines:\n"
        "username=your_username\npassword=your_password"
    )
    return None

def main():
    """
    Main entry point for the script.
    Handles argument parsing, authentication, track selection, and GPX export.
    """
    parser = argparse.ArgumentParser(
        description="Download a track from schweizmobil.ch and export as GPX."
    )
    parser.add_argument(
        "--username", "-u", help="Your schweizmobil.ch username"
    )
    parser.add_argument(
        "--password", "-p", help="Your schweizmobil.ch password"
    )
    parser.add_argument(
        "--track", "-t", help="Name of the track to export (case-sensitive)"
    )
    parser.add_argument(
        "--credentials-file", "-c",
        help="Path to a file containing username and password (format: username=... and password=...)"
    )
    args = parser.parse_args()

    creds = {}
    # 1. Try credentials file from argument
    if args.credentials_file:
        creds = load_credentials_from_file(args.credentials_file) or {}
    # 2. Try default credentials.txt if not already loaded
    if not creds:
        default_file = "credentials.txt"
        if os.path.isfile(default_file):
            creds = load_credentials_from_file(default_file) or {}
    # 3. Use command line arguments if provided
    if args.username:
        creds["username"] = args.username
    if args.password:
        creds["password"] = args.password

    # 4. Prompt interactively if still missing or empty
    if "username" not in creds or not creds["username"]:
        creds["username"] = input("Schweizmobil.ch username: ")
    if "password" not in creds or not creds["password"]:
        creds["password"] = getpass.getpass("Schweizmobil.ch password: ")

    # Final check
    if not creds.get("username") or not creds.get("password"):
        print("Username or password missing. Exiting.")
        exit(1)

    username = creds["username"]
    password = creds["password"]
    track_name = args.track or input("Track name (case-sensitive): ")

    pre = 'https://map.schweizmobil.ch'
    session = requests.Session()
    session.headers = {}

    # Authenticate
    payload = json.dumps({
        "username": username,
        "password": password
    })
    login_response = session.post(pre + '/api/4/login', data=payload)
    if login_response.status_code != 200:
        print("Login failed! Please check your username and password.")
        exit(1)

    # Get tracks
    response = session.get(pre + '/api/5/tracks')
    if response.status_code != 200:
        print("Failed to fetch tracks. Please check your connection or credentials.")
        exit(1)
    tracks = response.json()

    # LV03 (EPSG:21781) to WGS84 (EPSG:4326)
    transformer = Transformer.from_crs(21781, 4326, always_xy=True)

    # Find all tracks with the given name
    matching_tracks = [t for t in tracks if t["name"] == track_name]

    if not matching_tracks:
        print(f"\nTrack '{track_name}' not found in your schweizmobil.ch account.")
        print("Available tracks:")
        for t in tracks:
            print(f"- {t['name']} (ID: {t['id']})")
        exit(1)

    # If multiple tracks with the same name, ask the user to choose
    if len(matching_tracks) > 1:
        print(f"\nMultiple tracks found with the name '{track_name}':")
        # Fetch details for each matching track to show more info
        detailed_tracks = []
        for idx, t in enumerate(matching_tracks):
            detail_response = session.get(pre + '/api/4/tracks/' + str(t['id']))
            if detail_response.status_code == 200:
                detail = detail_response.json()
                props = detail.get("properties", {})
                created = props.get('created_at', 'unknown')
                modified = props.get('modified_at', 'unknown')
                filter_name = props.get('filter_name', 'N/A')

                # Format date/time for user-friendly display
                def fmt(dt):
                    try:
                        return datetime.datetime.fromisoformat(dt).strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        return dt

                created_fmt = fmt(created)
                modified_fmt = fmt(modified)

                print(f"{idx+1}: {filter_name} | ID={t['id']} | Created: {created_fmt} | Modified: {modified_fmt}")
                detailed_tracks.append(detail)
            else:
                print(f"{idx+1}: (details unavailable) | ID={t['id']}")
                detailed_tracks.append(None)
        while True:
            try:
                choice = int(input(f"Select a track (1-{len(matching_tracks)}): "))
                if 1 <= choice <= len(matching_tracks):
                    selected_detail = detailed_tracks[choice - 1]
                    if selected_detail is None:
                        print("Details for this track are unavailable. Please choose another.")
                        continue
                    selected_track = matching_tracks[choice - 1]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")
        # Use the already-fetched details
        track = selected_detail
    else:
        selected_track = matching_tracks[0]
        detail_response = session.get(pre + '/api/4/tracks/' + str(selected_track['id']))
        if detail_response.status_code != 200:
            print(f"Failed to fetch details for track '{track_name}'.")
            exit(1)
        track = detail_response.json()

    # Fetch and export the selected track
    props = track["properties"]
    profile_str = props['profile']
    points = parse_profile(profile_str)
    via_points = json.loads(props["via_points"])
    output_file = f"{track_name}.gpx"
    write_gpx(track_name, points, via_points, output_file, transformer)
    print(f"\nGPX written: {output_file}")

    print("Done.")

if __name__ == "__main__":
    main()


