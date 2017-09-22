#!/bin/sh

# A Java classpath that minimaly includes BaseX.jar, ModelInterface.jar,
# and BaseX's supporting libs (required to run the HTTP server)
CLASSPATH=$HOME/lib/basex/BaseX.jar:$HOME/lib/ModelInterface.jar:$HOME/lib/
basex/lib/*

if [ "$1" = "stop" ] ; then
   # The user just wants to stop an already running server
   java -cp $CLASSPATH org.basex.BaseXHTTP stop
   exit 0
elif [ $# -ne "1" ] ; then
   echo "Usage:"
   echo "$0 <path to databases>"
   echo "$0 stop"
   exit 1
fi

DBPATH=$1
echo "DB Path: $DBPATH"

# Ensure BaseX users have been set up since remote access will require a
# username and password.  To run Model Interface queries requires READ
access.
if [ ! -e "${DBPATH}/users.xml" ] ; then
   echo "No users.xml found in $DBPATH"
   echo "Enter a user name to create one now (or CTRL-C to copy/create a
users.xml manually):"
   read username
   java -cp $CLASSPATH -Dorg.basex.DBPATH=$DBPATH org.basex.BaseX
-c"CREATE USER $username;GRANT READ TO $username"
fi

# Run the server, note only the DBPATH is overriden here, all other
settings are
# defined in ~/.basex
java -cp $CLASSPATH -Dorg.basex.DBPATH=$DBPATH org.basex.BaseXHTTP
