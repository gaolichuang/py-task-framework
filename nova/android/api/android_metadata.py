# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 IBM Corp.
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

from oslo.config import cfg
import webob.exc

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
from nova import exception
from nova.openstack.common.gettextutils import _
from nova import conductor
from nova import utils
from nova import db as db_api
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging

ALIAS = "android-metadata"
CONF = cfg.CONF

LOG = logging.getLogger(__name__)

class AndroidsMiniTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('androids')
        elem = xmlutil.SubTemplateElement(root, 'android', selector='androids')
        ''' use elem to control which element can show'''
        elem.set('display_name')
        elem.set('android_state')
        elem.set('task_state')
        elem.set('verdor')
        return xmlutil.MasterTemplate(root, 1)

class AndroidsDetailTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('androids')
        elem = xmlutil.SubTemplateElement(root, 'android', selector='androids')
        ''' use elem to control which element can show'''
        elem.set('id')
        elem.set('android_state')
        elem.set('task_state')
        elem.set('display_name')
        elem.set('uuid')
        elem.set('verdor')
        return xmlutil.MasterTemplate(root, 1)

class AndroidShowTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('android', selector='android')
        root.set('id')
        root.set('user_id')
        root.set('project_id')
        root.set('android_state')
        root.set('task_state')
        root.set('launched_at')
        root.set('terminated_at')
        root.set('display_name')
        root.set('uuid')
        root.set('progress')
        root.set('verdor')
        root.set('host')
        return xmlutil.MasterTemplate(root, 1)



class AndroidController(object):

    def __init__(self):
        self.conductor_api = conductor.API()


    def _get_androids(self, req):
        context = req.environ['nova.context']
        androids = self.conductor_api.android_get_all(context)
        androids = jsonutils.to_primitive(androids)
        return androids

    def _get_android_by_id(self, req, id):
        context = req.environ['nova.context']
        android = self.conductor_api.android_get_by_uid(context, id)
        android = jsonutils.to_primitive(android)
        return android

    @extensions.expected_errors(())
    @wsgi.serializers(xml=AndroidsMiniTemplate)
    def index(self, req):
        """
        Return a list of all running services. Filter by host & service name.
        """
        services = self._get_androids(req)
        return {'androids': services}

    @extensions.expected_errors(())
    @wsgi.serializers(xml=AndroidsDetailTemplate)
    def detail(self, req):
        """
        Return a list of all running services. Filter by host & service name.
        """
        androids = self._get_androids(req)
        return {'androids': androids}

    @extensions.expected_errors(404)
    @wsgi.serializers(xml=AndroidShowTemplate)
    def show(self, req, id):
        '''get services by id, which id you can get by detail'''
        try:
            android = self._get_android_by_id(req,id)
            return {'android':android}
        except exception.ServiceNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())


class Androids(extensions.V3APIExtensionBase):
    """Services support."""

    name = "Androids"
    alias = ALIAS
    namespace = "http://docs.openstack.org/compute/ext/services/api/v3"
    version = 1

    def get_resources(self):
        collection_actions = {'detail': 'GET'}
        resources = [extensions.ResourceExtension(ALIAS,
                                               AndroidController(),
                                               collection_actions=collection_actions)]
        return resources

    def get_controller_extensions(self):
        return []