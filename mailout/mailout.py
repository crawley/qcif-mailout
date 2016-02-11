#!/usr/bin/env python

import argparse
import sys

import ConfigParser
import Generator

from Instance_Processor import Instance_Processor
from CSV_Processor import CSV_Processor
from Mail_Sender import Mail_Sender

def help(args):
    if args.name:
        if args.name in args.subparsers:
            args.subparsers[args.name].print_help()
        else:
            print "Unrecognized subcommand %s" % args.name
    else:
        print "Use 'mailout --help' for general help"
        print "Use 'mailout help <subcommand>' for subcommand help"
    sys.exit(0)

def instances(args):
    do_mailout(args, Instance_Processor())

def csvs(args):
    do_mailout(args, CSV_Processor())

def write_skeleton_config(args):
    do_write_config(args)
    
def collect_args():
    parser = argparse.ArgumentParser(
        description='Perform a mailout to the users associated with selected \
        QRIScloud or NeCTAR resources')

    parser.add_argument('-y', '--no-dry-run', action='store_true',
                        default=False,
                        help='Do the mailout / email generation.  The default \
                        is to stop prior to the generation step')
    parser.add_argument('-l', '--limit',
                        type=int,
                        default=None,
                        help='Limit the number of emails processed, defaults \
                        to no limit.  (For testing)')
    parser.add_argument('-d', '--debug', action='store_true',
                        default=False,
                        help='Enable debugging')
    parser.add_argument('-P', '--print-only', action='store_true',
                        default=False,
                        help='Print emails bodies to standard output instead \
                        of sending them')
    parser.add_argument('-T', '--test-to',
                        default=None,
                        help='Send emails to this test email account instead \
                        of the notional recipient')
    parser.add_argument('-c', '--config',
                        default='./mailout.cfg',
                        help='The config file contains properties that \
                        control a lot of the behavior of the mailout tool.  \
                        You can add custom properties.')
    parser.add_argument('-s', '--subject',
                        default='None',
                        help='The email subject.  Defaults to the value in \
                        the config file')
    parser.add_argument('-t', '--template',
                        default='template',
                        help='The basename for the email generator templates. \
                        defaults to "template"')
    parser.add_argument('--by-groups', action='store_true',
                        default=False,
                        help='Generate emails by group rather than by \
                        individual user')
    
    subparsers = parser.add_subparsers(help='subcommand help')

    instance_parser = subparsers.add_parser('instances',
                                            help='mailout to users associated \
                                            with selected NeCTAR instances')
    Instance_Processor.build_parser(instance_parser, instances)

    wsc_parser = subparsers.add_parser('write-skeleton-config', 
                                       help='(just) write a skeleton config \
                                       file')
    wsc_parser.set_defaults(subcommand=write_skeleton_config)

    csv_parser = subparsers.add_parser('from-csv',
                                       help='mailout to users selected from \
                                       a CSV file')
    CSV_Processor.build_parser(csv_parser, csvs)

    tenant_parser = subparsers.add_parser('tenants',
                                          help='mailout to users associated \
                                          with selected NeCTAR tenants \
                                          (not implemented)')

    qrisdata_parser = subparsers.add_parser('qrisdata',
                                            help='mailout to users associated \
                                            with selected QRISdata collections \
                                            (not implemented)')
    
    alloc_parser = subparsers.add_parser('allocations',
                                         help='mailout to users associated \
                                         with selected NeCTAR allocations \
                                         (not implemented)')
    
    help_parser = subparsers.add_parser('help',
                                        help='print subcommand help')
    help_parser.add_argument('name', nargs='?', default=None,
                             help='name of a subcommand')
    help_parser.set_defaults(subcommand=help,
                             subparsers={
                                 'help': help_parser,
                                 'instances': instance_parser,
                                 'tenants': tenant_parser,
                                 'allocations': alloc_parser,
                                 'qrisdata': qrisdata_parser,
                                 'from-csv': csv_parser,
                                 'write-skeleton-config': wsc_parser})
    return parser

def do_mailout(args, processor):
    config = load_config(args)
    generator = instantiate_generator(args)
    db = processor.process(args, config)
    if not args.no_dry_run:
        sys.stderr.write(('No emails sent: A total of %d users would receive ' +
                          'an email in this mailout\n') % \
                         len(db['recipient_users']))
        sys.stderr.write('  rerun with "-y" to send the emails\n')
        sys.stderr.write('  rerun with "-y" "-P" to just generate the email ' +
                         'bodies to standard output\n')
        sys.stderr.write('  include "--limit N" to stop after the first N ' +
                         'users\n')
        sys.exit(0)
    sender = Mail_Sender(config, db, generator,
                         test_to=args.test_to,
                         print_only=args.print_only,
                         debug=args.debug,
                         subject=args.subject,
                         limit=args.limit)
    if args.by_user:
        for user in db['recipient_users'].values():
            print user
            sender.render_and_send_by_user(user)
    else:
        for tenant in db['recipient_groups'].values():
            print tenant
            sender.render_and_send_by_groups(tenant)
            
    sys.stderr.write('A total of %d emails were generated / sent\n' %
                     sender.all_msgs_sent)

def instantiate_generator(args):
    return Generator.Generator(args.template)
    
def load_config(args):
    config = ConfigParser.SafeConfigParser({}, dict, True)
    config.readfp(open(args.config, 'r'))
    return config

def do_write_config(args):
    config = ConfigParser.RawConfigParser({}, dict, True)
    Mail_Sender.init_config(config)
    with open(args.config, 'wb') as configfile:
        config.write(configfile)
    
def main():
    args = collect_args().parse_args()
    args.subcommand(args)

if __name__ == '__main__':
    main()
