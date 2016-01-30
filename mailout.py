#!/usr/bin/env python

import argparse
import sys

import ConfigParser
import Generator

from Instance_Processor import Instance_Processor
from Mail_Sender import Mail_Sender

def help(args):
    if args.name:
        if args.name in args.subparsers:
            args.subparsers[args.name].print_help()
        else:
            print "Unrecognized subcommand %s" % args.name
    else:
        print "bar"
    sys.exit(0)

def instances(args):
    do_mailout(args, Instance_Processor())

def collect_args():
    parser = argparse.ArgumentParser(
        description='Perform a mailout to the users associated with selected \
        QRIScloud or NeCTAR resources')

    parser.add_argument('--write-skeleton-config', action='store_true',
                        default=False,
                        help='Write a skeleton config file and exit')
    parser.add_argument('-y', '--no-dry-run', action='store_false',
                        default=True,
                        help='Perform the actual actions, \
                        default is to only show what would happen')
    parser.add_argument('-l', '--limit',
                        default=None,
                        help='Limit the number of emails processed, defaults \
                        to no limit.  (For testing)')
    parser.add_argument('--max-emails-per-connection', 
                        default=100,
                        help='Limit the number of emails sent over one SMTP \
                        connection, defaults to 100')
    parser.add_argument('-d', '--debug', action='store_true',
                        default=False,
                        help='Enable debugging')
    parser.add_argument('-P', '--print-only', action='store_true',
                        default=False,
                        help='Print emails bodies to standard output instead \
                        of sending them')
    parser.add_argument('-c', '--config',
                        default='./mailout.cfg',
                        help='The config file contains properties that \
                        control a lot of the behavior of the mailout tool.  \
                        You can add custom properties.')
    parser.add_argument('-t', '--template',
                        default='template',
                        help='The basename for the email generator templates. \
                        defaults to "template"')
    subparsers = parser.add_subparsers(help='subcommand help')

    instance_parser = subparsers.add_parser('instances',
                                            help='mailout to users associated \
                                            with selected NeCTAR instances')
    Instance_Processor.build_parser(instance_parser, instances)

    tenant_parser = subparsers.add_parser('tenants',
                                          help='mailout to users associated \
                                          with selected NeCTAR tenants')

    qrisdata_parser = subparsers.add_parser('qrisdata',
                                            help='mailout to users associated \
                                            with selected QRISdata collections')
    
    alloc_parser = subparsers.add_parser('allocations',
                                          help='mailout to users associated \
                                          with selected NeCTAR allocations')
    
    help_parser = subparsers.add_parser('help',
                                        help='print subcommand help')
    help_parser.add_argument('name', nargs='?', default=None,
                             help='name of a subcommand')
    help_parser.set_defaults(subcommand=help,
                             subparsers={'help': help_parser,
                                         'instances': instance_parser,
                                         'tenants': tenant_parser,
                                         'allocations': alloc_parser,
                                         'qrisdata': qrisdata_parser})
    return parser

def do_mailout(args, processor):
    config = load_config(args)
    generator = instantiate_generator(args)
    users, db = processor.process(args, config)
    sender = Mail_Sender(config, db, generator,
                         print_only=args.print_only,
                         debug=args.debug,
                         limit=args.limit)
    for user in users.values():
        print user
        sender.render_and_send(user)
    sys.stderr.write('A total of %d emails were generated / sent\n' %
                     sender.all_msgs_sent)

def instantiate_generator(args):
    return Generator.Generator(args.template)
    
def load_config(args):
    config = ConfigParser.SafeConfigParser({}, dict, True)
    config.read(args.config)
    return config

def write_config(args):
    config = ConfigParser.RawConfigParser({}, dict, True)
    config.add_section('SMTP')
    config.set('SMTP', 'server', '127.0.0.1')
    config.set('SMTP', 'max-tries-per-connection', 100)
    config.add_section('Envelope')
    config.set('Envelope', 'from',
               'NeCTAR Research Cloud <bounces@rc.nectar.org.au>')
    config.set('Envelope', 'sender', None)
    config.set('Envelope', 'reply-to', 'support@rc.nectar.org.au')
    config.set('Envelope', 'subject', None)
    with open(args.config, 'wb') as configfile:
        config.write(configfile)
    
def main():
    args = collect_args().parse_args()
    if args.write_skeleton_config:
        write_config(args)
        sys.exit(0)
    args.subcommand(args)

if __name__ == '__main__':
    main()
