"""
Hurricane Electric DNS library module

Inspired by EveryDNS Python library by Scott Yang:
	http://svn.fucoder.com/fucoder/pyeverydns/everydnslib.py
"""
__version__ = '0.1'

import cookielib
import re
import urllib
import urllib2

HTTP_USER_AGENT = 'PyHurriceDNS/%s' % __version__
HTTP_REQUEST_PATH = 'https://dns.he.net/index.cgi'

class HurricaneError(Exception):
	pass

class HurricaneDNS(object):
	def __init__(self, username, password):
		self.__username = username
		self.__password = password
		self.__account = None
		self.__cookie = cookielib.CookieJar()
		self.__opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.__cookie))
		self.__opener.addheaders = [
			('User-Agent', HTTP_USER_AGENT),
		]
		
		self.__domains = {}
	
	def add_domain(self, domain, master=None, method=None):
		domain = domain.lower();
		data = {
			'retmain': 0,
			'submit': 1
		}
		
		if master and method:
			raise HurricaneError('Domain "%s" can not be both secondary and reverse' % domain)
		
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
			data['add_recerse'] = domain
			data['method'] = method
		else:
			data['add_domain'] = domain
			data['action'] = 'add_zone'
			
		self.__process(data)
		# HACK: Instead we should just add the domain
		self.__domains = None		
	
	def __add_or_edit_record(self, domain, record_id, host, rtype, value, mx, ttl):
		domain = domain.lower()
		d = self.get_domain(domain)
		
		if d['type'] == 'slave':
			raise HurricaneError('Domain "%s" is a slave zone, this is a bad idea!' % domain)
			
		res = self.__process({
			'account': '', #self.__account,
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

		if 'id="dns_status"' not in res:
			raise HurricaneError('Record "%s" (%s) not added or modified for domain "%s"' % (host, rtype, domain))
		# HACK: Be better to invalidate a single record...
		d['records'] = None
		
	def edit_record(self, domain, host, rtype, old_value=None, old_mx=None, old_ttl=None, value=None, mx=None, ttl=None):
		if value == None and ttl == None and not (rtype == 'MX' and mx != None):
			raise HurricaneError('You must specify one or more of value, ttl or mx priority')
			
		record = list(self.get_records(domain, host, rtype, old_value, old_mx, old_ttl))
		if len(record) > 1:
			raise HurricaneError('Criteria matches multiple records, please be more specific')
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
			raise HurricaneError('Domain "%s" is a slave zone, this is a bad idea!' % domain)
			
		res = self.__process({
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
			raise HurricaneError('Domain "%s" is a slave zone, this is a bad idea!' % domain)
		
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
		domains = self.cache_domains()
		for d in self.cache_domains():
			if d['domain'] == domain:
				return d

		raise HurricaneError('Domain "%s" does not exist' % domain)
			
	def cache_domains(self):
		if not self.__domains:
			self.__domains = self.list_domains()
		return self.__domains
		
	def list_domains(self):
		self.login()
		res = self.__process()
		all = re.findall(r'(?:menu=edit_([^&"]+)|menu="edit_(reverse)").*?onclick="delete_dom\(this\);" name="([^"]+)" value="([^"]+)', res, re.M | re.S)
		domains = {}
		for d in all:
			if d[2] in domains:
				if d[1] == 'reverse' and domains[d[2]]['type'] == 'zone':
					domains[d[2]]['type'] = 'reverse'
				continue			
			domains[d[2]] = {
				'domain': d[2],
				'id': d[3],
				'type': d[1] if len(d[1]) != 0 else d[0],
				'records': None
			}

		return domains.values()
		
	def get_record(self, domain, record_id):
		records = self.cache_records(domain)
		for r in records:
			if r['id'] == record_id:
				return r
		raise HurricaneError('Record %s does not exist for domain "%s"' % (record_id, domain))
		
	def get_records(self, domain, host, rtype=None, value=None, mx=None, ttl=None):
		records = self.cache_records(domain)
		results = []
		for r in records:
			if (r['host'] == host and
			   (rtype == None or r['type'] == rtype) and
			   (value == None or r['value'] == value) and
			   (mx == None or r['mx'] == mx) and
			   (ttl == None or r['ttl'] == ttl)):
					results.append(r)
		return results
		
	def cache_records(self, domain):
		d = self.get_domain(domain)
		if not d['records']:
			d['records'] = self.list_records(domain)
		return d['records']
		
	def list_records(self, domain):
		self.login()
		d = self.get_domain(domain)
		if d['type'] in ('zone', 'reverse'):
			res = self.__process({
				'hosted_dns_zoneid': d['id'],
				'menu': 'edit_zone',
				'hosted_dns_editzone': ''
			})
			
			all = re.findall(r'<tr class="dns_tr(?:_([^"]*))?"[^>]*>' + '\s+<td[^>]+>([^<]+)</td>' * 3 +
			                 '\s+<td[^>]+><img[^>]+data="([^"]+)"[^>]+></td>' +
			                 '\s+<td[^>]+>([^<]+)</td>' * 3, res)
			records = [{
					'id': r[2],
					'status': r[0],
					'host': r[3],
					'type': r[4],
					'ttl': r[5],
					'mx': r[6],
					'value': r[7]
				} for r in all]
		elif d['type'] == 'slave':
			res = self.__process({
				'domid': d['id'],
				'menu': 'edit_slave',
				'action': 'edit'
			})
			
			all = re.findall(r'<tr class="dns_tr" id="([^"]+)"[^>]*>' +
			                 '\s+<td[^>]+>([^<]+)</td>' * 5, res)
			records = [{
					'id': r[0],
					'status': 'locked',
					'host': r[1],
					'type': r[2],
					'ttl': r[3],
					'mx': r[4],
					'value': r[5]
				} for r in all]
		return records
		
	def login(self):
		# Are we already logged in?
		if self.__account != None:
			return True
		
		# Get our CGISESSID cookie
		self.__process()
		
		# submit the login form
		res = self.__process({
			'email': self.__username,
			'pass': self.__password,
			'submit': 'Login!'
		})
		
		account = re.search(r'name="account" value="([^"]+)"', res)
		if account:
			self.__account =  account.group(1)
		else:
			raise HurricaneError('Account not found')
			
		return True

	def __process(self, data=None):
		if isinstance(data, dict) or isinstance(data, list):
			data = urllib.urlencode(data)
		
		res = self.__opener.open(HTTP_REQUEST_PATH, data)
		res = res.read()
		
		if __debug__:
			print '%s' % str(data)
		
		if 'id="dns_err"' in res:
			msg = re.search(r'id="dns_err"[^>]*>([^<]*)', res)
			if msg:
				raise HurricaneError(msg.group(1))
			else:
				raise HurricaneError('Unknown error')
		else:
			return res
