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


{
    'name': 'Xivo Provisioning',
    'version': '0.1',
    'category': 'Phone',
    'license': 'AGPL-3',
    'summary': 'Create Xivo users from Odoo users',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com/',
    'depends': ['asterisk_click2dial'],
    'external_dependencies': {'python': ['requests', 'json']},
    'data': [
        'wizard/xivo_create_user_view.xml',
        'asterisk_server_view.xml',
        'res_users_view.xml',
        ],
    'demo': [],
    'installable': True,
}
