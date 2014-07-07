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

"""Handles database requests from other nova services."""
from oslo.config import cfg

from nova import exception
from nova import manager
from nova.openstack.common.gettextutils import _
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.openstack.common.rpc import common as rpc_common
from nova.openstack.common import periodic_task
from nova.openstack.common import importutils

CONF = cfg.CONF

CONF.import_opt('conductor_plugin_class_name', 'nova.conductor.api', group='conductor')

LOG = logging.getLogger(__name__)



class ConductorManager(manager.Manager):
    """Mission: Conduct things.

    The methods in the base API for nova-conductor are various proxy operations
    performed on behalf of the nova-compute service running on compute nodes.
    Compute nodes are not allowed to directly access the database, so this set
    of methods allows them to get specific work done without locally accessing
    the database.

    The nova-conductor service also exposes an API in the 'compute_task'
    namespace.  See the ComputeTaskManager class for details.
    """

    RPC_API_VERSION = '1.58'

    def __init__(self, *args, **kwargs):
        super(ConductorManager, self).__init__(service_name='conductor',
                                               *args, **kwargs)

        plugin_class_name = '%s.ConductorManagerPlugin' % CONF.conductor.conductor_plugin_class_name
        plugin_class = importutils.import_class(plugin_class_name)
        self.plugin = plugin_class()
        LOG.debug(_('Load Plugin at ConductorManager %(plugin_class_name)s'),
                         {'plugin_class_name': plugin_class_name})

    def __getattr__(self, key):
        plugin = self.__dict__.get('plugin', None)
        return getattr(plugin, key)


    @rpc_common.client_exceptions(exception.HostBinaryNotFound)
    def service_get_all_by(self, context, topic=None, host=None, binary=None):
        if not any((topic, host, binary)):
            result = self.db.service_get_all(context)
        elif all((topic, host)):
            result = self.db.service_get_by_host_and_topic(context,
                                                               host, topic)
        elif all((host, binary)):
            result = self.db.service_get_by_args(context, host, binary)
        elif topic:
            result = self.db.service_get_all_by_topic(context, topic)
        elif host:
            result = self.db.service_get_all_by_host(context, host)

        return jsonutils.to_primitive(result)

    def service_get_by_id(self, context, service_id):
        svc = self.db.service_get(context, service_id)
        return jsonutils.to_primitive(svc)

    def service_create(self, context, values):
        svc = self.db.service_create(context, values)
        return jsonutils.to_primitive(svc)

    @rpc_common.client_exceptions(exception.ServiceNotFound)
    def service_destroy(self, context, service_id):
        self.db.service_destroy(context, service_id)

    @rpc_common.client_exceptions(exception.ServiceNotFound)
    def service_update(self, context, service, values):
        svc = self.db.service_update(context, service['id'], values)
        return jsonutils.to_primitive(svc)

    # spacing is run interval between DynamicLoopingCall
    # enable is a on-off for one dynamic periodic task
    @periodic_task.periodic_task(spacing=25,                                                         
                                 external_process_ok=True,
                                 run_immediately=True,
                                 enabled=True)
    def _conductor_periodic_test(self, context):
        LOG.debug(_('Periodic task in conductor manager %(c-msg)s'),
                         {'c-msg': 'XXXXXXXXXXXX'})