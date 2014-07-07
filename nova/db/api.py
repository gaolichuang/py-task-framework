# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
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

"""Defines interface for DB access.

The underlying driver is loaded as a :class:`LazyPluggable`.

Functions in this module are imported into the nova.db namespace. Call these
functions from nova.db namespace, not the nova.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface. Currently, many of these objects are sqlalchemy objects that
implement a dictionary interface. However, a future goal is to have all of
these objects be simple dictionaries.


**Related Flags**

:db_backend:  string to lookup in the list of LazyPluggable backends.
              `sqlalchemy` is the only supported backend right now.

:connection:  string specifying the sqlalchemy connection to use, like:
              `sqlite:///var/lib/nova/nova.sqlite`.

:enable_new_services:  when adding a new service to the database, is it in the
                       pool of available hardware (Default: True)

"""

from oslo.config import cfg

from nova import exception
from nova.openstack.common.db import api as db_api
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging

db_opts = [
    cfg.BoolOpt('enable_new_services',
                default=True,
                help='Services to be added to the available pool on create'),
    ]

CONF = cfg.CONF
CONF.register_opts(db_opts)

_BACKEND_MAPPING = {'sqlalchemy': 'nova.db.sqlalchemy.api'}


IMPL = db_api.DBAPI(backend_mapping=_BACKEND_MAPPING)
LOG = logging.getLogger(__name__)


class NoMoreNetworks(exception.NovaException):
    """No more available networks."""
    pass


class NoMoreTargets(exception.NovaException):
    """No more available targets."""
    pass


###################


def constraint(**conditions):
    """Return a constraint object suitable for use with some updates."""
    return IMPL.constraint(**conditions)


def equal_any(*values):
    """Return an equality condition object suitable for use in a constraint.

    Equal_any conditions require that a model object's attribute equal any
    one of the given values.
    """
    return IMPL.equal_any(*values)


def not_equal(*values):
    """Return an inequality condition object suitable for use in a constraint.

    Not_equal conditions require that a model object's attribute differs from
    all of the given values.
    """
    return IMPL.not_equal(*values)


###################


def service_destroy(context, service_id):
    """Destroy the service or raise if it does not exist."""
    return IMPL.service_destroy(context, service_id)


def service_get(context, service_id):
    """Get a service or raise if it does not exist."""
    return IMPL.service_get(context, service_id)


def service_get_by_host_and_topic(context, host, topic):
    """Get a service by host it's on and topic it listens to."""
    return IMPL.service_get_by_host_and_topic(context, host, topic)


def service_get_all(context, disabled=None):
    """Get all services."""
    return IMPL.service_get_all(context, disabled)


def service_get_all_by_topic(context, topic):
    """Get all services for a given topic."""
    return IMPL.service_get_all_by_topic(context, topic)


def service_get_all_by_host(context, host):
    """Get all services for a given host."""
    return IMPL.service_get_all_by_host(context, host)


def service_get_by_compute_host(context, host):
    """Get the service entry for a given compute host.

    Returns the service entry joined with the compute_node entry.
    """
    return IMPL.service_get_by_compute_host(context, host)


def service_get_by_args(context, host, binary):
    """Get the state of a service by node name and binary."""
    return IMPL.service_get_by_args(context, host, binary)


def service_create(context, values):
    """Create a service from the values dictionary."""
    return IMPL.service_create(context, values)


def service_update(context, service_id, values):
    """Set the given properties on a service and update it.

    Raises NotFound if service does not exist.

    """
    return IMPL.service_update(context, service_id, values)


###################

def android_get_all(context, include_delete=False):
    """Get all services."""
    if include_delete:
        read_deleted = 'yes'
    else:
        read_deleted = 'no'
    return IMPL.android_get_all(context, read_deleted)

def android_get_by_name(context, name):
    '''get one android by name'''
    return IMPL.android_get_by_name(context, name)
def android_get_by_uid(context, uuid):
    '''get one android by name'''
    return IMPL.android_get_by_uid(context, uuid)

def android_create(context, values):
    """Create a service from the values dictionary."""
    return IMPL.android_create(context, values)


def android_update(context, uuid, values):
    """Set the given properties on a service and update it.

    Raises NotFound if uid does not exist.

    """
    return IMPL.android_update(context, uuid, values)

def android_destroy(context, uuid):
    """Destroy the android or raise if it does not exist."""
    return IMPL.android_destroy(context, uuid)
