# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 IBM Corp.
# Copyright 2010 OpenStack Foundation
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

from oslo.config import cfg
import webob.dec
import webob.exc

from nova.api.openstack import wsgi
from nova import context
from nova import wsgi as base_wsgi

CONF = cfg.CONF
CONF.import_opt('use_forwarded_for', 'nova.api.auth')


class NoAuthMiddlewareBase(base_wsgi.Middleware):
    """Return a fake token if one isn't specified."""

    def base_call(self, req):
        user_id = req.headers.get('X-Auth-User', 'admin')
        project_id = req.headers.get('X-Auth-Project-Id', 'admin')
        remote_address = getattr(req, 'remote_address', '127.0.0.1')
        if CONF.use_forwarded_for:
            remote_address = req.headers.get('X-Forwarded-For', remote_address)
        ctx = context.RequestContext(user_id,
                                     project_id,
                                     is_admin=True,
                                     remote_address=remote_address)

        req.environ['nova.context'] = ctx
        return self.application


class NoAuthMiddleware(NoAuthMiddlewareBase):
    """Return a fake token if one isn't specified."""

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        return self.base_call(req)
