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


class SampleAPI(rpcclient.RpcProxy):
    """Client side of the conductor RPC API
    """

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self,plugin_class_name=None):

        super(SampleAPI, self).__init__(
            topic=CONF.sample.topic,
            default_version=self.BASE_RPC_API_VERSION,
            serializer=objects_base.NovaObjectSerializer())
        self.client = self.get_client()
