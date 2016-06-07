"""
Hurricane Electric DNS library module

Inspired by EveryDNS Python library by Scott Yang:
    http://svn.fucoder.com/fucoder/pyeverydns/everydnslib.py
"""
try:
    from http.cookiejar import CookieJar
except ImportError:
    from cookielib import CookieJar

try:
    from urllib.parse import urlencode
    from urllib.request import build_opener, HTTPCookieProcessor
except ImportError:
    from urllib import urlencode
    from urllib2 import build_opener, HTTPCookieProcessor

import pkg_resources
import re
import warnings
import html5lib
import lxml

__version__ = pkg_resources.require("hurricanedns")[0].version
__author__ = "Brian Hartvigsen <brian.andrew@brianandjenny.com>"
__copyright__ = "Copyright 2015, Brian Hartvigsen"
__credits__ = ["Scott Yang", "Brian Hartvigsen"]
__license__ = "MIT"

# Basically we just want to make sure it's here.  We need lxml because
# ElementTree does not support parent relationships in XPath
assert lxml

HTTP_USER_AGENT = 'PyHurriceDNS/%s' % __version__
HTTP_REQUEST_PATH = 'https://dns.he.net/index.cgi'


class HurricaneError(Exception):
    pass


class HurricaneAuthenticationError(HurricaneError):
    pass


class HurricaneBadArgumentError(HurricaneError):
    pass


