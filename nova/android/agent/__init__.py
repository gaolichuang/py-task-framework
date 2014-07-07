
from oslo.config import cfg
from nova.android import api as android_api

CONF = cfg.CONF

def API(*args, **kwargs):
    api = android_api.API
    return api(*args, **kwargs)