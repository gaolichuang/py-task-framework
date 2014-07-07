#    Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Client side of the conductor RPC API."""

from oslo.config import cfg

from nova.objects import base as objects_base
from nova.openstack.common import jsonutils
from nova.openstack.common.rpc import common as rpc_common
from nova.openstack.common import importutils
from nova import rpcclient

CONF = cfg.CONF
CONF.import_opt('conductor_plugin_class_name', 'nova.conductor.api', group='conductor')

rpcapi_cap_opt = cfg.StrOpt('conductor',
        help='Set a version cap for messages sent to conductor services')
CONF.register_opt(rpcapi_cap_opt, 'upgrade_levels')



class ConductorAPI(rpcclient.RpcProxy):
    """Client side of the conductor RPC API
    """

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self,plugin_class_name=None):

        super(ConductorAPI, self).__init__(
            topic=CONF.conductor.topic,
            default_version=self.BASE_RPC_API_VERSION,
            serializer=objects_base.NovaObjectSerializer())
        self.client = self.get_client()

        if plugin_class_name is None:
            plugin_class_name = '%s.RpcApiPlugin' % CONF.conductor.conductor_plugin_class_name
        plugin_class = importutils.import_class(plugin_class_name)
        self.plugin = plugin_class()

    def __getattr__(self, key):
        plugin = self.__dict__.get('plugin', None)
        return getattr(plugin, key)

    def service_get_all_by(self, context, topic=None, host=None, binary=None):
        cctxt = self.client.prepare(version='1.28')
        return cctxt.call(context, 'service_get_all_by',
                          topic=topic, host=host, binary=binary)

    def action_event_start(self, context, values):
        values_p = jsonutils.to_primitive(values)
        cctxt = self.client.prepare(version='1.25')
        return cctxt.call(context, 'action_event_start', values=values_p)

    def action_event_finish(self, context, values):
        values_p = jsonutils.to_primitive(values)
        cctxt = self.client.prepare(version='1.25')
        return cctxt.call(context, 'action_event_finish', values=values_p)

    def service_get_by_id(self, context, service_id):
        cctxt = self.client.prepare(version='1.27')
        return cctxt.call(context, 'service_get_by_id', service_id=service_id)

    def service_create(self, context, values):
        cctxt = self.client.prepare(version='1.27')
        return cctxt.call(context, 'service_create', values=values)

    def service_destroy(self, context, service_id):
        cctxt = self.client.prepare(version='1.29')
        return cctxt.call(context, 'service_destroy', service_id=service_id)

    def service_update(self, context, service, values):
        service_p = jsonutils.to_primitive(service)
        cctxt = self.client.prepare(version='1.34')
        return cctxt.call(context, 'service_update',
                          service=service_p, values=values)
