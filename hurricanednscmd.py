#!/usr/bin/env python
"""EveryDNS Command Line tools/shell"""

__version__ = '0.1'

import cmd
import os
import re
import sys

import HurricaneDNS as everydnslib
everydnslib.EveryDNS = everydnslib.HurricaneDNS
everydnslib.LoginFailed = everydnslib.HurricaneError


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


class EveryDNSShell(cmd.Cmd):
    def __init__(self, username, password):
        cmd.Cmd.__init__(self)
        self.__username = username
        self.__password = password
        self.__edns = None
        self._make_prompt()

    def default(self, line):
        self._do_error('command not found')

    def do_add(self, args):
        """!NAME
        add - Add a domain/record

        !SYNOPSIS
        add domain [domain option]
        add domain host type value [mx] [ttl]

        !DESCRIPTION
        Add either a domain or a host record to EveryDNS. If the number of
        arguments is 1 or 2, it will add the domain in arg 1, and then use arg
        2 as option. If the number of arguments is between 4 and 6, it will
        add the host record with optional MX and TTL.

        """
        args = split_args(args)
        if len(args) < 3:
            domain = args[0]
            extra = {}
            if len(args) == 2:
                if args[1] == 'dynamic':
                    extra['dynamic'] = True
                elif args[1].startswith('secondary='):
                    extra['secondary'] = args[1][10:]
                elif args[1].startswith('webhop='):
                    extra['webhop'] = args[1][7:]
            self._get_edns().add_domain(domain, **extra)
        elif 6 >= len(args) >= 4:
            self._get_edns().add_record(*args)
        else:
            self._do_error('Invalid arguments')

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
        if len(args) == 1:
            self._get_edns().del_domain(args[0])
        elif len(args) > 1:
            self._get_edns().del_records(*args)

    def do_EOF(self, args):
        print
        return 1

    def do_exit(self, args):
        return 1

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
            existing = self._get_edns().cache_domains()
            existing = set([item['domain'] for item in existing])
            records = []
            for domain in split_args(args):
                if domain.lower() not in existing:
                    self._do_error('Invalid domain: ' + domain)
                    continue
                records.extend(self._get_edns().cache_records(domain))

            if records:
                maxhost = max([len(item['host']) for item in records])
                maxvalue = max([len(item['value']) for item in records])
                template = '%%%ds %%-5s %%-%ds %%2s %%6s' % (maxhost, maxvalue)
                print template % ('HOST', 'TYPE', 'VALUE', 'TTL', 'MX')
                for record in records:
                    print template % (record['host'], record['type'],
                        record['value'], record['ttl'], record['mx'])
        else:
            domains = self._get_edns().cache_domains()
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
        print 'ednssh: %s: %s' % (command, errmsg)

    def _get_edns(self):
        if not self.__edns:
            self.__edns = everydnslib.EveryDNS(self.__username,
                self.__password)
        return self.__edns

    def _make_prompt(self):
        self.prompt = '[%s@everydns] ' % self.__username

    def cmdloop(self):
        try:
            cmd.Cmd.cmdloop(self)
        except KeyboardInterrupt:
            print
            self.cmdloop()


def main():
    myname = os.path.basename(sys.argv[0])
    if len(sys.argv) == 3:
        try:
            shell = EveryDNSShell(sys.argv[1], sys.argv[2])
            shell.cmdloop()
        except everydnslib.LoginFailed:
            print '%s: Invalid username/password' % myname
            sys.exit(1)
    else:
        print 'Usage: %s [username] [password]' % myname


def split_args(args):
    args = re.findall(
        '"([^"]*?)"(?:\s|$)' + '|' + # double-quoted
        "'([^']*?)'(?:\s|$)" + '|' + # single-quoted
        '([^\s]+)(?:\s|$)',          # unquoted
        args.strip())

    result = []
    for arg in args:
        for elm in arg:
            if elm != '':
                result.append(elm)
                break
        else:
            result.append('')
    return result


if __name__ == '__main__':
    main()
