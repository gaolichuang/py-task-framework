#    Copyright 2012 IBM Corp.
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

"""Handles all requests to the conductor service."""

from oslo.config import cfg

from nova import baserpc


from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import importutils
from nova.openstack.common.rpc import common as rpc_common
from nova import utils

sample_opts = [
    cfg.StrOpt('topic',
               default='sample',
               help='the topic conductor nodes listen on'),
    cfg.StrOpt('manager',
               default='nova.sample.manager.SampleManager',
               help='full class name for the Manager for nova sample'),
    cfg.IntOpt('workers',
               help='Number of workers for OpenStack Conductor service'),
]
sample_group = cfg.OptGroup(name='sample',
                               title='Sample Options')
CONF = cfg.CONF
CONF.register_group(sample_group)
CONF.register_opts(sample_opts, sample_group)

from nova.sample import manager
from nova.sample import rpcapi

LOG = logging.getLogger(__name__)



class API(object):
    """A local version of the conductor API that does database updates
    locally instead of via RPC.
    """

    def __init__(self, plugin_class_name = None):
        # TODO(danms): This needs to be something more generic for
        # other/future users of this sort of functionality.
        self._manager = utils.ExceptionHelper(manager.SampleManager())
        self._rpcapi = rpcapi.SampleAPI()

    def wait_until_ready(self, context, *args, **kwargs):
        # nothing to wait for in the local case.
        pass

