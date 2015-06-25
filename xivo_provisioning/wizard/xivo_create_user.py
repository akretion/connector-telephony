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
import logging
from pprint import pprint

logger = logging.getLogger(__name__)


class XivoCreateUser(models.TransientModel):
    _name = 'xivo.create.user'
    _description = 'Wizard to create Xivo users from Odoo'

    def _default_xivo_client_login(self):
        user = self.env['res.users'].browse(self._context['active_id'])
        return user.login.split('@')[0]

    def _default_xivo_client_password(self):
        user = self.env['res.users'].browse(self._context['active_id'])
        server = user.get_asterisk_server_from_user()
        return server.xivo_default_xivo_client_password

    create_voicemail = fields.Boolean(
        string="Create Voicemail", default=True)
    create_agent = fields.Boolean(string="Create Agent", default=True)
    create_incall = fields.Boolean(
        default=True, string='Create Incoming Call')
    grant_xivo_client = fields.Boolean(
        string="Grant Access to Xivo Client", default=True)
    xivo_client_login = fields.Char(
        string="Xivo Client Login",
        default=_default_xivo_client_login)
    xivo_client_password = fields.Char(
        string="Xivo Client Password",
        default=_default_xivo_client_password)

    @api.model
    def extract_xivo_firstname_lastname(self, user):
        name_split = user.name.split(' ')
        if len(name_split) > 1:
            return (name_split[0], ' '.join(name_split[1:]))
        else:
            return (user.name, '')

    @api.model
    def _prepare_agent_payload(self, user, internal_number):
        firstname, lastname = self.extract_xivo_firstname_lastname(user)
        agent_payload = {
            'agentfeatures': {
                'autologoff': '0',
                'context': 'default',
                'firstname': firstname,
                'language': 'fr_FR',
                'lastname': lastname,
                'number': internal_number,
                'numgroup': '1',
            },
            # 'queue-select': [queue_name],
            # 'queue': {queue_name: {}},
        }
        return agent_payload

    @api.model
    def _prepare_callerid(self, user, server, sda):
        if sda:
            number = sda
        else:
            if not user.company_id.phone:
                raise Warning(_(
                    "The user '%s' doesn't have any direct line and the "
                    "company '%s' doesn't have a phone number, so we "
                    "cannot generate the Caller ID")
                    % (user.name, user.company_id.name))
            number = self.env['phone.common'].convert_to_dial_number(
                user.company_id.phone)
        res = '"%s" <%s>' % (user.name, number)
        return res

    @api.model
    def _prepare_user_payload(
            self, server, user, internal_number, new_agent_id, callerid):
        firstname, lastname = self.extract_xivo_firstname_lastname(user)
        res = {
            'dialaction': {
                'busy': {'actiontype': 'none'},
                'busy': {'actiontype': 'none'},
                'congestion': {'actiontype': 'none'},
                'chanunavail': {'actiontype': 'none'},
                },
            'phonefunckey': {
                'fknum': ['1', '2'],
                'type': [
                    'extenfeatures-fwdunc',
                    'extenfeatures-agentstaticlogtoggle'],
                'typeval': ['', unicode(new_agent_id)],
                'label': [u'Renvoi', u'Standard'],
                'supervision': ['1', '1'],
                },
            'linefeatures': {
                'protocol': ['sip'],
                'context': ['default'],
                'number': [internal_number],
                },
            'userfeatures': {
                'agentid': new_agent_id and unicode(new_agent_id) or '',
                'enablehint': True,
                'enablexfer': True,
                'enableautomon': False,
                'entityid': 1,
                'firstname': firstname,
                'language': 'fr_FR',  # TODO
                'lastname': lastname,
                'outcallerid': callerid,
                'enableclient': False,
                'loginclient': '',
                'passwdclient': '',
                'mobilephonenumber': user.mobile or False,
                'musiconhold': server.xivo_default_moh,
                'profileclient': 'Client',
                'ringseconds': server.xivo_default_ring_seconds,
                'simultcalls': unicode(server.xivo_default_simult_calls),
                },
            # TODO : check option
            'voicemail-option': 'add',
            'voicemail': {
                'email': user.email or '',
                'mailbox': internal_number,
                'fullname': user.name,
                'password': server.xivo_default_voicemail_pin or '',
                'skipcheckpass': False,
                'attach': '1',
                'deletevoicemail': '1',
                },
        }
        if self.grant_xivo_client:
            res['userfeatures']['enableclient'] = True
            res['userfeatures']['loginclient'] = self.xivo_client_login
            res['userfeatures']['passwdclient'] = self.xivo_client_password
        pprint(res)
        return res

    @api.model
    def _prepare_incall_payload(self, incall_number, xivo_user_id):
        res = {
            'incall': {
                'exten': incall_number,
                'context': 'from-extern',
                'preprocess_subroutine': 'odoo',  # TODO
            },
            #  'callerid': {
            #     'mode': 'prepend', # = préfixe
            #     'callerdisplay': 'EXT',
            #  },
            'dialaction': {
                'answer': {
                    'actiontype': 'user',
                    'actionarg1': unicode(xivo_user_id),
                    'actionarg2': '',
                    },
            }
        }
        pprint(res)
        return res

    @api.multi
    def create_user(self):
        assert self._context['active_model'] == 'res.users'
        user = self.env['res.users'].browse(self._context['active_id'])
        if not user.internal_number:
            raise Warning(_(
                "Missing internal number on the user %s.") % user.name)
        intnum = user.internal_number
        logger.info(
            'Starting to create Xivo user %s with internal '
            'number %s', user.name, intnum)
        server = user.get_asterisk_server_from_user()
        if self.create_agent:
            # check if the agent already exists
            logger.info(
                "Check if an agent with number '%s' already exists", intnum)
            list_agent = server.xivo_get_request(
                '/callcenter/json.php/restricted/settings/agents?act=list')
            for agent in list_agent:
                if agent.get('number') == intnum:
                    raise Warning(_(
                        "An agent with internal number '%s' already exists: "
                        "agent ID = %s, Agent lastname = '%s'"
                        % (intnum, agent.get('id'), agent.get('lastname'))))
            logger.info(
                "There are currently no agents with number '%s'", intnum)
        # check if the user already exists
        logger.info(
            "Check if a line with internal number '%s' already exists"
            % intnum)
        list_lines = server.xivo_get_request(
            '/service/ipbx/json.php/restricted/pbx_settings/lines/'
            '?act=list&protocol=sip')
        for line in list_lines:
            if line.get('number') == intnum:
                raise Warning(_(
                    "A line with internal number '%s' already exists: "
                    "line ID %s, account %s/%s")
                    % (intnum, line.get('id'),
                       line.get('protocol') and line.get('protocol').upper(),
                       line.get('name')))
        logger.info(
            "There are currently no lines with internal number '%s'", intnum)

        # check if mailbox already exists even creating is not asked
        # We consider that mailbox number = internal number
        logger.info(
            "Check if a voicemail with number '%s' already exists", intnum)
        list_voicemail = server.xivo_get_request(
            '/service/ipbx/json.php/restricted/pbx_settings/voicemail/'
            '?act=list')
        for voicemail in list_voicemail:
            if voicemail.get('mailbox') == intnum:
                raise Warning(_(
                    "A voicemail with number '%s' already exists: "
                    "voicemail ID %s, fullname '%s'"
                    % (intnum, voicemail.get('uniqueid'),
                       voicemail.get('fullname'))))

        logger.info(
            "There are currently no voicemail with internal number '%s'",
            intnum)
        sda = False
        if self.create_incall:
            if not user.partner_id.phone:
                raise Warning(_(
                    "Failed to read the direct line in the Phone field on "
                    "the partner attached to the user %s") % user.name)
            sda = self.env['phone.common'].convert_to_dial_number(
                user.partner_id.phone)
            incall_id = False
            logger.info(
                "Check if the incoming call with number '%s' already exist",
                sda)
            list_incall = server.xivo_get_request(
                '/service/ipbx/json.php/restricted/call_management/incall/'
                '?act=list')
            for incall in list_incall:
                if incall.get('exten') == sda:
                    if not incall.get('id'):
                        raise Warning(_("Missing ID on incoming call !!!"))
                    incall_id = int(incall.get('id').replace('"', ''))
                    logger.warning(
                        "An incoming call with number '%s' already exists: "
                        "ID %d", (sda, incall_id))
                    break
            if not incall_id:
                logger.info(
                    "There are currently no incoming call with number '%s'",
                    sda)

        # Create agent
        new_agent_id = False
        if self.create_agent:
            logger.info("Starting to create a new agent")
            agent_payload = self._prepare_agent_payload(user, intnum)
            server.xivo_post_request(
                '/callcenter/json.php/restricted/settings/agents?act=add',
                agent_payload)
            logger.info("The new agent has been created")
            # The create agent request doesn't return the agent ID,
            # so I do a get right after
            list_agent_getid = server.xivo_get_request(
                '/callcenter/json.php/restricted/settings/agents?act=list')
            for agent in list_agent_getid:
                if agent.get('number') == intnum:
                    new_agent_id = int(agent.get('id'))
                    logger.info("The new agent has ID %d" % new_agent_id)
                    break
            assert new_agent_id, 'Could not get the Agent ID'

        callerid = self._prepare_callerid(user, server, sda)
        user_payload = self._prepare_user_payload(
            server, user, intnum, new_agent_id, callerid)
        res_create_user = server.xivo_post_request(
            '/service/ipbx/json.php/restricted/pbx_settings/users/?act=add',
            user_payload)
        logger.info("A new user has been created")
        xivo_user_id = int(res_create_user.content.replace('"', ''))
        if not xivo_user_id:
            raise Warning(_("Could not get the ID of the new user !!!"))
        logger.info("The newly created Xivo user has ID %d", xivo_user_id)
        sip_login = False
        logger.info("Get SIP login of new user ID %d" % xivo_user_id)
        view_user = server.xivo_get_request(
            '/service/ipbx/json.php/restricted/pbx_settings/users/'
            '?act=view&id=%d' % xivo_user_id)
        if not view_user.get('linefeatures'):
            raise Warning(_(
                "View Xivo user answer: 'linefeatures' not "
                "present in result. This should never happen"))
        if not isinstance(view_user.get('linefeatures'), list):
            raise Warning(_(
                "'linefeatures' key in answer is not a sequence. "
                "This should never happen"))
        sip_login = view_user.get('linefeatures')[0].get('name')
        if not sip_login:
            raise Warning(_(
                "Can't find the 'name' key in the 'linefeatures' key "
                "of the result. This should never happen"))
        if not isinstance(sip_login, (str, unicode)):
            raise Warning(_(
                "SIP login is not a string. This should never happen"))

        user.write({
            'xivo_user_identifier': xivo_user_id,
            'callerid': callerid,
            'resource': sip_login,
            })
        if self.create_incall:
            incall_payload = self._prepare_incall_payload(
                sda, xivo_user_id)
            if not incall_id:
                server.xivo_post_request(
                    '/service/ipbx/json.php/restricted/call_management/incall/'
                    '?act=add', incall_payload)
                logger.info("A new incoming call has been created")
            else:
                logger.warning(
                    "Updating the incoming call '%s' to link it to "
                    "the new xivo user" % sda)
                server.xivo_post_request(
                    '/service/ipbx/json.php/restricted/call_management/incall/'
                    '?act=edit&id=%d' % incall_id, incall_payload)
                logger.info("Incoming call '%s' has been updated" % sda)
        return