class HurricaneDNS(object):
    def __init__(self, username, password):
        self.__username = username
        self.__password = password
        self.__account = None
        self.__cookie = CookieJar()
        self.__opener = build_opener(HTTPCookieProcessor(self.__cookie))
        self.__domains = {}

    def add_domain(self, domain, master=None, method=None):
        domain = domain.lower()
        data = {
            'retmain': 0,
            'submit': 1
        }

        if master and method:
            raise HurricaneBadArgumentError('Domain "%s" can not be both slave and reverse' % domain)

        if master:
            if isinstance(master, list) or isinstance(master, tuple):
                i = 1
                for ns in master:
                    data['master%s' % i] = ns
                    i += 1
                    if i == 4:
                        break
            else:
                data['master1'] = master
            data['add_slave'] = domain
            data['action'] = 'add_slave'
        elif method:
            data['add_reverse'] = domain
            data['method'] = method
            data['action'] = 'add_reverse'
        else:
            data['add_domain'] = domain
            data['action'] = 'add_zone'

        try:
            self.__process(data)
        except HurricaneError as e:
            raise HurricaneBadArgumentError(e)
        # HACK: Instead we should just add the domain
        self.__domains = None

    def __add_or_edit_record(self, domain, record_id, host, rtype, value, mx, ttl):
        domain = domain.lower()
        d = self.get_domain(domain)

        if d['type'] == 'slave':
            raise HurricaneBadArgumentError('Domain "%s" is a slave zone, this is a bad idea!' % domain)

        try:
            res = self.__process({
                'account': '',  # self.__account,
                'menu': 'edit_zone',
                'hosted_dns_zoneid': d['id'],
                'hosted_dns_recordid': record_id or '',
                'hosted_dns_editzone': 1,
                'hosted_dns_editrecord': 'Update' if record_id else 'Submit',
                'Name': host.lower(),
                'Type': rtype,
                'Priority': mx or '',
                'Content': value,
                'TTL': ttl
            })
        except HurricaneError as e:
            raise HurricaneBadArgumentError(e)

        if res.find('.//div[@id="dns_err"]') is not None:
            # this should mean duplicate records
            pass
        elif res.find('.//div[@id="dns_status"]') is None:
            raise HurricaneBadArgumentError('Record "%s" (%s) not added or modified for domain "%s"' % (host, rtype, domain))
        # HACK: Be better to invalidate a single record...
        d['records'] = None

    def edit_record(self, domain, host, rtype, old_value=None, old_mx=None, old_ttl=None, value=None, mx=None, ttl=None):
        if value is None and ttl is None and not (rtype == 'MX' and mx is not None):
            raise HurricaneError('You must specify one or more of value, ttl or mx priority')

        record = list(self.get_records(domain, host, rtype, old_value, old_mx, old_ttl))
        if len(record) > 1:
            raise HurricaneBadArgumentError('Criteria matches multiple records, please be more specific')
        else:
            record = record[0]

        if not value:
            value = record['value']
        if (not mx) and rtype == 'MX':
            mx = record['mx']
        if not ttl:
            ttl = record['ttl']

        self.__add_or_edit_record(domain, record['id'], host, rtype, value, mx, ttl)

    def add_record(self, domain, host, rtype, value, mx=None, ttl=86400):
        self.__add_or_edit_record(domain, None, host, rtype, value, mx, ttl)

    def del_record(self, domain, record_id):
        d = self.get_domain(domain.lower())
        if d['type'] == 'slave':
            raise HurricaneBadArgumentError('Domain "%s" is a slave zone, this is a bad idea!' % domain)

        self.__process({
            'hosted_dns_zoneid': d['id'],
            'hosted_dns_recordid': record_id,
            'menu': 'edit_zone',
            'hosted_dns_delconfirm': 'delete',
            'hosted_dns_editzone': 1,
            'hosted_dns_delrecord': 1
        })

        # HACK: Be better to invaldate a single record...
        d['records'] = None

    def del_records(self, domain, host, rtype=None, value=None, mx=None, ttl=None):
        domain = domain.lower()
        d = self.get_domain(domain)
        if d['type'] == 'slave':
            raise HurricaneBadArgumentError('Domain "%s" is a slave zone, this is a bad idea!' % domain)

        for r in self.get_records(domain, host, rtype, value, mx, ttl):
            if r['status'] == 'locked':
                continue
            self.del_record(domain, r['id'])

    def del_domain(self, domain):
        domain = domain.lower()
        self.__process({
            'delete_id': self.get_domain(domain)['id'],
            'account': self.__account,
            'remove_domain': 1
        })
        # HACK: instead we could just remove the one domain
        self.__domains = None

    def get_domain(self, domain):
        domain = domain.lower()
        for d in self.cache_domains():
            if d['domain'] == domain:
                return d

        raise HurricaneBadArgumentError('Domain "%s" does not exist' % domain)

    def cache_domains(self):
        if not self.__domains:
            self.__domains = self.list_domains()
        return self.__domains

    def list_domains(self):
        res = self.__process()
        domains = {}

        the_list = res.findall('.//img[@alt="edit"]')
        the_list += res.findall('.//img[@alt="information"]')
        for d in the_list:
            info = d.findall('./../../td')
            info = info[len(info) - 1].find('img')
            domain_type = 'zone'
            if d.get('menu') is not None:
                domain_type = re.match(r'edit_(.*)', d.get('menu')).group(1)
            else:
                domain_type = re.search(r'menu=edit_([a-z]+)', d.get('onclick')).group(1)

            domains[info.get('name')] = {
                'domain': info.get('name'),
                'id': info.get('value'),
                'type': domain_type,
                'records': None
            }

        return domains.values()

    def get_record(self, domain, record_id):
        records = self.cache_records(domain)
        for r in records:
            if r['id'] == record_id:
                return r
        raise HurricaneBadArgumentError('Record %s does not exist for domain "%s"' % (record_id, domain))

    def get_records(self, domain, host, rtype=None, value=None, mx=None, ttl=None):
        rtype = rtype.lower() if rtype else rtype
        records = self.cache_records(domain)
        results = []
        for r in records:
            if (r['host'] == host and
               (rtype is None or r['type'].lower() == rtype) and
               (value is None or r['value'] == value) and
               (mx is None or r['mx'] == mx) and
               (ttl is None or r['ttl'] == ttl)):
                    results.append(r)
        return results

    def cache_records(self, domain):
        d = self.get_domain(domain)
        if not d['records']:
            d['records'] = self.list_records(domain)
        return d['records']

    def list_records(self, domain):
        d = self.get_domain(domain)
        records = []

        if d['type'] == 'zone':
            res = self.__process({
                'hosted_dns_zoneid': d['id'],
                'menu': 'edit_zone',
                'hosted_dns_editzone': ''
            })

            # Drop the first row as it's actually headers...
            rows = res.findall('.//div[@id="dns_main_content"]/table//tr')[1:]
            for r in rows:
                data = r.findall('td')
                status = re.search(r'dns_tr_(.*)', r.get('class'))
                if status:
                    status = status.group(1)

                records.append({
                    'id': data[1].text,
                    'status': status,
                    'host': data[2].text,
                    'type': data[3].find('img').get('data'),
                    'ttl': data[4].text,
                    'mx': data[5].text,
                    'value': data[6].text,
                    'extended': data[6].get('data')
                })
        elif d['type'] == 'slave':
            res = self.__process({
                'domid': d['id'],
                'menu': 'edit_slave',
                'action': 'edit'
            })

            rows = res.findall('.//tr[@class="dns_tr"]')
            records = [{
                'id': r.get('id'),
                'status': 'locked',
                'host': r.findall('td')[0].text,
                'type': r.findall('td')[1].text,
                'ttl': r.findall('td')[2].text,
                'mx': r.findall('td')[3].text,
                'value': r.findall('td')[4].text
            } for r in rows]
        return records

    def login(self):
        # Are we already logged in?
        if self.__account is not None:
            return True

        # Get our CGISESSID cookie
        self.__process(login=True)

        # submit the login form
        try:
            res = self.__process({
                'email': self.__username,
                'pass': self.__password,
                'submit': 'Login!'
            }, login=True)
        except HurricaneError:
            raise HurricaneAuthenticationError("Invalid Username/Password")

        account = res.find('.//input[@type="hidden"][@name="account"]').get('value')
        if account:
            self.__account = account
        else:
            raise HurricaneAuthenticationError('Login failure')

        return True

    def __process(self, data=None, login=False):
        if not login:
            self.login()
        if isinstance(data, dict) or isinstance(data, list):
            data = urlencode(data).encode("UTF-8")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = html5lib.parse(self.__opener.open(HTTP_REQUEST_PATH, data),
                                 namespaceHTMLElements=False, treebuilder="lxml")

        error = res.find('.//div[@id="content"]/div/div[@id="dns_err"]')

        if error is not None:
            # This is not a real error...
            if 'properly delegated' in error.text:
                pass
            elif 'record already exists' in error.text.lower():
                pass
            else:
                raise HurricaneError(error.text)

        return res
