#!/usr/bin/env python

import argparse
import sys
import logging
import os

import ConfigParser
import Generator

from Instance_Processor import Instance_Processor
from CSV_Processor import CSV_Processor
from DB_Processor import DB_Processor
from Mail_Sender import Mail_Sender
from Summarizer import Summarizer

def help(args):
    if args.name:
        if args.name in args.subparsers:
            args.subparsers[args.name].print_help()
        else:
            sys.stderr.write("Unrecognized subcommand %s\n" % args.name)
    else:
        sys.stderr.write("Use 'mailout --help' for general help\n")
        sys.stderr.write("Use 'mailout help <subcommand>' for subcommand help\n")
    sys.exit(0)

def instances(args):
    do_mailout(args, Instance_Processor(debug=args.debug))

def csvs(args):
    do_mailout(args, CSV_Processor())

def dbs(args):
    configPath = args.db_config or args.config
    config = load_config(configPath)
    do_mailout(args, DB_Processor(config))

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
    parser.add_argument('--print-only', action='store_true',
                        default=False,
                        help='Print emails bodies to standard output instead \
                        of sending them')
    parser.add_argument('--summarize-only', action='store_true',
                        default=False,
                        help='Print summaries to standard output instead \
                        of sending emails')
    parser.add_argument('-T', '--test-to',
                        default=None,
                        help='Send emails to this test email account instead \
                        of the notional recipient')
    parser.add_argument('-c', '--config',
                        default='~/.mailout.cfg',
                        help='The config file contains properties that \
                        control a lot of the behavior of the mailout tool.  \
                        You can add custom properties.')
    parser.add_argument('-p', '--property', action='append',
                        default=[],
                        help='Adds an arbitrary template property.  This \
                        can be repeated.')
    parser.add_argument('-s', '--subject',
                        default=None,
                        help='The email subject.  Defaults to the value in \
                        the config file')
    parser.add_argument('-C', '--cc', metavar='EMAIL',
                        dest='ccs', action='append', default=[],
                        help='An additional Cc: for the email; e.g. if you \
                        want to send a copy of the email to a ticket system')
    parser.add_argument('--skip-to',
                        default=None,
                        help='Skip over users (or groups) until this one. \
                        This allows you restart a mailout that failed part \
                        way through.')
    parser.add_argument('-t', '--template',
                        default='template',
                        help='The basename for the email generator templates. \
                        defaults to "template"')
    parser.add_argument('--by-group', action='store_true',
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

    csv_parser = subparsers.add_parser('csv',
                                       help='mailout to users selected from \
                                       a CSV file')
    CSV_Processor.build_parser(csv_parser, csvs)

    db_parser = subparsers.add_parser('db',
                                       help='mailout to users selected from \
                                       a MySQL database')
    DB_Processor.build_parser(db_parser, dbs)

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
                                 'csv': csv_parser,
                                 'db': db_parser,
                                 'write-skeleton-config': wsc_parser})
    return parser


def setup_debug(debug):
    if debug:
        streamformat = "%(levelname)s (%(module)s:%(lineno)d) %(message)s"
        logging.basicConfig(level=logging.DEBUG,
                            format=streamformat)
        logging.getLogger('iso8601').setLevel(logging.WARNING)

def do_mailout(args, processor):
    sys.stderr.write('Command line options: %s\n' % sys.argv)
    config = load_config(args.config)
    subject = args.subject
    if subject == None:
        subject = config.get('Envelope', 'subject')
    if subject == None:
        if args.summarize_only:
            subject = "Dummy subject"  # not used
        else:
            raise Exception("No subject / subject template supplied")
    extra_params = build_params(args)
    generator = instantiate_generator(args, subject)
    db = processor.process(args, config)
    db.update(extra_params)
    if args.summarize_only:
        sender = Summarizer(config, db, generator, debug=args.debug)
    elif args.no_dry_run:
        sender = Mail_Sender(config, db, generator,
                             test_to=args.test_to,
                             ccs=args.ccs,
                             print_only=args.print_only,
                             debug=args.debug,
                             limit=args.limit)
    else:
        sys.stderr.write(('No emails sent: A total of %d users would receive ' +
                          'an email in this mailout\n') % \
                         len(db['recipient_users']))
        sys.stderr.write('  rerun with "-y" to send the emails\n')
        sys.stderr.write('  rerun with "-y" "--print-only" to just generate ' +
                         'the emails to standard output\n')
        sys.stderr.write('  include "-T <your email>" to do a test run ' +
                         'sending all of the emails to yourself (only)\n')
        sys.stderr.write('  include "--limit N" to stop after the first N ' +
                         'emails\n')
        sys.exit(0)

    map = db['recipient_groups'] if args.by_group else db['recipient_users']
    keys = sorted(map.keys())
    
    skip_to = args.skip_to
    for key in keys:
        if skip_to is not None:
            if key != skip_to:
                continue
            skip_to = None
        obj = map[key]
        if args.debug:
            sys.stderr.write("key %s --> %s\n" % (key, obj))
        if args.by_group:
            sender.render_and_send(group=obj)
        else:
            sender.render_and_send(user=obj)

    sys.stderr.write('A total of %d emails were generated / sent\n' %
                     sender.all_msgs_sent)
    if args.by_group:
        sys.stderr.write('A total of %d emails copies were sent\n' %
                         sender.all_copies_sent)

def instantiate_generator(args, subject):
    return Generator.Generator(args.template, subject)

def build_params(args):
    res = {}
    for p in args.property:
        nv = p.strip().split('=', 1)
        if len(nv) == 1 and p[0] != '':
            res[nv[0]] = ''
        elif len(nv) == 2:
            res[nv[0]] = nv[1]
    if args.debug:
        sys.stderr.write("params %s\n" % (res))
    return res
    

def load_config(configPath):
    config = ConfigParser.SafeConfigParser({}, dict, True)
    config.readfp(open(os.path.expanduser(configPath), 'r'))
    return config

def do_write_config(configPath):
    config = ConfigParser.RawConfigParser({}, dict, True)
    Mail_Sender.init_config(config)
    DB_Processor.init_config(config)
    filename = os.path.expanduser(configPath)
    if os.path.exists(filename):
        if not query_yes_no('File "%s" already exists.  Overwrite it?' % filename,
                            default='no'):
            sys.exit(1)
        
    with open(filename, 'wb') as configfile:
        config.write(configfile)

# Copied from here: http://code.activestate.com/recipes/577058/
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")
    
def main():
    args = collect_args().parse_args()
    setup_debug(args.debug)
    args.subcommand(args)

if __name__ == '__main__':
    main()
