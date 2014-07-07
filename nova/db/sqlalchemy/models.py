# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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
"""
SQLAlchemy models for nova data.
"""

from sqlalchemy import Column, Index, Integer, BigInteger, Enum, String, schema
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey, DateTime, Boolean, Text, Float
from sqlalchemy.orm import relationship, backref, object_mapper
from oslo.config import cfg

from nova.openstack.common.db.sqlalchemy import models
from nova.openstack.common import timeutils

CONF = cfg.CONF
BASE = declarative_base()


def MediumText():
    return Text().with_variant(MEDIUMTEXT(), 'mysql')


class NovaBase(models.SoftDeleteMixin,
               models.TimestampMixin,
               models.ModelBase):
    metadata = None


class Service(BASE, NovaBase):
    """Represents a running service on a host."""

    __tablename__ = 'services'
    __table_args__ = (
        schema.UniqueConstraint("host", "topic", "deleted",
                                name="uniq_services0host0topic0deleted"),
        schema.UniqueConstraint("host", "binary", "deleted",
                                name="uniq_services0host0binary0deleted")
        )

    id = Column(Integer, primary_key=True)
    host = Column(String(255))  # , ForeignKey('hosts.id'))
    binary = Column(String(255))
    topic = Column(String(255))
    report_count = Column(Integer, nullable=False, default=0)
    disabled = Column(Boolean, default=False)
    disabled_reason = Column(String(255))


#########################
# for android project
#########################
class Instance(BASE, NovaBase):
    '''represents one android'''
    __tablename__ = 'instances'
    __table_args__ = (
        Index('uuid', 'uuid', unique=True),
        Index('project_id', 'project_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # user id and project id come from context
    user_id = Column(String(255))
    project_id = Column(String(255))

    android_state = Column(String(255))
    task_state = Column(String(255))

    # time when created
    launched_at = Column(DateTime)
    # time when destroy
    terminated_at = Column(DateTime)
    display_name = Column(String(255))
    uuid = Column(String(36))

    progress = Column(Integer)

    #some android own info
    verdor = Column(String(64))
