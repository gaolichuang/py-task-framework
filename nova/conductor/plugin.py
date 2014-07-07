'''
Created on 20140622

@author: gaolichuang@gmail.com
'''

from oslo.config import cfg

from nova.objects import base as objects_base
from nova import rpcclient
from nova.db import base


CONF = cfg.CONF
CONF.import_opt('topic', 'nova.conductor.api', group='conductor')

class BaseRpcApi(rpcclient.RpcProxy):

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        super(BaseRpcApi, self).__init__(
            topic=CONF.conductor.topic,
            default_version=self.BASE_RPC_API_VERSION,
            serializer=objects_base.NovaObjectSerializer())
        self.client = self.get_client()

class BaseConductor(base.Base):
    def __init__(self, db_driver = None):
        super(BaseConductor, self).__init__(db_driver)