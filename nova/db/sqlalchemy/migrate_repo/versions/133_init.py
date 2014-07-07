# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
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

from migrate.changeset import UniqueConstraint
from migrate import ForeignKeyConstraint
from sqlalchemy import Boolean, BigInteger, Column, DateTime, Float, ForeignKey
from sqlalchemy import Index, Integer, MetaData, String, Table, Text
from sqlalchemy import dialects

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging

LOG = logging.getLogger(__name__)


# Note on the autoincrement flag: this is defaulted for primary key columns
# of integral type, so is no longer set explicitly in such cases.

# NOTE(dprince): This wrapper allows us to easily match the Folsom MySQL
# Schema. In Folsom we created tables as latin1 and converted them to utf8
# later. This conversion causes some of the Text columns on MySQL to get
# created as mediumtext instead of just text.
def MediumText():
    return Text().with_variant(dialects.mysql.MEDIUMTEXT(), 'mysql')


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


    migrations = Table('migrations', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Boolean),
        Column('id', Integer, primary_key=True, nullable=False),
        Column('source_compute', String(length=255)),
        Column('dest_compute', String(length=255)),
        Column('dest_host', String(length=255)),
        Column('status', String(length=255)),
        Column('instance_uuid', String(length=255)),
        Column('old_instance_type_id', Integer),
        Column('new_instance_type_id', Integer),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )


    services = Table('services', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Boolean),
        Column('id', Integer, primary_key=True, nullable=False),
        Column('host', String(length=255)),
        Column('binary', String(length=255)),
        Column('topic', String(length=255)),
        Column('report_count', Integer, nullable=False),
        Column('disabled', Boolean),
        Column('disabled_reason', String(length=255)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    
    # create all tables
    tables = [migrations, services]

    for table in tables:
        try:
            table.create()
        except Exception:
            LOG.info(repr(table))
            LOG.exception(_('Exception while creating table.'))
            raise

    if migrate_engine.name == "mysql":
        # In Folsom we explicitly converted migrate_version to UTF8.
        sql = "ALTER TABLE migrate_version CONVERT TO CHARACTER SET utf8;"
        # Set default DB charset to UTF8.
        sql += "ALTER DATABASE %s DEFAULT CHARACTER SET utf8;" % \
                migrate_engine.url.database
        migrate_engine.execute(sql)


    if migrate_engine.name == "postgresql":
        # TODO(dprince): Drop this in Grizzly. Snapshots were converted
        # to UUIDs in Folsom so we no longer require this autocreated
        # sequence.
        sql = """CREATE SEQUENCE snapshots_id_seq START WITH 1 INCREMENT BY 1
              NO MINVALUE NO MAXVALUE CACHE 1;
              ALTER SEQUENCE snapshots_id_seq OWNED BY snapshots.id;
              SELECT pg_catalog.setval('snapshots_id_seq', 1, false);
              ALTER TABLE ONLY snapshots ALTER COLUMN id SET DEFAULT
              nextval('snapshots_id_seq'::regclass);"""

        # TODO(dprince): Drop this in Grizzly. Volumes were converted
        # to UUIDs in Folsom so we no longer require this autocreated
        # sequence.
        sql += """CREATE SEQUENCE volumes_id_seq START WITH 1 INCREMENT BY 1
               NO MINVALUE NO MAXVALUE CACHE 1;
               ALTER SEQUENCE volumes_id_seq OWNED BY volumes.id;
               SELECT pg_catalog.setval('volumes_id_seq', 1, false);
               ALTER TABLE ONLY volumes ALTER COLUMN id SET DEFAULT
               nextval('volumes_id_seq'::regclass);"""

        migrate_engine.execute(sql)




def downgrade(migrate_engine):
    raise NotImplementedError('Downgrade from Folsom is unsupported.')
