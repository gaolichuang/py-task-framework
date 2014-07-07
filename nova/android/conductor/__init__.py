
from oslo.config import cfg
from nova.openstack.common.rpc import common as rpc_common
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.objects import base as objects_base
from nova.openstack.common import jsonutils
from nova.conductor import plugin
from nova import db as db_api
from nova import exception

LOG = logging.getLogger(__name__)


class PluginAPI(object):
    ''' Uniq API for this conductor, manager can be rpcapi or Conductor'''
    def __init__(self, manager):
        self.manager =  manager

    def android_get_all(self, context,include_delete=False):
        return self.manager.android_get_all(context,include_delete=include_delete)

    def android_get_all_by_name(self, context, name):
        return self.manager.android_get_all_by_name(context,name=name)

    def android_create(self, context, values):
        return self.manager.android_create(context,values=values)

    def android_destroy(self, context, uuid):
        return self.manager.android_destroy(context,uuid=uuid)

    def android_update(self, context, uuid, values):
        return self.manager.android_update(context,uuid=uuid,values=values)



class RpcApiPlugin(plugin.BaseRpcApi):
    '''rpc client for Conductor'''
    def __init__(self):
        super(RpcApiPlugin, self).__init__() 

    def android_get_all(self, context, include_delete):
        cctxt = self.client.prepare(version='1.0')
        return cctxt.call(context, 'android_get_all', include_delete=include_delete)

    def android_get_all_by_name(self, context, name):
        cctxt = self.client.prepare(version='1.0')
        return cctxt.call(context, 'android_get_all_by_name', name=name)

    def android_create(self, context, values):
        cctxt = self.client.prepare(version='1.0')
        return cctxt.call(context, 'android_create', values=values)

    def android_destroy(self, context, uuid):
        cctxt = self.client.prepare(version='1.0')
        return cctxt.call(context, 'android_destroy', uuid=uuid)

    def android_update(self, context, uuid, values):
        cctxt = self.client.prepare(version='1.0')
        return cctxt.call(context, 'android_update', uuid=uuid,values=values)



class ConductorManagerPlugin(plugin.BaseConductor):
    '''this code will plugin at nova.conductor.ConductorManager, run at rpc server'''
    def __init__(self):
        super(ConductorManagerPlugin, self).__init__()

    def android_get_all(self, context,include_delete):
        result = self.db.android_get_all(context,include_delete)
        return jsonutils.to_primitive(result)

    def android_get_all_by_name(self, context, name):
        result = self.db.android_get_by_name(context, name)
        return jsonutils.to_primitive(result)

    def android_create(self, context, values):
        result = self.db.android_create(context, values)
        return jsonutils.to_primitive(result)

    @rpc_common.client_exceptions(exception.AndroidNotFound)
    def android_destroy(self, context, uuid):
        self.db.android_destroy(context,uuid)

    @rpc_common.client_exceptions(exception.AndroidNotFound)
    def android_update(self, context, uuid, values):
        result = self.db.android_update(context, uuid, values)
        return result