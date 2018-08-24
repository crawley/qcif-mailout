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
        self.api_key = self.config.get('Freshdesk', 'api_key')
        if self.api_key is None or self.api_key == '':
            raise Exception("No Freshdesk api-key set: refer to README.md!")
        self.email_config_id = self.config.getint('Freshdesk',
                                                  'email_config_id')
        self.group_id = self.config.getint('Freshdesk', 'group-id')
        self.priority = self.config.getint('Freshdesk', 'priority')
        self.status = self.config.getint('Freshdesk', 'status')
        self.subject_prefix = self.config.get('Freshdesk', 'subject-prefix')
        tags = self.config.get('Freshdesk', 'tags')
        self.tags = [] if tags == '' else \
                    map((lambda s: s.strip()), tags.split(','))
        self.need_html = True
        self.freshdesk = None
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
        config.set('Freshdesk', 'priority', '2')
        config.set('Freshdesk', 'status', '5')  # initially closed
        config.set('Freshdesk', 'subject-prefix', '[Nectar Notice] ')
        config.set('Freshdesk', 'tags', 'notification') # comma separated
        config.set('Freshdesk', 'messages-per-second', '1.0')

    def send_message(self, recipients, subject, text, html=None):
        if not self.presend_checks(recipients, subject, text, html):
            return

        addresses = recipients + self.ccs if self.ccs else []
        bcc_addresses = self.bccs if self.bccs else []
        to_address = addresses.pop(0)
        
        if self.test_to:
            print('Would send ticket to: {}, cc: {}, bcc: {}'
                  .format(to_address, addresses, bcc_addresses))
            to_address = self.test_to
            addresses = []
            bcc_addresses = []
        else:
            print('Sending ticket to: {}, cc: {}, bcc: {}'
                  .format(to_address, addresses, bcc_addresses))

        try:
            ticket = self.freshdesk.create_outbount_email(
                description=html,
                subject=self.subject_prefix + subject,
                email=to_address,
                cc_emails=addresses,
                bcc_emails=bcc_addresses,
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
            self.msgs_tried = 0
        return self.freshdesk

