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

from nova import exception
from nova.objects import base as objects_base
from nova.openstack.common import jsonutils
from nova.openstack.common.rpc import common as rpc_common
from nova.openstack.common import importutils
from nova import rpcclient

CONF = cfg.CONF

def _instance_host(host, instance):
    '''Get the destination host for a message.

    :param host: explicit host to send the message to.
    :param instance: If an explicit host was not specified, use
                     instance['host']

    :returns: A host
    '''
    if host:
        return host
    if not instance:
        raise exception.NovaException(_('No compute host specified'))
    if not instance['host']:
        raise exception.NovaException(_('Unable to find host for '
                                        'Instance %s') % instance['uuid'])
    return instance['host']


class AndroidAPI(rpcclient.RpcProxy):
    """Client side of the conductor RPC API
    """

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self,plugin_class_name=None):

        super(AndroidAPI, self).__init__(
            topic=CONF.sample.topic,
            default_version=self.BASE_RPC_API_VERSION,
            serializer=objects_base.NovaObjectSerializer())
        self.client = self.get_client()
    def create_android(self, context, instance):
        cctxt = self.client.prepare(version='1.0')
        return cctxt.call(context, 'create_android', instance=instance)

    def active_android(self, context, instance):
        cctxt = self.client.prepare(server=_instance_host(None, instance))
        cctxt.cast(context, 'active_android', instance=instance)

    def destroy_android(self, context, instance):
        cctxt = self.client.prepare(server=_instance_host(None, instance))
        cctxt.cast(context, 'destroy_android', instance=instance)

    def deactive_android(self, context, instance):
        cctxt = self.client.prepare(server=_instance_host(None, instance))
        cctxt.cast(context, 'deactive_android', instance=instance)

    def start_android(self, context, instance):
        cctxt = self.client.prepare(server=_instance_host(None, instance))
        cctxt.cast(context, 'start_android', instance=instance)

    def stop_android(self, context, instance):
        cctxt = self.client.prepare(server=_instance_host(None, instance))
        cctxt.cast(context, 'stop_android', instance=instance)