#!/usr/bin/env python
"""HurricaneDNS Command Line tools/shell

Inspired by & heavily borrowed from the EveryDNS Command Line tool/shell by
    Scott Yang: http://svn.fucoder.com/fucoder/pyeverydns/everydnscmd.py
"""
__author__ = "Brian Hartvigsen <brian.andrew@brianandjenny.com>"
__copyright__ = "Copyright 2015, Brian Hartvigsen"
__credits__ = ["Scott Yang", "Brian Hartvigsen"]
__license__ = "MIT"
__version__ = "0.4"

import cmd
from shlex import split as split_args
import HurricaneDNS


def write_help(func):
    def decorator(self):
        from cStringIO import StringIO
        for line in StringIO(func.__doc__):
            line = line.strip()
            if line.startswith('!'):
                print line[1:].upper()
            else:
                print '        ' + line

    return decorator


class HurricaneDNSShell(cmd.Cmd):
    def __init__(self, username, password):
        cmd.Cmd.__init__(self)
        self.__username = username
        self.__password = password
        self.__hdns = None
        self._make_prompt()

    def default(self, line):
        self._do_error('command not found')

    def completedefault(self, text, line, begidx, endidx):
        pass

    def do_add(self, args):
        """!NAME
        add - Add a domain/record

        !SYNOPSIS
        add domain [domain option]
        add domain host type value [mx] [ttl]

        !DESCRIPTION
        Add either a domain or a host record to HurricaneDNS. If the number of
        arguments is 1 or 2, it will add the domain in arg 1, and then use arg
        2 as option. If the number of arguments is between 4 and 6, it will
        add the host record with optional MX and TTL.

        """
        args = split_args(args)
        try:
            if len(args) and len(args) < 3:
                domain = args[0]
                extra = {}
                if len(args) == 2:
                    (option, value) = args[1].split("=", 1)
                    extra[option] = value
                self._get_hdns().add_domain(domain, **extra)
            elif 6 >= len(args) >= 4:
                    self._get_hdns().add_record(*args)
            else:
                self._do_error('Invalid arguments')
        except HurricaneDNS.HurricaneError as e:
            self._do_error(e)

    def complete_add(self, text, line, begidx, endidx):
        def filter_down(args, pos, possibiles):
            start = args[pos - 1] if len(args) == pos else None
            final = filter(lambda x: x.startswith(start) if start else True, possibiles)
            return final

        args = line.split()
        pos = len(args)
        if not text:
            pos += 1

        domains = map(lambda x: x['domain'], self._get_hdns().cache_domains())
        if pos == 2:
            return filter_down(args, pos, domains)
        elif not args[1] in domains:
            if pos == 3:
                return filter_down(args, pos, ["method=", "master="])
            else:
                return []
        else:
            if pos == 4:
                types = []
                if args[1].endswith('.in-addr.arpa') or args[1].endswith('.ip6.arpa'):
                    types = ["CNAME", "NS", "PTR", "TXT"]
                else:
                    types = ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "AFSDB", "HINFO", "RP", "LOC", "NAPTR", "PTR", "SSHFP", "SPF", "SRV"]
                return filter_down(args, pos, types)
            else:
                pass

    def do_del(self, args):
        """!NAME
        del - Delete domain or host records

        !SYNOPSIS
        del domain
        del domain host [type] [value] [mx] [ttl]

        !DESCRIPTION
        Delete either domain or host records. If only 1 argument is given, it
        will use that as the domain name ot delete. Otherwise it will delete
        host records that match the arguments.

        """
        args = split_args(args)
        try:
            if len(args) == 1:
                self._get_hdns().del_domain(args[0])
            elif len(args) > 1:
                self._get_hdns().del_records(*args)
        except HurricaneDNS.HurricaneError as e:
            self._do_error(e)

    def do_EOF(self, args):
        print
        return 1

    def do_exit(self, args):
        return 1

    def complete_ls(self, text, line, begidx, endidx):
        domains = filter(lambda x: x.startswith(text) if text else True,
                         map(lambda x: x['domain'], self._get_hdns().cache_domains()))
        return domains

    def do_ls(self, args):
        """!NAME
        ls - List domains or host records

        !SYNOPSIS
        ls
        ls domain [domain...]

        !DESCRIPTION
        Listing all the domains when there is no argument. Otherwise list all
        host records from the specified domains.

        """
        if args:
            existing = self._get_hdns().cache_domains()
            existing = set([item['domain'] for item in existing])
            records = []
            for domain in split_args(args):
                if domain.lower() not in existing:
                    self._do_error('Invalid domain: ' + domain)
                    continue
                records.extend(self._get_hdns().cache_records(domain))

            if records:
                maxhost = max([len(item['host']) for item in records])
                maxvalue = max([len(item['value']) for item in records])
                maxttl = max([len(item['ttl']) for item in records])
                template = '%%%ds %%-5s %%-%ds %%%ds %%6s' % (maxhost, maxvalue, maxttl)
                print template % ('HOST', 'TYPE', 'VALUE', 'TTL', 'MX')
                for record in records:
                    print template % (record['host'], record['type'], record['value'], record['ttl'], record['mx'])
        else:
            domains = self._get_hdns().cache_domains()
            domains.sort(key=lambda item: item['domain'])
            print 'TYPE       DOMAIN'
            for domain in domains:
                print '%-9s %s' % (domain['type'], domain['domain'])

    def emptyline(self):
        pass

    help_add = write_help(do_add)
    help_del = write_help(do_del)
    help_ls = write_help(do_ls)

    def _do_error(self, errmsg):
        command = self.lastcmd.split()[0]
        print 'hdnssh: %s: %s' % (command, errmsg)

    def _get_hdns(self):
        if not self.__hdns:
            self.__hdns = HurricaneDNS.HurricaneDNS(self.__username, self.__password)
        return self.__hdns

    def _make_prompt(self):
        self.prompt = '[%s@dns.he.net] ' % self.__username

    def cmdloop(self):
        try:
            cmd.Cmd.cmdloop(self)
        except KeyboardInterrupt:
            print
            self.cmdloop()


def main():
    import argparse
    from sys import exit, stdin
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='version', version="%%(prog)s %s (%s)" % (__version__, __author__))
    parser.add_argument('username', help="Your HE DNS username")
    parser.add_argument('password', help="Your HE DNS password")
    parser.add_argument('command', nargs=argparse.REMAINDER,
                        help="An optional command, if blank we drop into interactive mode")
    options = parser.parse_args()

    shell = HurricaneDNSShell(options.username, options.password)
    try:
        if not options.command:
            if stdin.isatty():
                shell.cmdloop()
            else:
                for line in stdin.readlines():
                    shell.onecmd(line)
        else:
            from pipes import quote
            shell.onecmd(" ".join(map(lambda x: quote(x), options.command)))
    except HurricaneDNS.HurricaneAuthenticationError as e:
        print '%s: HE sent an error (%s)' % (parser.prog, e)
        exit(1)
    except HurricaneDNS.HurricaneError as e:
        print '%s: %s' % (parser.prog, e)


if __name__ == '__main__':
    main()
