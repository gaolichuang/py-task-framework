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

from eventlet import greenthread


from oslo.config import cfg

from nova import exception
from nova import manager
from nova.openstack.common.gettextutils import _
from nova.openstack.common import jsonutils
from nova.openstack.common import timeutils
from nova.openstack.common import log as logging
from nova.openstack.common.rpc import common as rpc_common
from nova.openstack.common import periodic_task
from nova.openstack.common import importutils
from nova import conductor
from nova.android import rb_status
from nova.android import task_status

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class AndroidManager(manager.Manager):
    """Mission: Conduct things.

    The methods in the base API for nova-conductor are various proxy operations
    performed on behalf of the nova-compute service running on compute nodes.
    Compute nodes are not allowed to directly access the database, so this set
    of methods allows them to get specific work done without locally accessing
    the database.

    The nova-conductor service also exposes an API in the 'compute_task'
    namespace.  See the ComputeTaskManager class for details.
    """

    RPC_API_VERSION = '1.0'

    def __init__(self, *args, **kwargs):
        super(AndroidManager, self).__init__(service_name='android',
                                               *args, **kwargs)
        self.conductor = conductor.API()

    def create_android(self, context, instance):
        instance['host'] = self.host
        android = self.conductor.android_create(context, instance)
        LOG.debug(_('android have been created %(instance)s'),
                         {'instance': instance})
        return android

    def destroy_android(self, context, instance):
        self.conductor.android_destroy(context, instance['uuid'])
        LOG.debug(_('android have been destory %(instance)s'),
                         {'instance': instance})

    def _android_status_update(self, context, instance,
                               android_status = None, _task_status = None):
        if android_status != None:
            instance['android_state'] = android_status
        instance['task_status'] = _task_status
        self.conductor.android_update(context, instance['uuid'], instance)

    def active_android(self, context, instance):
        self._android_status_update(context, instance, None, task_status.ACTIVING)
        LOG.debug(_('android is activing %(instance)s'),
                         {'instance': instance})
        greenthread.sleep(10)
        self._android_status_update(context, instance, rb_status.ACTIVE, None)
        LOG.debug(_('android already actived %(instance)s'),
                         {'instance': instance})

    def deactive_android(self, context, instance):
        self._android_status_update(context, instance, None, task_status.DEACTIVING)
        LOG.debug(_('android is DEACTIVING %(instance)s'),
                         {'instance': instance})
        greenthread.sleep(20)
        self._android_status_update(context, instance, rb_status.READY, None)
        LOG.debug(_('android already deactived %(instance)s'),
                         {'instance': instance})

    def start_android(self, context, instance):
        self._android_status_update(context, instance, None, task_status.STARTING)
        LOG.debug(_('android is worked %(instance)s'),
                         {'instance': instance})
        greenthread.sleep(20)
        self._android_status_update(context, instance, rb_status.WORKING, None)
        LOG.debug(_('android already working %(instance)s'),
                         {'instance': instance})

    def stop_android(self, context, instance):
        self._android_status_update(context, instance, None, task_status.STOPING)
        LOG.debug(_('android is worked %(instance)s'),
                         {'instance': instance})
        greenthread.sleep(20)
        self._android_status_update(context, instance, rb_status.ACTIVE, None)
        LOG.debug(_('android already working %(instance)s'),
                         {'instance': instance})