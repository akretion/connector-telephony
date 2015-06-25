# -*- encoding: utf-8 -*-
##############################################################################
#
#    Xivo Provisioning module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com/)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import requests
import json


class ResUsers(models.Model):
    _inherit = 'res.users'

    xivo_user_identifier = fields.Integer(string='Xivo User ID', copy=False)


class AsteriskServer(models.Model):
    _inherit = 'asterisk.server'

    xivo_default_voicemail_pin = fields.Char(
        string='Default Voicemail PIN', default='1234')
    xivo_default_ring_seconds = fields.Selection([
        ('5', '5 seconds'),
        ('10', '10 seconds'),
        ('15', '15 seconds'),
        ('20', '20 seconds'),
        ('25', '25 seconds'),
        ('30', '30 seconds'),
        ('35', '35 seconds'),
        ('40', '40 seconds'),
        ('45', '45 seconds'),
        ('50', '50 seconds'),
        ('55', '55 seconds'),
        ('60', '60 seconds'),
        ], string='Default Ringing Time (seconds)', default='30')
    xivo_default_simult_calls = fields.Integer(
        string='Default Simultaneous Calls', default=5)
    xivo_default_moh = fields.Char(
        string='Default Music On Hold', default='default')
    xivo_default_xivo_client_password = fields.Char(
        string='Default Xivo Client Password', default='xivo')
    xivo_webservice_login = fields.Char(
        string='Xivo Webservice Login', copy=False)
    xivo_webservice_password = fields.Char(
        string='Xivo Webservice Password', copy=False)

    @api.multi
    def _prepare_xivo_webservices(self, url):
        self.ensure_one()
        if not self.xivo_webservice_login:
            raise Warning(_(
                "Missing Xivo Webservice Login on server %s.") % self.name)
        if not self.xivo_webservice_password:
            raise Warning(_(
                "Missing Xivo Webservice Password on server %s.") % self.name)
        res = {
            'url': 'https://%s%s' % (self.ip_address, url),
            'auth': (self.xivo_webservice_login,
                     self.xivo_webservice_password),
            }
        return res

    @api.multi
    def xivo_get_request(self, url):
        self.ensure_one()
        xivo = self._prepare_xivo_webservices(url)
        res_request = requests.get(
            xivo['url'], auth=xivo['auth'], verify=False)
        if res_request.status_code == 200:
            res = res_request.json()
            if not res:
                raise Warning(_(
                    "The request to %s returned an empty answer") % url)
            return res
        elif res_request.status_code == 204:
            return []
        else:
            raise Warning(_(
                "The request to %s returned HTTP code %d")
                % (url, res_request.status_code))

    @api.multi
    def xivo_post_request(self, url, payload):
        self.ensure_one()
        xivo = self._prepare_xivo_webservices(url)
        res_request = requests.post(
            xivo['url'], auth=xivo['auth'], verify=False,
            data=json.dumps(payload))
        if res_request.status_code != 200:
            raise Warning(_(
                "The request to %s returned HTTP code %d")
                % (url, res_request.status_code))
        return res_request
