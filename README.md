
[![Build Status](https://travis-ci.org/jimboca/udi-camera-poly.svg?branch=master)](https://travis-ci.org/jimboca/udi-camera-poly)

# harmony-polyglot

This is the Camera Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
(c) JimBoCA aka Jim Searle
MIT license. 

This node server is intended to support IP Cameras.

## Support Cameras

1. All Known Foscams
2. All Amcrest cameras supported by [Python Amcrest](https://github.com/tchellomello/python-amcrest)

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Add NodeServer in Polyglot Web
4. Go to the Camera NodeServer Configuration Page
  * Set user and password for camera, all cameras must use the same.
4. Open the admin console (if you already had it open, the close and re-open)
5. You should get a new node 'Camera Controller', select it
6. The auto-discover can find Foscam cameras, so if you have some, enable Foscam Polling, 10s is usually enough.
7. If you have other support cameras, they have to bbe added as Manual entries, in the NodeServer Configuration as detailed in the next sextion.
8. Then click the 'Disover' for the Camera Controller node
   * This should find your Cameras add them to the ISY
   * While this is running you can view the nodeserver log in the Polyglot UI to see what it's doing

### Manual Camera Entries

If the discover does not work, or you prefer to not use it, or you have other supported cameras,
you can add customParms in the Polyglot Web UI to tell it about your cameras.

Create a param with the name 'cam_xx' with a value: { "type:" "Amcrest", "host": "192.168.1.86" }
The _xx is not important, it just needs to be unique for each one.  If your port is not the default
then add port as well.  There is a cam_example in the Polyglot configuration you can copy/paste.

#### Allowed Types:
   Type must currently be:
   * Amcrest

## Grouping the Camers

Each Camera is added with a Motion node, you can right-click the camera and select Group devices.


## Requirements

1. Polyglot V2 itself should be run on Raspian Stretch.
  To check your version, ```cat /etc/os-release``` and the first line should look like
  ```PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"```. It is possible to upgrade from Jessie to
  Stretch, but I would recommend just reimaging the SD card.  Some helpful links:
   * https://www.raspberrypi.org/blog/raspbian-stretch/
   * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
1. This has only been tested with ISY 5.0.11C so it is not garunteed to work with any other version.

# Upgrading

Open the Polyglot web page, go to nodeserver store and click "Update" for "Camera".

# Release Notes

- 2.0.0 01/28/2018
   - Not offically released
