
[![Build Status](https://travis-ci.org/jimboca/udi-camera-poly.svg?branch=master)](https://travis-ci.org/jimboca/udi-camera-poly)

# udi-camera-polyglot

This is the Camera Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
(c) JimBoCA aka Jim Searle
MIT license.

This node server is intended to support IP Cameras.

## Supported Cameras

### Foscam MJPEG

  This is any Foscam Camera MJPEG camera.  This should be any camera that uses this interface  [Foscam IP Camera CGI](docs/ipcam_cgi_sdk.pdf) which includes the non-HD Smarthome INSTEON cameras that are rebranded Foscam's.
  * These cameras allow configuring a push notification when motion is sensed so it's seen on the ISY immediatly, but then the Polyglot has to poll the camera every short poll interval to see when motion is off.
  * All the params are documented in the pdf mentioned above, if you have questions about them, please read that document first.
  * The 'IR LED' only has a set option, and does not display the status because it seems there is no way to get the status of this from the camera that I can find.  If you know how, please tell me!
  * The 'Network LED Mode' is the led_mode from the camera which is defined as:
    * led_mode=0 : LED indicates network connection
    * led_mode=1 : LED indicates connected network type
    * led_mode=2 : LED deactivated except during camera boot

### FoscamHD2 (H.264)

   Any Camera that uses the interface [Foscam IPCamera CGI User Guide](docs/Foscam-IPCamera-CGI-User-Guide-AllPlatforms-2015.11.06.pdf)
   * Presets: To use the Goto preset control you must defined presets named "1", "2", "3", ... on the camera.  I would like to support using the preset names defined on the camera but that would require creating the profile.zip on the fly which is possible, but hasn't been done yet, and not sure it's worth the effort.
   * These cameras do not allow configuring a push notification when motion is sensed so you must enable motion polling which will poll the camera every short poll interval to check for motion.


   Tested with:

|  Model   |     Name    | Hardware Version | Firmware Version | Amba
| -------- |------------ | ---------------- | ---------------- | ----
|  1035    | FI9826P+V2  |   1.5.3.19       | 2.21.2.27        | False
|    50    | FI9828P+V2  |   1.4.1.10       | 2.11.1.133       | False
|  5096    | R2 V4       |   1.11.1.11      | 2.71.1.59        | True
|          | FI9900P     |                  |                  | True?


   Notes:
    * Amba means it uses the "Amba S2L" as documented in section 8 of the pdf above.  If you are not sure if that is needed for your camera enable/disable motion detection and see if the nodeserver log shows <result>-3</result> this may mean we need to update the nodeserver to understand this for your camera.  Currently this is enabled when System Firmware starts with 1.11.  I think the FI9900P Cameras need this enabled but I don't have an example.

If you have a camera that is not on this list, please look for this line in your nodeserver log and send it to me or add it here yourself if you can.
```
2018-03-25 19:24:21,540 INFO     FoscamHD2:CamOutEntry:get_cam_all: model=50, model_name=FI9828P+V2, hardware_ver=1.4.1.10, firmware_ver=2.11.1.133, amba=False
```
Just search for get_cam_all in your log to find them.

### Amcrest

   This uses the [Python Amcrest](https://github.com/tchellomello/python-amcrest) library to control the camera so any that work with that interace should work.
   Currently there is no discovery for this cameras so you need to add them to the nodeserver configuration
   * Presets: To use the Goto preset control you must defined presets named "1", "2", "3", ... on the camera.  I would like to support using the preset names defined on the camera but that would require creating the profile.zip on the fly which is possible, but hasn't been done yet, and not sure it's worth the effort.
   * These cameras do not allow configuring a push notification when motion is sensed so you must enable motion polling which will poll the camera every short poll interval to check for motion.

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Add Camera NodeServer in Polyglot
   * To do a manual install if Polyglot Fails 
      * cd ~/.polyglot/nodeservers
      * git clone https://github.com/jimboca/udi-camera-poly Camera
      * cd Camera
      * ./install.sh
4. Go to the Camera NodeServer Configuration Page
   * Set user and password for camera it may take a few seconds for the default user and password to show up in the configuration page, just wait and they should show up, then change the defaults for your cameras.
   * Currently all cameras must use the same.
4. Open the admin console (if you already had it open, then close and re-open)
   * There is usually no need to reboot the ISY
5. You should see a new node 'Camera Controller', select it
6. The auto-discover can find Foscam cameras so enable Foscam Polling if desired, setting to 10s is usually enough.
7. If you have other support cameras, they have to be added as Manual entries in the NodeServer Configuration as detailed Manual Camera Entries section.
8. Then click the 'Discover' for the Camera Controller node
   * This should find your Cameras add them to the ISY
   * While this is running you can view the nodeserver log in the Polyglot UI to see what it's doing

### Manual Camera Entries

If the discover does not work, or you prefer to not use it, or you have other supported cameras,
you can add customParms in the Polyglot Web UI to tell it about your cameras.

Create a param with the name 'cam_xx' with a value: { "type:" "Amcrest", "host": "192.168.1.86" }
The underscore xx is not important, it just needs to be unique for each one.  If your port is not the default
then add port as well.  There is a cam_example in the Polyglot configuration you can copy/paste.

#### Allowed Types:
   Type must currently be:
   * Amcrest

## Grouping the Cameras

Each Camera is added with a Motion node, you can right-click the camera and select Group devices.

## Requirements

1. Polyglot V2 itself should be run on Raspian Stretch.
  To check your version, ```cat /etc/os-release``` and the first line should look like
  ```PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"```. It is possible to upgrade from Jessie to
  Stretch, but I would recommend just reimaging the SD card.  Some helpful links:
   * https://www.raspberrypi.org/blog/raspbian-stretch/
   * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
1. This has only been tested with ISY 5.0.11 so it is not confirmed to work with any prior version.

# Upgrading

Open the Polyglot web page, go to nodeserver store and click "Update" for "Camera".

# Release Notes

- 2.1.10
  - Fix setting number of cameras on controller
  - Setting debug mode actually changes the logging mode
- 2.1.9
  - Fix initialization of controller ST
  - Add controller heartbeat which sends DON/DOF
    - MUST Select "Install Profile" on controller after updating.
- 2.1.8
  - Add info line like: get_cam_all: model=50, model_name=FI9828P+V2, hardware_ver=1.4.1.10, firmware_ver=2.11.1.133, amba=False
- 2.1.7
  - https://github.com/jimboca/udi-camera-poly/issues/1
  - https://github.com/jimboca/udi-camera-poly/issues/3
- 2.1.6
  - Fixes for some FoscamHD2 commands which have been broken since release.
- 2.1.5
  - Minor fixes for flakey cameras
- 2.1.4 02/16/2018
  - Really fix Amcrest causing a crash
- 2.1.3 02/12/2018
  - Fix for Amcrest causing a crash
- 2.1.2 02/11/2018
  - Add zip to requirements
- 2.1.1 02/11/2018
  - Minor profile fixes
- 2.1.0 02/10/2018
  - First release
- 2.0.0 01/28/2018
  - Not offically released
