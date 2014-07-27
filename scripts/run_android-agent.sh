#!/bin/bash
# Author: gaolichuang@gmail.com

usage="usage: run_conductor.sh (start|stop) [stdio]"

if [ $# -lt 1 ]; then
  echo $usage
  exit -1
fi

PYTHON=python
WAIT_SECS=120
operation=$1
output=$2
BIN_DIR=/Application/nova-framework/
BIN_NAME=.venv/bin/nova-android-agent
CONF_FILE=$BIN_DIR/nova/etc/nova/nova.conf
LOG_DIR=$BIN_DIR/nova/

LOG_NAME=`basename $BIN_NAME`_log.txt

cmd="$PYTHON $BIN_DIR/$BIN_NAME
  --config-file=$CONF_FILE
"
getin_venv(){
source $BIN_DIR/../.venv/bin/activate
}
#getin_venv

stop() {
  pid=$(ps aux | grep `basename $BIN_NAME` |grep `basename $CONF_FILE`| awk '{print $2}')
  echo pid:$pid
  if [ "$pid" == "" ]; then
    echo "$BIN_NAME not found"
    return 0
  fi
  echo "stop $BIN_NAME"
  kill -USR1 $pid
  time_left=$WAIT_SECS
  while [ $time_left -gt 0 ]; do
    if [ ! -e /proc/$pid ]; then
      return 0
    fi
    sleep 1
    time_left=$(($time_left-1))
  done
  return 1
}

start() {
  echo $cmd
#  ulimit -c unlimited
  rm $LOG_DIR/$LOG_NAME
  if [ -z $output ];then
    $cmd 2>>$LOG_DIR/$LOG_NAME 1>>$LOG_DIR/$LOG_NAME &
  elif [ $output == 'stdio' ];then
    $cmd
  else
    $cmd 2>>$LOG_DIR/$LOG_NAME 1>>$LOG_DIR/$LOG_NAME &
  fi
  time_left=$WAIT_SECS
  while [ $time_left -gt 0 ]; do
    cnt=$(ps aux | grep $BIN_NAME | grep -c `basename $CONF_FILE`)
    if [ $cnt != 0 ]; then
      return 0
    fi
    sleep 1
    time_left=$(($time_left-1))
  done
  return 1
}

if [ $operation == "start" ]; then
  start
elif [ $operation == "stop" ]; then
  stop
else
  echo $usage
fi
succ=$?
if [ $succ -eq 0 ]; then
echo $BIN_NAME $operation accomplished
else
echo $BIN_NAME $operation failed
fi

exit $succ
