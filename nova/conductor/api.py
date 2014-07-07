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

conductor_opts = [
    cfg.BoolOpt('use_local',
                default=False,
                help='Perform nova-conductor operations locally'),
    cfg.StrOpt('topic',
               default='conductor',
               help='the topic conductor nodes listen on'),
    cfg.StrOpt('manager',
               default='nova.conductor.manager.ConductorManager',
               help='full class name for the Manager for conductor'),
    cfg.IntOpt('workers',
               help='Number of workers for OpenStack Conductor service'),
    cfg.StrOpt('conductor_plugin_class_name',
               default = 'nova.conductor.plugin',
               help='this flag will use at conductor.api, conductor.rpcapi, conductor.manager')
]
conductor_group = cfg.OptGroup(name='conductor',
                               title='Conductor Options')
CONF = cfg.CONF
CONF.register_group(conductor_group)
CONF.register_opts(conductor_opts, conductor_group)

from nova.conductor import manager
from nova.conductor import rpcapi

LOG = logging.getLogger(__name__)



class LocalAPI(object):
    """A local version of the conductor API that does database updates
    locally instead of via RPC.
    """

    def __init__(self, plugin_class_name = None):
        # TODO(danms): This needs to be something more generic for
        # other/future users of this sort of functionality.
        self._manager = utils.ExceptionHelper(manager.ConductorManager())

        if plugin_class_name is None:
            plugin_class_name = '%s.PluginAPI' % CONF.conductor.conductor_plugin_class_name
        plugin_class = importutils.import_class(plugin_class_name)
        self.plugin = plugin_class(manager = self._manager)
        LOG.debug(_('Load Plugin at Conductor LocalAPI %(plugin_class_name)s'),
                         {'plugin_class_name': plugin_class_name})

    def __getattr__(self, key):
        plugin = self.__dict__.get('plugin', None)
        return getattr(plugin, key)

    def wait_until_ready(self, context, *args, **kwargs):
        # nothing to wait for in the local case.
        pass

    def service_get_all(self, context):
        return self._manager.service_get_all_by(context)

    def service_get_all_by_topic(self, context, topic):
        return self._manager.service_get_all_by(context, topic=topic)

    def service_get_by_id(self, context, service_id):
        return self._manager.service_get_by_id(context, service_id=service_id)

    def service_get_all_by_host(self, context, host):
        return self._manager.service_get_all_by(context, host=host)

    def service_get_by_host_and_topic(self, context, host, topic):
        return self._manager.service_get_all_by(context, topic, host)

    def service_get_by_compute_host(self, context, host):
        result = self._manager.service_get_all_by(context, 'compute', host)
        # FIXME(comstud): A major revision bump to 2.0 should return a
        # single entry, so we should just return 'result' at that point.
        return result[0]

    def service_get_by_args(self, context, host, binary):
        return self._manager.service_get_all_by(context, host=host,
                                                binary=binary)

    def action_event_start(self, context, values):
        return self._manager.action_event_start(context, values)

    def action_event_finish(self, context, values):
        return self._manager.action_event_finish(context, values)

    def service_create(self, context, values):
        return self._manager.service_create(context, values)

    def service_destroy(self, context, service_id):
        return self._manager.service_destroy(context, service_id)

    def service_update(self, context, service, values):
        return self._manager.service_update(context, service, values)


class API(LocalAPI):
    """Conductor API that does updates via RPC to the ConductorManager."""

    def __init__(self,plugin_class_name = None):
        self._manager = rpcapi.ConductorAPI()
        self.base_rpcapi = baserpc.BaseAPI(topic=CONF.conductor.topic)


        if plugin_class_name is None:
            plugin_class_name = '%s.PluginAPI' % CONF.conductor.conductor_plugin_class_name
        plugin_class = importutils.import_class(plugin_class_name)
        self.plugin = plugin_class(manager = self._manager)
        LOG.debug(_('Load Plugin at Conductor API %(plugin_class_name)s'),
                         {'plugin_class_name': plugin_class_name})


    def wait_until_ready(self, context, early_timeout=10, early_attempts=10):
        '''Wait until a conductor service is up and running.

        This method calls the remote ping() method on the conductor topic until
        it gets a response.  It starts with a shorter timeout in the loop
        (early_timeout) up to early_attempts number of tries.  It then drops
        back to the globally configured timeout for rpc calls for each retry.
        '''
        attempt = 0
        timeout = early_timeout
        while True:
            # NOTE(danms): Try ten times with a short timeout, and then punt
            # to the configured RPC timeout after that
            if attempt == early_attempts:
                timeout = None
            attempt += 1

            # NOTE(russellb): This is running during service startup. If we
            # allow an exception to be raised, the service will shut down.
            # This may fail the first time around if nova-conductor wasn't
            # running when this service started.
            try:
                self.base_rpcapi.ping(context, '1.21 GigaWatts',
                                      timeout=timeout)
                break
            except rpc_common.Timeout:
                LOG.warning(_('Timed out waiting for nova-conductor. '
                                'Is it running? Or did this service start '
                                'before nova-conductor?'))