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

"""Handles all requests to the android service."""

import functools


from oslo.config import cfg

from nova import baserpc
from nova import exception


from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import importutils
from nova.openstack.common.rpc import common as rpc_common
from nova.openstack.common import uuidutils

from nova import utils
from nova.android import rb_status
from nova.android import task_status 

android_opts = [
    cfg.StrOpt('topic',
               default='android',
               help='the topic conductor nodes listen on'),
    cfg.StrOpt('manager',
               default='nova.android.manager.AndroidManager',
               help='full class name for the Manager for nova android project'),
    cfg.IntOpt('workers',
               help='Number of workers for OpenStack Conductor service'),
]
android_group = cfg.OptGroup(name='android',
                               title='android Options')
CONF = cfg.CONF
CONF.register_group(android_group)
CONF.register_opts(android_opts, android_group)

from nova.android.agent import manager
from nova.android.agent import rpcapi
from nova import conductor

LOG = logging.getLogger(__name__)


def check_instance_state(android_state=None, task_state=(None,),
                         must_have_launched=False):
    """Decorator to check VM and/or task state before entry to API functions.

    If the instance is in the wrong state, or has not been successfully
    started at least once the wrapper will raise an exception.
    """

    if android_state is not None and not isinstance(android_state, set):
        android_state = set(android_state)
    if task_state is not None and not isinstance(task_state, set):
        task_state = set(task_state)
    def outer(f):
        @functools.wraps(f)
        def inner(self, context, instance, *args, **kw):
            if android_state is not None and instance['android_state'] not in android_state:
                raise exception.InstanceInvalidState(
                    attr='android_state',
                    instance_uuid=instance['uuid'],
                    state=instance['android_state'],
                    method=f.__name__)
            if (task_state is not None and
                    instance['task_state'] not in task_state):
                raise exception.InstanceInvalidState(
                    attr='task_state',
                    instance_uuid=instance['uuid'],
                    state=instance['task_state'],
                    method=f.__name__)
#            if must_have_launched and not instance['launched_at']:
#                raise exception.InstanceInvalidState(
#                    attr='Launched_at',
#                    not_launched=True,
#                    instance_uuid=instance['uuid'],
#                    state=instance['launched_at'],
#                    method=f.__name__)

            return f(self, context, instance, *args, **kw)
        return inner
    return outer

class API(object):
    """A local version of the conductor API that does database updates
    locally instead of via RPC.
    """

    def __init__(self, plugin_class_name = None):
        self._rpcapi = rpcapi.AndroidAPI()
        self.conductor = conductor.API()

    def get(self, context, instance_id):
        """Get a single instance with the given instance_id."""
        # NOTE(ameade): we still need to support integer ids for ec2
        try:
            if uuidutils.is_uuid_like(instance_id):
                instance = self.conductor.android_get_by_uid(context, instance_id)
            elif utils.is_int_like(instance_id):
                ## TODO: not support search by id
                raise exception.AndroidNotFound(uuid=instance_id) 
            else:
                raise exception.AndroidNotFound(uuid=instance_id)
        except exception.AndroidNotFound:
            raise exception.AndroidNotFound(uuid=instance_id)
        return instance

    def create(self, context, name, verdor = ''):
        instances = {}
        instances['name'] = name
        instances['verdor'] = verdor
        instances['android_state'] = rb_status.READY # init variable
        return self._rpcapi.create_android(context,instances)

    @check_instance_state(android_state=[rb_status.READY],
                          task_state=None)
    def active(self, context, instance):
        self._rpcapi.active_android(context, instance)

    @check_instance_state(android_state=[rb_status.ACTIVE,rb_status.WORKING],
                          task_state=None)
    def deactive(self, context, instance):
        self._rpcapi.deactive_android(context, instance)

    @check_instance_state(android_state=[rb_status.ACTIVE],
                          task_state=None)
    def start(self, context, instance):
        self._rpcapi.start_android(context, instance)

    @check_instance_state(android_state=[rb_status.WORKING],
                          task_state=None)
    def stop(self, context, instance):
        self._rpcapi.stop_android(context, instance)

    @check_instance_state(android_state=[None,rb_status.WORKING,rb_status.ACTIVE,rb_status.READY],
                          task_state=[None,task_status.DEACTIVING,task_status.STARTING,
                                      task_status.STOPING])
    def destroy(self, context, instance):
        self._rpcapi.destroy_android(context, instance)