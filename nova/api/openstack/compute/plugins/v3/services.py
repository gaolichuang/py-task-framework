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

ALIAS = "os-services"
authorize = extensions.extension_authorizer('compute', 'v3:' + ALIAS)
CONF = cfg.CONF
CONF.import_opt('service_down_time', 'nova.service')

LOG = logging.getLogger(__name__)

class ServicesMiniTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('services')
        elem = xmlutil.SubTemplateElement(root, 'service', selector='services')
        ''' use elem to control which element can show'''
        elem.set('binary')
        elem.set('topic')
        elem.set('host')
        elem.set('disabled')
        return xmlutil.MasterTemplate(root, 1)

class ServicesDetailTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('services')
        elem = xmlutil.SubTemplateElement(root, 'service', selector='services')
        ''' use elem to control which element can show'''
        elem.set('id')
        elem.set('binary')
#        elem.set('deleted')
#        elem.set('created_at')
        elem.set('updated_at')
#        elem.set('report_count')
        elem.set('topic')
        elem.set('host')
        elem.set('disabled')
#        elem.set('deleted_at')
        elem.set('disabled_reason')
        return xmlutil.MasterTemplate(root, 1)

class ServiceShowTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('service', selector='service')
        root.set('id')
        root.set('binary')
        root.set('deleted')
        root.set('created_at')
        root.set('updated_at')
        root.set('report_count')
        root.set('topic')
        root.set('host')
        root.set('disabled')
        root.set('deleted_at')
        root.set('disabled_reason')
        return xmlutil.MasterTemplate(root, 1)

class ServiceUpdateTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('service', selector='service')
        root.set('host')
        root.set('binary')
        root.set('status')
        root.set('disabled_reason')

        return xmlutil.MasterTemplate(root, 1)

class ServiceExtendController(wsgi.Controller):
    @wsgi.serializers(xml=ServiceShowTemplate)
    @wsgi.response(201)
    #@wsgi.extends(action='custom')
    @wsgi.action('custom')
    def custom(self, req, id, body):
        LOG.debug(_("custom id %s and body %s "% (id,body)))
        return {'service':'not implement  custom...id %s body %s'%(id, body)}


class ServiceController(object):

    def __init__(self):
        self.conductor_api = conductor.API()

    def _is_valid_as_reason(self, reason):
        try:
            utils.check_string_length(reason.strip(), 'Disabled reason',
                                      min_length=1, max_length=255)
        except exception.InvalidInput:
            return False

        return True

    def _get_services(self, req):
        context = req.environ['nova.context']
        services = self.conductor_api.service_get_all(context)
        services = jsonutils.to_primitive(services)
        
        host = ''
        if 'host' in req.GET:
            host = req.GET['host']
        binary = ''
        if 'binary' in req.GET:
            binary = req.GET['binary']
        if host:
            services = [s for s in services if s['host'] == host]
        if binary:
            services = [s for s in services if s['binary'] == binary]
        return services

    def _get_services_by_id(self, req, id):
        context = req.environ['nova.context']
        services = self.conductor_api.service_get_by_id(context, id)
        services = jsonutils.to_primitive(services)
        return services

    def _update_service(self,context, host, binary, status_detail):
        service = self.conductor_api.service_get_by_args(context, host, binary)
        service.update(status_detail)
        service.save()


    @extensions.expected_errors(())
    @wsgi.serializers(xml=ServicesMiniTemplate)
    def index(self, req):
        """
        Return a list of all running services. Filter by host & service name.
        """
        services = self._get_services(req)
        return {'services': services}

    @extensions.expected_errors(())
    @wsgi.serializers(xml=ServicesDetailTemplate)
    def detail(self, req):
        """
        Return a list of all running services. Filter by host & service name.
        """
        services = self._get_services(req)
        return {'services': services}

    @extensions.expected_errors(404)
    @wsgi.serializers(xml=ServiceShowTemplate)
    def show(self, req, id):
        '''get services by id, which id you can get by detail'''
        try:
            service = self._get_services_by_id(req,id)
            return {'service':service}
        except exception.ServiceNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())


    @extensions.expected_errors((400, 404))
    @wsgi.serializers(xml=ServiceUpdateTemplate)
    def update(self, req, id, body):
        """Enable/Disable scheduling for a service."""
        context = req.environ['nova.context']
        #authorize(context)

        if id == "enable":
            disabled = False
            status = "enabled"
        elif id in ("disable", "disable-log-reason"):
            disabled = True
            status = "disabled"
        else:
            raise webob.exc.HTTPNotFound("Unknown action")
        try:
            # host and binary can target only one service
            host = body['service']['host']
            binary = body['service']['binary']
            ret_value = {
                'service': {
                    'host': host,
                    'binary': binary,
                    'status': status,
                },
            }
            status_detail = {
                'disabled': disabled,
                'disabled_reason': None,
            }
            if id == "disable-log-reason":
                reason = body['service']['disabled_reason']
                if not self._is_valid_as_reason(reason):
                    msg = _('Disabled reason contains invalid characters '
                            'or is too long')
                    raise webob.exc.HTTPBadRequest(detail=msg)

                status_detail['disabled_reason'] = reason
                ret_value['service']['disabled_reason'] = reason
        except (TypeError, KeyError):
            msg = _('Invalid attribute in the request')
            if 'host' in body and 'binary' in body:
                msg = _('Missing disabled reason field')
            raise webob.exc.HTTPBadRequest(detail=msg)

        try:
            self._update_service(context, host, binary, status_detail)
        except exception.ServiceNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())

        return ret_value

    @wsgi.serializers(xml=ServiceShowTemplate)
    @wsgi.response(201)
    def create(self, req, body):
        LOG.debug(_("Service create fuction body %s"%body))
        return {'service':'not implement  create... body %s'%body}


    @wsgi.serializers(xml=ServiceShowTemplate)
    @extensions.expected_errors(404)
    @wsgi.response(204)
    def delete(self, req, id, body = None):
        LOG.debug(_("Service delete fuction id %s and body %s"%(id,body)))
        try:
            return {'service':'not implement  delete... id %s and body %s'%(id,body)}
        except exception.ServiceNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())

    @wsgi.serializers(xml=ServiceShowTemplate)
    @wsgi.response(201)
    def add(self, req, body):
        LOG.debug(_("add function  body %s "%(body)))
        return {'service':'not implement  add... body %s'%body}


#    @wsgi.serializers(xml=ServiceShowTemplate)
#    @wsgi.response(201)
#    def action(self, req, id, body):
#        LOG.debug(_("add function id %s body %s "%(id,body)))
#        return {'service':'not implement  action...id %s body %s'%(id, body)}




class Services(extensions.V3APIExtensionBase):
    """Services support."""

    name = "Services"
    alias = ALIAS
    namespace = "http://docs.openstack.org/compute/ext/services/api/v3"
    version = 1

    def get_resources(self):
        collection_actions = {'detail': 'GET','add':'POST'}
        member_actions = {'action':'POST'}
        resources = [extensions.ResourceExtension(ALIAS,
                                               ServiceController(),
                                               collection_actions=collection_actions,
                                               member_actions = member_actions)]
        return resources

    def get_controller_extensions(self):
        controller = ServiceExtendController()
        extension = extensions.ControllerExtension(self, ALIAS, controller)
        return [extension]