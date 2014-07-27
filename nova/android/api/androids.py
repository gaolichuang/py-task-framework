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
from nova.android import agent as android_api
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.api.openstack.wsgi import Controller as wsgi_controller
ALIAS = "androids-plant"
CONF = cfg.CONF

LOG = logging.getLogger(__name__)

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

class AndroidExtendController(wsgi.Controller):
    def __init__(self):
        self._android_api = android_api.API()
        super(AndroidExtendController, self).__init__() 

    @wsgi.serializers(xml=AndroidShowTemplate)
    @wsgi.response(201)
    @wsgi.action('active')
    def active(self, req, id, body):
        context = req.environ['nova.context']
        instance = {}
        instance['uuid'] = id
        self._android_api.active(context, instance)
        return {'service':'not implement  custom...id %s body %s'%(id, body)}

    @wsgi.serializers(xml=AndroidShowTemplate)
    @wsgi.response(201)
    @wsgi.action('deactive')
    def deactive(self, req, id, body):
        context = req.environ['nova.context']
        instance = {}
        instance['uuid'] = id
        self._android_api.deactive(context, instance)
        LOG.debug(_("custom id %s and body %s "% (id,body)))
        return {'service':'not implement  custom...id %s body %s'%(id, body)}

    @wsgi.serializers(xml=AndroidShowTemplate)
    @wsgi.response(201)
    @wsgi.action('start')
    def start(self, req, id, body):
        context = req.environ['nova.context']
        instance = {}
        instance['uuid'] = id
        self._android_api.start(context, instance)
        LOG.debug(_("custom id %s and body %s "% (id,body)))
        return {'service':'not implement  custom...id %s body %s'%(id, body)}

    @wsgi.serializers(xml=AndroidShowTemplate)
    @wsgi.response(201)
    @wsgi.action('stop')
    def stop(self, req, id, body):
        context = req.environ['nova.context']
        instance = {}
        instance['uuid'] = id
        self._android_api.stop(context, instance)
        LOG.debug(_("custom id %s and body %s "% (id,body)))
        return {'service':'not implement  custom...id %s body %s'%(id, body)}

class AndroidController(object):

    def __init__(self):
        self._android_api = android_api.API()

    @wsgi.serializers(xml=AndroidShowTemplate)
    @extensions.expected_errors((400, 409))
    def create(self, req, body):
        LOG.debug(_("Service create fuction body %s"%body))
        if not wsgi_controller.is_valid_body(body, 'android'):
            raise webob.exc.HTTPBadRequest('Invalid request body ')
        vals = body['android']
        name = vals.get('name',None)
        verdor = vals.get('verdor',None)
        if name == None or verdor == None:
            raise webob.exc.HTTPBadRequest('Invalid request body not set name or verdor')
        context = req.environ['nova.context']
        LOG.debug(_("get name and verdor  %s %s" % (name,verdor)))

        service = self._android_api.create(context, name = name, verdor =verdor)
        LOG.debug(_("android create  %s"%service))

        return {'android':service}


    @wsgi.serializers(xml=AndroidShowTemplate)
    @extensions.expected_errors(404)
    @wsgi.response(204)
    def delete(self, req, id, body = None):
        context = req.environ['nova.context']
        try:
            instance = {}
            instance = self._android_api.get(context,id)
            self._android_api.destroy(context,instance)
        except exception.AndroidNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())



class Androids(extensions.V3APIExtensionBase):
    """Android control service."""

    name = "AndroidsPlant"
    alias = ALIAS
    namespace = "http://docs.openstack.org/compute/ext/services/api/v3"
    version = 1

    def get_resources(self):
        member_actions = {'action':'POST'}
        resources = [extensions.ResourceExtension(ALIAS,
                                               AndroidController(),
                                               member_actions = member_actions)]
        return resources

    def get_controller_extensions(self):
        controller = AndroidExtendController()
        extension = extensions.ControllerExtension(self, ALIAS, controller)
        return [extension]