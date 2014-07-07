'''
Created on 20140624

@author: gaolichuang@gmail.com

android status -- task status -->> android status
        READY -- ACTIVING -->> ACTIVE
        ACTIVE -- DEACTIVING -->> READY
        ACTIVE -- STARTING -->> WORKING
        WORKING -- STOPING -->> ACTIVE
        WORKING --DEACTIVING -->> READY
'''

READY = 'ready'
ACTIVE = 'active'
WORKING = 'working'