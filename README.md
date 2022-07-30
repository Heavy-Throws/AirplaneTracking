# Articulated Camera for Flight Tracking

## Purpose
Purely educational. This project is not meant to be used by others, but rather a history of me learning the following concepts: 
- Python 
- API calls
- Serial communication
- Configuration files
- Creating an arbitrary motor command protocol
- Visualizing GIS-like data

## Code Navigation
### Tracking Software
This is python code which handles all API calls and angle calculations. It sends PAN and TILT target angles to the motor controller. 

## Motor Control
Arduino (C++) code which accepts PAN and TILT angle targets and meets them. Uses [laurb9's Stepper Drivier Library](https://github.com/laurb9/StepperDriver).

## Installation
DON'T. It's not ready yet.

## Use
Feel free to download and read through the code - but I don't promise it will work. 

## TODO
- [x] README
- [ ] License 
- [ ] Visualization 
- [ ] Configurations