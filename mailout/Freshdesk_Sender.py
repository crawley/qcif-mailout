import argparse
import csv
import os
import sys
import time

from freshdesk.v2.api import API

from Sender import Sender

class Freshdesk_Sender(Sender):
    
    def __init__(self, *args, **kwargs):
        Sender.__init__(self, *args, **kwargs)
        self.domain = self.config.get('Freshdesk', 'domain')
        self.friendly_domain = self._get_optional('Freshdesk',
                                                  'friendly-domain',
                                                  dflt=self.domain)
        self.api_key = self._get_optional('Freshdesk', 'api-key', dflt='')
        if self.api_key == '':
            raise Exception("No Freshdesk api-key set: refer to README.md!")

        # It would be possible to look this up ...
        self.email_config_id = self.config.getint('Freshdesk',
                                                  'email-config-id')
        # It would be possible to look this up ...
        self.group_id = self.config.getint('Freshdesk', 'group-id')
        
        priority = self.config.get('Freshdesk', 'priority')
        try:
            self.priority = {'low': 1, 'medium': 2,
                             'high': 3, 'urgent': 4}[priority]
        except KeyError:
            raise Exception("Unknown ticket priority {}".format(priority))

        status = self.config.get('Freshdesk', 'status')
        try:
            self.status = {'open': 2, 'pending': 3,
                           'resolved': 4, 'closed': 5}[status]
        except KeyError:
            raise Exception("Unknown ticket status {}".format(status))
            
        self.subject_prefix = self.config.get('Freshdesk', 'subject-prefix')
        tags = self.config.get('Freshdesk', 'tags')
        self.tags = [] if tags == '' else \
                    map((lambda s: s.strip()), tags.split(','))
        self.need_html = True
        if self.bccs:
            raise Exception("Freshdesk outbounding does not support Bcc")
        self.freshdesk = None
        self.max_tries = 1
        self.rate = self.config.getfloat('Freshdesk', 'messages-per-second')
        self.delay_after_send = 1.0 / self.rate if self.rate else None
        if self.debug:
            print('Freshdesk_Sender: {}'.format(self.__dict__))


    @staticmethod
    def init_config(config):
        Sender.init_config(config)
        config.add_section('Freshdesk')
        config.set('Freshdesk', 'domain', 'dhdnectar.freshdesk.com')
        config.set('Freshdesk', 'friendly-domain', 'support.ehelp.edu.au')
        config.set('Freshdesk', 'api-key', None) # must get manually ...
        config.set('Freshdesk', 'email-config-id', '6000071619')
        config.set('Freshdesk', 'group-id', '6000144734')
        config.set('Freshdesk', 'priority', 'medium')
        config.set('Freshdesk', 'status', 'closed')
        config.set('Freshdesk', 'subject-prefix', '[Nectar Notice] ')
        config.set('Freshdesk', 'tags', 'notification') # comma separated
        config.set('Freshdesk', 'messages-per-second', '1.0')

    def send_message(self, recipients, subject, text, html=None):
        if not self.presend_checks(recipients, subject, text, html):
            return

        addresses = recipients + self.ccs if self.ccs else []
        to_address = addresses.pop(0)
        
        if self.test_to:
            print('Would send ticket to: {}, cc: {}'
                  .format(to_address, addresses))
            to_address = self.test_to
            addresses = []
        else:
            print('Sending ticket to: {}, cc: {},'
                  .format(to_address, addresses))

        success = False
        try:
            freshdesk = self.get_freshdesk()
            if self.subject_prefix:
                subject = "{} {}".format(self.subject_prefix, subject)
            ticket = freshdesk.tickets.create_outbound_email(
                description=html,
                subject=subject,
                email=to_address,
                cc_emails=addresses,
                email_config_id=self.email_config_id,
                group_id=self.group_id,
                priority=self.priority,
                status=self.status,
                tags=self.tags)
            ticket_url = "https://{}/helpdesk/tickets/{}".format(
                self.friendly_domain, ticket.id)                
            print('Ticket URL: {}'.format(ticket_url))
            success = True
        finally:
            self.message_sent(success, len(recipients))

    def get_freshdesk(self):
        if self.freshdesk is None:
            self.freshdesk = API(self.domain, self.api_key)
            self.msgs_tries = 0
        return self.freshdesk

