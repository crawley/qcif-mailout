import sys
import os
import argparse
import re

import os_client_config

from keystoneclient.exceptions import NotFound

from Processor import Processor

class Instance_Processor(Processor):
    def __init__(self, debug=False):
        Processor.__init__(self)
        self.debug = debug
        self.nova, self.keystone, self.neutron = self.get_clients(debug=debug)
        self.tm_id = self.keystone.roles.find(name="TenantManager").id
        self.member_id = self.keystone.roles.find(name="Member").id
        

    @staticmethod
    def build_parser(parser, func):
        parser.epilog = 'The instance selection logic is AND or ORs.  \
        For example "mailout instances --tenant A --tenant B --status paused" \
        selects all instances in tenants A >OR< B >AND< that are in the \
        paused state'
        
        parser.add_argument('--ip', action='append', metavar='IP-ADDR',
                            dest='ips', default=[],
                            help='Selects by instance IP address.  \
                            Can be repeated')
        parser.add_argument('--host', action='append', metavar='HOSTNAME',
                            dest='hosts', default=[],
                            help='Selects by compute-node hostname.  \
                            Can be repeated')
        parser.add_argument('--ip-regex', action='append', metavar='REGEX',
                            dest='ipregexes', default=[],
                            help='Filters by instance IP address (regex).  \
                            Can be repeated')
        parser.add_argument('--host-regex', action='append',
                            metavar='REGEX',
                            dest='hostregexes', default=[],
                            help='Filters by compute-node hostname (regex).  \
                            Can be repeated')
        parser.add_argument('--tenant', action='append', metavar='NAME-OR-ID',
                            dest='tenants', default=[],
                            help='Selects by tenant name or id.  \
                            Can be repeated')
        parser.add_argument('--status', action='append', metavar='STATUS',
                            dest='statuses', default=[],
                            help='Filters by instance status.  \
                            Can be repeated')
        parser.add_argument('--instance', action='append', metavar='ID',
                            dest='instances', default=[],
                            help='Selects by instance id.  \
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
        if (len(args.ips) + len(args.hosts) +
            len(args.tenants) + len(args.instances) +
            len(args.hostregexes) + len(args.ipregexes) == 0):
            sys.stderr.write("You must make least one primary selection " +
                             "using --instance, --ip, --host, --tenant " +
                             "--ip-regex or --host-regex\n")
            sys.exit(1)
        if ((len(args.ips) > 0 and len(args.ipregexes) > 0) or
            (len(args.hosts) > 0 and len(args.hostregexes) > 0)):
            sys.stderr.write("You cannot mix direct selection and regex " +
                             "selection options for hosts or ips\n")
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
        elif len(args.ips) > 0:
            instances = self.neutron_select(args.ips)
        else:
            searches, opts = self.build_searches(args)
            instances = list(self.select_instances(searches, opts))
            
        if self.debug:
            sys.stderr.write("nos instances = %d\n" % len(instances))
        
        # Apply additional filters to the result set
        if len(args.ips) > 1:
            instances = filter(lambda i: i.accessIPv4 in args.ips, instances)
        if len(args.ipregexes) > 1:
            regexes = self.rcompile(args.ipregexes)
            instances = filter(lambda i: self.rmatch(i.accessIPv4, regexes),
                               instances)
        if len(args.tenants) > 1:
            instances = filter(lambda i: i.tenant in args.tenants, instances)
        if len(args.hosts) > 1:
            instances = filter(lambda i: i.to_dict()['OS-EXT-SRV-ATTR:host'] \
                               in args.hosts, instances)
        if len(args.hostregexes) > 0:
            regexes = self.rcompile(args.hostregexes)
            instances = filter(lambda i: self.rmatch(i.to_dict()['OS-EXT-SRV-ATTR:host'],
                                                     regexes), instances)
        if len(args.statuses) > 1:
            instances = filter(lambda i: i.status in args.statuses, instances)

        if self.debug:
            sys.stderr.write("nos instances = %d\n" % len(instances))
        db['instances'] = instances
        return instances

    def simple_select(self, instance_ids):
        return map(lambda id: self.nova.servers.get(id), instance_ids)

    def neutron_select(self, ips):
        # Recent changes to Nova have made "nova list --all-tenants --ip"
        # queries horribly slow.  So now we use "neutron port-list" instead.
        res = []
        for ip in ips:
            ports = self.neutron.list_ports(fixed_ips=('ip_address=' + ip))
            if len(ports['ports']) == 1:
                id = ports['ports'][0]['device_id']
                res.append(self.nova.servers.get(id))
        return res

    def build_searches(self, args):
        opts = {}
        # Figure out query options based on a primary selectors with a single
        # value ... if any
        searches = [{}]
        if len(args.ipregexes) == 1:
            opts['ip'] = args.ipregexes[0]
        if len(args.tenants) == 1:
            opts['tenant_id'] = self.get_tenant_id(args.tenants[0])
        if len(args.hosts) == 1:
            opts['host'] = args.hosts[0]
        if len(opts) == 0:
            # If no primary selector has a single value, pick one of them
            # and create queries for each of its values
            if len(args.ipregexes) > 1:
                searches = map(lambda ip: {'ip': ip}, args.ipregexes)
            elif len(args.tenants) > 1:
                searches = map(lambda t: {'tenant_id': t}, args.tenants)
            elif len(args.hosts) > 1:
                searches = map(lambda h: {'host': h}, args.hosts)
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
                response = self.nova.servers.list(search_opts=opts)
                if not response:
                    break
                for server in response:
                    marker = server.id
                    yield server

    def relate_to_recipients(self, args, instances, db, config):
        users = {}
        tenants = {}
        for instance in instances:
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
        if self.debug:
            sys.stderr.write("users: {}\ntenants: {}\n".format(
                users.values(),
                tenants.values()))
        db['recipient_users'] = users
        db['recipient_groups'] = tenants

    def add_user(self, users, tenants, user_id, instance):
        # Aggregate instances per user
        if user_id not in users:
            keystone_user = self.keystone.users.get(user_id)
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
            tenant = self.keystone.projects.get(name_or_id)
        except NotFound:
            tenant = self.keystone.projects.find(name=name_or_id)
        return tenant.id
        
    def fetch_tenant(self, db, tenant_id):
        if 'tenants' not in db:
            db['tenants'] = {}
        if tenant_id in db['tenants']:
            return db['tenants'][tenant_id]
        tenant = self.keystone.projects.get(tenant_id)
        members = []
        managers = []
        for ra in self.keystone.role_assignments.list(project=tenant):
            if ra.role['id'] == self.tm_id:
                managers.append(ra.user['id'])
            elif ra.role['id'] == self.member_id:
                members.append(ra.user['id'])
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
    def rcompile(regexes):
        return map(lambda r: re.compile(r), regexes)
    
    @staticmethod
    def rmatch(str, regexes):
        return str and any(map(lambda r: r.match(str), regexes))

    @staticmethod
    def ip_regex(ip):
        return "^%s$" % re.escape(ip)

    @staticmethod
    def get_clients(debug=False):
        nova = os_client_config.make_client('compute',
                                            http_log_debug=debug)
        keystone = os_client_config.make_client('identity',
                                                debug=debug)
        neutron = os_client_config.make_client('network',
                                               http_log_debug=debug)
        return nova, keystone, neutron

    
