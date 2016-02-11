import sys
import os
import argparse
import re

from keystoneclient import client as ks_client
from keystoneclient.auth import identity as ks_identity
from keystoneclient import session as ks_session
from keystoneclient.exceptions import NotFound
from novaclient import client as nova_client

from Processor import Processor

class Instance_Processor(Processor):

    def __init__(self):
        Processor.__init__(self)
        self.nc, self.kc = self.get_clients()

    @staticmethod
    def build_parser(parser, func):
        parser.epilog = 'The instance selection logic is AND or ORs.  \
        For example "mailout instances --tenant A --tenant B --status paused" \
        selects all instances in tenants A >OR< B >AND< that are in the \
        paused state'
        
        parser.add_argument('--ip', action='append', metavar='IP-ADDR',
                            dest='ips', default=[],
                            help='Selected instance IP address.  \
                            Can be repeated')
        parser.add_argument('--host', action='append', metavar='HOSTNAME',
                            dest='hosts', default=[],
                            help='Selected compute-node hostname.  \
                            Can be repeated')
        parser.add_argument('--tenant', action='append', metavar='NAME-OR-ID',
                            dest='tenants', default=[],
                            help='Selected tenant name or id.  \
                            Can be repeated')
        parser.add_argument('--status', action='append', metavar='STATUS',
                            dest='statuses', default=[],
                            help='Selected instance status.  \
                            Can be repeated')
        parser.add_argument('--instance', action='append', metavar='ID',
                            dest='instances', default=[],
                            help='Selected instance id.  \
                            Can be repeated')
        # Add more selectors as required
        
        parser.set_defaults(subcommand=func)
        parser.add_argument('--owners', action='store_true',
                            default=False,
                            help='Send emails to instance owners')
        parser.add_argument('--managers', action='store_true',
                            default=False,
                            help='Send emails to tenant managers')
        parser.add_argument('--members', action='store_true',
                            default=False,
                            help='Send emails to tenant members')
        parser.add_argument('--all-users', action='store_true',
                            default=False,
                            help='Send emails to owners, members and managers')

    def check_args(self, args):
        if len(args.ips) + len(args.hosts) + \
           len(args.tenants) + len(args.instances) == 0:
            sys.stderr.write("You must make least one primary selection " +
                             "using --instance, --ip, --host or --tenant\n")
            sys.exit(1)
        if args.all_users:
            args.owners = True
            args.members = True
            args.managers = True
        elif not args.owners and not args.managers and not args.members:
            sys.stderr.write("You must specify the email targets: " +
                             "one or more of --owners, --managers, " +
                             "--members or --all-users\n")
            sys.exit(1)
        # normalize to tenant ids
        args.tenants = map(lambda t: self.get_tenant_id(t), args.tenants)
        
    def select_resources(self, args, db, config):
        if len(args.instances) > 0:
            instances = self.simple_select(args.instances)
        else:
            searches, opts = self.build_searches(args)
            instances = list(self.select_instances(searches, opts))
            
        print len(instances)
        
        # Apply additional filters to the result set
        if len(args.ips) > 1:
            instances = filter(lambda i: i.accessIPv4 in args.ips, instances)
        if len(args.tenants) > 1:
            instances = filter(lambda i: i.tenant in args.tenants, instances)
        if len(args.hosts) > 1:
            instances = filter(lambda i: i.host in args.hosts, instances)
        if len(args.statuses) > 1:
            instances = filter(lambda i: i.status in args.statuses, instances)

        print len(instances)
        db['instances'] = instances
        return instances

    def simple_select(self, instance_ids):
        servers = self.nc.servers
        return map(lambda id: servers.get(id), instance_ids)

    def build_searches(self, args):
        opts = {}
        # Figure out query options based on a primary selectors with a single
        # value ... if any
        if len(args.ips) == 1:
            opts['ip'] = self.ip_regex(args.ips[0])
        if len(args.tenants) == 1:
            opts['tenant_id'] = self.get_tenant_id(args.tenants[0])
        if len(args.hosts) == 1:
            opts['host'] = args.hosts[0]
        if len(opts) == 0:
            # If no primary selector has a single value, pick one of them
            # and create queries for each of its values
            if len(args.ips) > 1:
                searches = map(lambda ip: {'ip': self.ip_regex(ip)},
                                args.ips)
            elif len(args.tenants) > 1:
                searches = map(lambda t: {'tenant_id': t},
                                args.tenants)
            elif len(args.hosts) > 1:
                searches = map(lambda h: {'host': h},
                                args.hosts)
        else:
            searches = [{}]
        opts['all_tenants'] = True
        return searches, opts


    def select_instances(self, searches, shared_opts):
        results = []
        for search_opts in searches:
            opts = shared_opts.copy()
            opts.update(search_opts)
            marker = None
            while True:
                if marker:
                    opts['marker'] = marker
                response = self.nc.servers.list(search_opts=opts)
                if not response:
                    break
                for server in response:
                    marker = server.id
                    yield server

    def relate_to_recipients(self, args, instances, db, config):
        users = {}
        tenants = {}
        for instance in instances:
            instance.get()
            tenant = self.fetch_tenant(db, instance.tenant_id)
            if args.owners:
                self.add_user(users, tenants, instance.user_id, instance)
            if args.managers or args.members:
                if args.managers:
                    for manager_id in tenant['managers']:
                        self.add_user(users, tenants, manager_id, instance) 
                if args.members:
                    for member_id in tenant['members']:
                        self.add_user(users, tenants, member_id, instance)
        print users.values()
        print tenants.values()
        db['recipient_users'] = users
        db['recipient_groups'] = tenants

    def add_user(self, users, tenants, user_id, instance):
        # Aggregate instances per user
        if user_id not in users:
            keystone_user = self.kc.users.get(user_id)
            user = {'id': user_id,
                    'email': keystone_user._info.get('email', None),
                    'instances': set()}
            users[user_id] = user
        else:
            user = users[user_id]
        user['instances'].add(instance)
        
        # Aggregate instances and users per tenant
        tenant_id = instance.tenant_id
        if tenant_id not in tenants:
            tenant = {'id': tenant_id,
                      'users': {},
                      'instances': set()}
            tenants[tenant_id] = tenant
        else:
            tenant = tenants[tenant_id]
        tenant['users'][user_id] = user
        tenant['instances'].add(instance)

    def get_tenant_id(self, name_or_id):
        try:
            tenant = self.kc.tenants.get(name_or_id)
        except NotFound:
            tenant = self.kc.tenants.find(name=name_or_id)
        print tenant
        return tenant.id
        
    def fetch_tenant(self, db, tenant_id):
        if 'tenants' not in db:
            db['tenants'] = {}
        if tenant_id in db['tenants']:
            return db['tenants'][tenant_id]
        tenant = self.kc.tenants.get(tenant_id)
        members = []
        managers = []
        for user in tenant.list_users():
            for role in user.list_roles(tenant):
                if role.name == "TenantManager":
                    managers.append(user.id)
                elif role.name == "Member":
                    members.append(user.id)
        info = {
            'id': tenant_id,
            'name': tenant.name,
            'members': members,
            'managers': managers,
            'enabled': tenant.enabled
        }
        db['tenants'][tenant_id] = info
        return info
        
    @staticmethod
    def ip_regex(ip):
        return "^%s$" % re.escape(ip)

    @staticmethod
    def get_clients():
        username = os.environ.get('OS_USERNAME')
        password = os.environ.get('OS_PASSWORD')
        tenant = os.environ.get('OS_TENANT_NAME')
        url = os.environ.get('OS_AUTH_URL')
        
        nc = nova_client.Client(2, username,
                                password,
                                tenant,
                                url,
                                service_type='compute')
        auth = ks_identity.v2.Password(username=username,
                                       password=password,
                                       tenant_name=tenant,
                                       auth_url=url)
        session = ks_session.Session(auth=auth)
        kc = ks_client.Client(session=session)
        return nc, kc

    
