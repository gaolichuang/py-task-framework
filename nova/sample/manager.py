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
from nova.openstack.common import timeutils
from nova.openstack.common import log as logging
from nova.openstack.common.rpc import common as rpc_common
from nova.openstack.common import periodic_task
from nova.openstack.common import importutils
from nova import conductor
CONF = cfg.CONF


LOG = logging.getLogger(__name__)



class SampleManager(manager.Manager):
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
        super(SampleManager, self).__init__(service_name='sample',
                                               *args, **kwargs)
        self.conductor = conductor.API()



    # spacing is run interval between DynamicLoopingCall
    # enable is a on-off for one dynamic periodic task
    @periodic_task.periodic_task(spacing=25,                                                         
                                 external_process_ok=True,
                                 run_immediately=True,
                                 enabled=True)
    def _sample_periodic_test(self, context):
        LOG.debug(_('Periodic task in sample manager %(c-msg)s'),
                         {'c-msg': 'XXXXXXXXXXXX'})
        values = {'display_name':'name-2',
                  'verdor':'company-1',
                  'launched_at':timeutils.utcnow()}
        #self.conductor.android_create(context, values)
        print self.conductor.android_get_all(context,True)
        #print self.conductor.android_update(context,'XXX',values)
        #print self.conductor.android_update(context,'02cb1e22-7668-4a6b-8eb9-cb204b685c56',values)
        #self.conductor.android_destroy(context,'02cb1e22-7668-4a6b-8eb9-cb204b685c56')
        