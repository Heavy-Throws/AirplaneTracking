# OpenSky Data Reader and Angle Calculator

## Purpose
This software will request live ADB-S within a bounding box, search for the closest aircraft with recent data, and then calculate the angles required to point a PAN/TILT device towards it. 

## OpenSky API
There are [restrictions and limitations] (https://openskynetwork.github.io/opensky-api/rest.html#limitations) to the data collected. 
Since the data will be received every 5 or 10 seconds (depending on whether you're a registered user) this software also estimate the position until new data arrives.

## TODO
- [x] README
- [ ] License 
- [ ] Visualizations
- [ ] Configuration for all items needed
  - [x] API credentials
  - [ ] Serial COM 
  - [ ] GPS "me" position
  - [ ] Size of bounding box
- [ ] Auto-generate bounding box based on "me" GPS point and radius
- [ ] 