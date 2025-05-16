# schweizmobil-downloader

A Python script to download a route from [schweizmobil.ch](https://map.schweizmobil.ch/) directly as a `.gpx` file. Useful for importing routes into tools like [Marschzeittabelle.ch](https://marschzeittabelle.ch/).

## Features

- Authenticates to [schweizmobil.ch](https://map.schweizmobil.ch/) with your username and password
- Supports loading credentials from a file, so you don't have to enter them every time
- Lists your tracks and allows selection by name (with extra info if duplicates exist)
- Converts Swiss LV03 coordinates to WGS84 for GPX export
- Exports the route as a GPX file, including waypoints for all via points

## Requirements

- Python 3.7+
- [requests](https://pypi.org/project/requests/)
- [pyproj](https://pypi.org/project/pyproj/)

Install dependencies with:
```sh
pip install requests pyproj
```

## Usage

You can run the script from the command line:

```sh
python Schweizmobil_direct_GPX_downloader.py --username <YOUR_USERNAME> --password <YOUR_PASSWORD> --track "<TRACK_NAME>"
```

Or, to avoid entering your credentials every time, create a file called `credentials.txt` in the same directory with the following content:
```
username=your_username
password=your_password
```
Then run:
```sh
python Schweizmobil_direct_GPX_downloader.py --track "<TRACK_NAME>"
```
Or specify a custom credentials file:
```sh
python Schweizmobil_direct_GPX_downloader.py --credentials-file mycreds.txt --track "<TRACK_NAME>"
```

If you omit any arguments, the script will prompt you for them interactively.

The resulting GPX file will be saved in the current directory.
