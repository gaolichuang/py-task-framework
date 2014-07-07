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

"""Implementation of SQLAlchemy backend."""

import collections
import copy
import datetime
import functools
import itertools
import sys
import time
import uuid

from oslo.config import cfg
from sqlalchemy import and_
from sqlalchemy import Boolean
from sqlalchemy.exc import DataError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import or_
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import joinedload_all
from sqlalchemy.orm import noload
from sqlalchemy.schema import Table
from sqlalchemy.sql.expression import asc
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql.expression import select
from sqlalchemy.sql import func
from sqlalchemy import String

import nova.context
from nova.db.sqlalchemy import models
from nova import exception
from nova.openstack.common.db import exception as db_exc
from nova.openstack.common.db.sqlalchemy import session as db_session
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils


CONF = cfg.CONF
CONF.import_opt('connection',
                'nova.openstack.common.db.sqlalchemy.session',
                group='database')

LOG = logging.getLogger(__name__)

get_engine = db_session.get_engine
get_session = db_session.get_session




def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def require_admin_context(f):
    """Decorator to require admin request context.

    The first argument to the wrapped function must be the context.

    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        nova.context.require_admin_context(args[0])
        return f(*args, **kwargs)
    return wrapper


def require_context(f):
    """Decorator to require *any* user or admin context.

    This does no authorization for user or project access matching, see
    :py:func:`nova.context.authorize_project_context` and
    :py:func:`nova.context.authorize_user_context`.

    The first argument to the wrapped function must be the context.

    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        nova.context.require_context(args[0])
        return f(*args, **kwargs)
    return wrapper


def require_instance_exists_using_uuid(f):
    """Decorator to require the specified instance to exist.

    Requires the wrapped function to use context and instance_uuid as
    their first two arguments.
    """
    @functools.wraps(f)
    def wrapper(context, instance_uuid, *args, **kwargs):
        instance_get_by_uuid(context, instance_uuid)
        return f(context, instance_uuid, *args, **kwargs)

    return wrapper


def require_aggregate_exists(f):
    """Decorator to require the specified aggregate to exist.

    Requires the wrapped function to use context and aggregate_id as
    their first two arguments.
    """

    @functools.wraps(f)
    def wrapper(context, aggregate_id, *args, **kwargs):
        aggregate_get(context, aggregate_id)
        return f(context, aggregate_id, *args, **kwargs)
    return wrapper


