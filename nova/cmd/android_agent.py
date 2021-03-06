# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""Starter script for Nova Conductor."""

import sys

from oslo.config import cfg

from nova import config
from nova import objects
from nova.openstack.common import log as logging
from nova import service
from nova import utils

CONF = cfg.CONF
CONF.import_opt('topic', 'nova.android.agent.api', group='android')


def main():
    objects.register_all()
    config.parse_args(sys.argv)
    logging.setup("nova")
    utils.monkey_patch()
    server = service.Service.create(binary='nova-android',
                                    topic=CONF.android.topic,
                                    manager='nova.android.agent.manager.AndroidManager')
    service.serve(server, workers=CONF.conductor.workers)
    service.wait()
