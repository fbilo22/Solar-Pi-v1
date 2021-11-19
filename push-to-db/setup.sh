#!/bin/sh -

# This script initialize the needed software parts to run sqlite3
# database storage & push-to-db.py script

echo "Install SQLite3"
sudo apt-get install sqlite

echo "Create storage path /var/local/sqlite"
sudo mkdir /var/local/sqlite
# /var/local is owned by root and accessible to group staff
# so /var/local/sqlite should also do so.

echo "Add user 'pi' to group 'staff'"
sudo usermod -a -G staff pi
echo "Set 'staff' as group for 'sqlite' folder"
sudo chgrp staff /var/local/sqlite
echo "Give right to group 'staff' on 'sqlite' folder"
sudo chmod g+rwx /var/local/sqlite

echo "Install push-to-db.ini to /etc/solarpi/"
# file in /etc/solarpi/push-to-db.ini can be read by user pi
sudo mkdir /etc/solarpi
sudo cp inifile.sample /etc/solarpi/push-to-db.ini

echo "Install push-to-db.log in /var/log/solarpi/"
sudo mkdir /var/log/solarpi
sudo chgrp staff /var/log/solarpi
sudo chmod g+rw /var/log/solarpi

# Needs to reload user configuration (and groups)
# so user "pi" can act with "staff" group access
# without logout/login again.
# Executing command with 'sudo su ...' will do it
# for the current user "pi" but having "staff" group
# attached immediately to it
# sudo su -c 'command' $USER
echo "Check user groups, staff must now be attached"
sudo su -c 'groups' $USER

# owner and group  would be the current user (pi)
sudo su -c 'touch /var/log/solarpi/push-to-db.log' $USER
# Set permission to -rw-rw-r--
sudo su -c 'sudo chmod +664 /var/log/solarpi/push-to-db.log' $USER
# change owner to root (keep pi as the group)
sudo su -c 'sudo chown root /var/log/solarpi/push-to-db.log' $USER

echo "Creating solarpi.db in var/local/sqlite/"
# Initialize the pythonic databases to run the push-to-db.py python script.
# push-to-db.py push MQTT data to SQLite3 database
sudo su -c 'cat createdb.sql | sqlite3 /var/local/sqlite/solarpi.db' $USER

echo "Installing python libraries"
sudo pip install paho-mqtt

echo "Done!"

if $(groups | fgrep -wq -e staff); then
   echo "Great staff is already in user groups :)"
else
   echo "-------------------------------------"
   echo "You must logout/login to update your"
   echo "current session user groups !"
   echo "------------------------------------"
fi
