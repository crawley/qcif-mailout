import sys
import os
import argparse
import csv

from Processor import Processor

class CSV_Processor(Processor):

    def __init__(self):
        Processor.__init__(self)

    @staticmethod
    def build_parser(parser, func):
        parser.epilog = 'The CSV must have a column containing the users \
        email address.  The rows are collated using the email as the key. \
        some fields may be designated as user identifiers.'
        
        parser.add_argument('--email', metavar='COLUMN-NAME',
                            dest='email', default='email',
                            help='Denotes the email column: default "email"')
        parser.add_argument('--key', action='append', metavar='COLUMN-NAME',
                            dest='keys', default=[],
                            help='Denotes a resource key column.  \
                            Can be repeated')
        parser.add_argument('--name', action='append', metavar='COLUMN-NAME',
                            dest='names', default=[],
                            help='Optionally denotes a user name column.  \
                            Can be repeated')
        parser.add_argument('filename', metavar='FILE-NAME',
                            default=None,
                            help='The input CSV filename')
        # Add more selectors as required
        
        parser.set_defaults(subcommand=func)

        
    def check_args(self, args):
        pass
        
    def select_resources(self, args, db, config):
        with open(args.filename) as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader)

    def related_users(self, args, rows, db, config):
        users = {}
        for row in rows:
            self.add_user(users, args, row)
        print users
        return users

    def add_user(self, users, args, row):
        email = row[args.email]
        if email not in users:
            user = {'email': email,
                    'resources': {}}
            for name in args.names:
                user[name] = row[name]
            users[email] = user
        else:
            user = users[email]
        resource_key = tuple(map(lambda k : row[k], args.keys))
        user['resources'][resource_key] = row
        
 
