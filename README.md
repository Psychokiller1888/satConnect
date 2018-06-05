# satConnect

## An easy way to add satellites to your Snips main unit

This tool, when run on both your Snips main unit and your freshly installed Snips satellite will help you configure both devices!

* The main unit needs Snips completly installed
* The satellites only need "snips-audio-server" installed. Follow the same instructions as for snips but instead of ```sudo apt-get install snips-platform-voice``` do ```sudo apt-get install snips-audio-server```

## Install (First time...)

* On both the new satellite and the main unit ```git clone https://github.com/Psychokiller1888/satConnect.git```
* On both the new satellite and the main unit ```cd satConnect```
* On both the new satellite and the main unit ```sudo pip install -r requirements.txt```
* On the main unit ```sudo python server.py```
* On the satellite ```sudo python connect.py```
* Follow the instructions on the satellite terminal

## Install (Again)

If you already used this tool, you don't need to do anything on the main unit, but follow the steps only for the satellites as the script is already installed on the main unit. 

* On the new satellite ```git clone https://github.com/Psychokiller1888/satConnect.git```
* On both the new satellite and the main unit ```cd satConnect```
* On the new satellite ```sudo pip install -r requirements.txt```
* On the main unit ```sudo python server.py```
* On the satellite ```sudo python connect.py```
* Follow the instructions on the satellite terminal

## Why sudo?

Because we need to write to the snips configuration file

## Be aware

* Your current settings in toml file will be kept, but commented out configurations will be removed!
* This is under development
* A backup of your configurations can be found in backup.txt on both devices
* This script configures the satellite to stream everything to the main unit. On request I can make the script evolve, if you want the hotword on the satellites per exemple

## Flags
You can start the scripts with the following flags. Exemple: ```sudo python server.py --remove-backup```
* --remove-backup: This will remove any created backup before recreating it
* --restore-backup: This will restore the backup, restoring the original snips.toml file
* --disconnect: For satellites only, removes the satellite from main unit