def _retry_on_deadlock(f):
    """Decorator to retry a DB API call if Deadlock was received."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        while True:
            try:
                return f(*args, **kwargs)
            except db_exc.DBDeadlock:
                LOG.warn(_("Deadlock detected when running "
                           "'%(func_name)s': Retrying..."),
                           dict(func_name=f.__name__))
                # Retry!
                time.sleep(0.5)
                continue
    functools.update_wrapper(wrapped, f)
    return wrapped


def model_query(context, model, *args, **kwargs):
    """Query helper that accounts for context's `read_deleted` field.

    :param context: context to query under
    :param session: if present, the session to use
    :param read_deleted: if present, overrides context's read_deleted field.
    :param project_only: if present and context is user-type, then restrict
            query to match the context's project_id. If set to 'allow_none',
            restriction includes project_id = None.
    :param base_model: Where model_query is passed a "model" parameter which is
            not a subclass of NovaBase, we should pass an extra base_model
            parameter that is a subclass of NovaBase and corresponds to the
            model parameter.
    """
    session = kwargs.get('session') or get_session()
    read_deleted = kwargs.get('read_deleted') or context.read_deleted
    project_only = kwargs.get('project_only', False)

    def issubclassof_nova_base(obj):
        return isinstance(obj, type) and issubclass(obj, models.NovaBase)

    base_model = model
    if not issubclassof_nova_base(base_model):
        base_model = kwargs.get('base_model', None)
        if not issubclassof_nova_base(base_model):
            raise Exception(_("model or base_model parameter should be "
                              "subclass of NovaBase"))

    query = session.query(model, *args)

    default_deleted_value = base_model.__mapper__.c.deleted.default.arg
    if read_deleted == 'no':
        query = query.filter(base_model.deleted == default_deleted_value)
    elif read_deleted == 'yes':
        pass  # omit the filter to include deleted and active
    elif read_deleted == 'only':
        query = query.filter(base_model.deleted != default_deleted_value)
    else:
        raise Exception(_("Unrecognized read_deleted value '%s'")
                            % read_deleted)

    if nova.context.is_user_context(context) and project_only:
        if project_only == 'allow_none':
            query = query.\
                filter(or_(base_model.project_id == context.project_id,
                           base_model.project_id == None))
        else:
            query = query.filter_by(project_id=context.project_id)

    return query


def exact_filter(query, model, filters, legal_keys):
    """Applies exact match filtering to a query.

    Returns the updated query.  Modifies filters argument to remove
    filters consumed.

    :param query: query to apply filters to
    :param model: model object the query applies to, for IN-style
                  filtering
    :param filters: dictionary of filters; values that are lists,
                    tuples, sets, or frozensets cause an 'IN' test to
                    be performed, while exact matching ('==' operator)
                    is used for other values
    :param legal_keys: list of keys to apply exact filtering to
    """

    filter_dict = {}

    # Walk through all the keys
    for key in legal_keys:
        # Skip ones we're not filtering on
        if key not in filters:
            continue

        # OK, filtering on this key; what value do we search for?
        value = filters.pop(key)

        if key == 'metadata' or key == 'system_metadata':
            column_attr = getattr(model, key)
            if isinstance(value, list):
                for item in value:
                    for k, v in item.iteritems():
                        query = query.filter(column_attr.any(key=k))
                        query = query.filter(column_attr.any(value=v))

            else:
                for k, v in value.iteritems():
                    query = query.filter(column_attr.any(key=k))
                    query = query.filter(column_attr.any(value=v))
        elif isinstance(value, (list, tuple, set, frozenset)):
            # Looking for values in a list; apply to query directly
            column_attr = getattr(model, key)
            query = query.filter(column_attr.in_(value))
        else:
            # OK, simple exact match; save for later
            filter_dict[key] = value

    # Apply simple exact matches
    if filter_dict:
        query = query.filter_by(**filter_dict)

    return query


def convert_datetimes(values, *datetime_keys):
    for key in values:
        if key in datetime_keys and isinstance(values[key], basestring):
            values[key] = timeutils.parse_strtime(values[key])
    return values


def _sync_instances(context, project_id, user_id, session):
    return dict(zip(('instances', 'cores', 'ram'),
                    _instance_data_get_for_user(
                context, project_id, user_id, session)))


def _sync_floating_ips(context, project_id, user_id, session):
    return dict(floating_ips=_floating_ip_count_by_project(
                context, project_id, session))


def _sync_fixed_ips(context, project_id, user_id, session):
    return dict(fixed_ips=_fixed_ip_count_by_project(
                context, project_id, session))


def _sync_security_groups(context, project_id, user_id, session):
    return dict(security_groups=_security_group_count_by_project_and_user(
                context, project_id, user_id, session))

QUOTA_SYNC_FUNCTIONS = {
    '_sync_instances': _sync_instances,
    '_sync_floating_ips': _sync_floating_ips,
    '_sync_fixed_ips': _sync_fixed_ips,
    '_sync_security_groups': _sync_security_groups,
}

###################


def constraint(**conditions):
    return Constraint(conditions)


def equal_any(*values):
    return EqualityCondition(values)


def not_equal(*values):
    return InequalityCondition(values)


class Constraint(object):

    def __init__(self, conditions):
        self.conditions = conditions

    def apply(self, model, query):
        for key, condition in self.conditions.iteritems():
            for clause in condition.clauses(getattr(model, key)):
                query = query.filter(clause)
        return query


class EqualityCondition(object):

    def __init__(self, values):
        self.values = values

    def clauses(self, field):
        return or_([field == value for value in self.values])


class InequalityCondition(object):

    def __init__(self, values):
        self.values = values

    def clauses(self, field):
        return [field != value for value in self.values]


###################


@require_admin_context
def service_destroy(context, service_id):
    session = get_session()
    with session.begin():
        count = model_query(context, models.Service, session=session).\
                    filter_by(id=service_id).\
                    soft_delete(synchronize_session=False)

        if count == 0:
            raise exception.ServiceNotFound(service_id=service_id)



def _service_get(context, service_id, session=None):
    query = model_query(context, models.Service, session=session).\
                     filter_by(id=service_id)



    result = query.first()
    if not result:
        raise exception.ServiceNotFound(service_id=service_id)

    return result


@require_admin_context
def service_get(context, service_id):
    return _service_get(context, service_id)


@require_admin_context
def service_get_all(context, disabled=None):
    query = model_query(context, models.Service)

    if disabled is not None:
        query = query.filter_by(disabled=disabled)

    return query.all()


@require_admin_context
def service_get_all_by_topic(context, topic):
    return model_query(context, models.Service, read_deleted="no").\
                filter_by(disabled=False).\
                filter_by(topic=topic).\
                all()


@require_admin_context
def service_get_by_host_and_topic(context, host, topic):
    return model_query(context, models.Service, read_deleted="no").\
                filter_by(disabled=False).\
                filter_by(host=host).\
                filter_by(topic=topic).\
                first()


@require_admin_context
def service_get_all_by_host(context, host):
    return model_query(context, models.Service, read_deleted="no").\
                filter_by(host=host).\
                all()


@require_admin_context
def service_get_by_compute_host(context, host):
    result = model_query(context, models.Service, read_deleted="no").\
                options(joinedload('compute_node')).\
                filter_by(host=host).\
                filter_by(topic=CONF.compute_topic).\
                first()

    if not result:
        raise exception.ComputeHostNotFound(host=host)

    return result


@require_admin_context
def service_get_by_args(context, host, binary):
    result = model_query(context, models.Service).\
                     filter_by(host=host).\
                     filter_by(binary=binary).\
                     first()

    if not result:
        raise exception.HostBinaryNotFound(host=host, binary=binary)

    return result


@require_admin_context
def service_create(context, values):
    service_ref = models.Service()
    service_ref.update(values)
    if not CONF.enable_new_services:
        service_ref.disabled = True
    try:
        service_ref.save()
    except db_exc.DBDuplicateEntry as e:
        if 'binary' in e.columns:
            raise exception.ServiceBinaryExists(host=values.get('host'),
                        binary=values.get('binary'))
        raise exception.ServiceTopicExists(host=values.get('host'),
                        topic=values.get('topic'))
    return service_ref


@require_admin_context
def service_update(context, service_id, values):
    session = get_session()
    with session.begin():
        service_ref = _service_get(context, service_id, session=session)
        service_ref.update(values)

    return service_ref


###################
def _android_instance_get(context, uuid, session=None):
    query = model_query(context, models.Instance, session=session).\
                     filter_by(uuid=uuid)
    result = query.first()
    if not result:
        raise exception.AndroidNotFound(uuid=uuid)
    return result

def android_get_all(context, read_deleted="no"):
    query = model_query(context, models.Instance, read_deleted=read_deleted)
    return query.all()

def android_get_by_name(context, name):
    return model_query(context, models.Instance, read_deleted="no").\
                filter_by(display_name=name).\
                all()

def android_get_by_uid(context, uuid):
    return _android_instance_get(context, uuid)

@require_admin_context
def android_create(context, values):
    if not values.get('uuid'):
        values['uuid'] = str(uuid.uuid4())
    if not values.get('project_id'):
        values['project_id'] = context.project_id
    if not values.get('user_id'):
        values['user_id'] = context.user_id

    instance_ref = models.Instance()
    instance_ref.update(values)
    session = get_session()
    with session.begin():
        session.add(instance_ref)
    return instance_ref

@require_admin_context
def android_update(context, uuid, values):
    session = get_session()
    with session.begin():
        instance_ref = _android_instance_get(context, uuid, session=session)
        instance_ref.update(values)
    return instance_ref

@require_admin_context
def android_destroy(context, uuid):
    session = get_session()
    with session.begin():
        count = model_query(context, models.Instance, session=session).\
                    filter_by(uuid=uuid).\
                    soft_delete(synchronize_session=False)

        if count == 0:
            raise exception.AndroidNotFound(uuid=uuid)
##############################################