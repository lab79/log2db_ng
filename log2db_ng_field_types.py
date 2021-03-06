#!/usr/local/bin/python -Wignore::DeprecationWarning
# -*- coding: utf-8 -*-

import re
import urllib
import urlparse
import math
import os

import geoip2.database
import geoip2.errors

geoip_city = geoip2.database.Reader('/usr/local/share/GeoIP/GeoIP2-City.mmdb') 
geoip_conn_type = geoip2.database.Reader('/usr/local/share/GeoIP/GeoIP2-Connection-Type.mmdb')
geoip_isp = geoip2.database.Reader('/usr/local/share/GeoIP/GeoIP2-ISP.mmdb')
# geoip_asn = geoip2.database.Reader('/usr/local/share/GeoIP/GeoLite2-ASN.mmdb')
# geoip_isp = geoip2.database.Reader('/usr/local/share/GeoIP/GeoIPISP.dat')

class LogField(object):
    def __init__(self, value, *args, **kwargs):
        self.value = value

        super(LogField, self).__init__(*args, **kwargs)

    def clean(self):
        return self.value

class IPv4Field(LogField):
    def clean(self):
        assert re.match('([0-2]?([0-5]|(?<![2-9])[0-9])?([0-5]|(?<!25)[0-9])\.){4}', self.value + '.')
        return self.value

# GeoIP2-City.mmdb
class GeoIP2CityDBField(IPv4Field):
    db = None
    ip = None
    def __init__(self, value, *args, **kwargs):
        super(GeoIP2CityDBField, self).__init__(value, *args, **kwargs)
    def clean(self):
        self.value = super(GeoIP2CityDBField, self).clean()
        if self.ip != self.value:
            try:
                GeoIP2CityDBField.db = geoip_city.city(self.value)
            except geoip2.errors.AddressNotFoundError:
                GeoIP2CityDBField.db = None
            GeoIP2CityDBField.ip = self.value

# GeoIP2-ISP.mmdb
class GeoIP2IspDBField(IPv4Field):
    db = None
    ip = None
    def __init__(self, value, *args, **kwargs):
        super(GeoIP2IspDBField, self).__init__(value, *args, **kwargs)
    def clean(self):
        self.value = super(GeoIP2IspDBField, self).clean()
        if self.ip != self.value:
            try:
                GeoIP2IspDBField.db = geoip_isp.isp(self.value)
            except geoip2.errors.AddressNotFoundError:
                GeoIP2IspDBField.db = None
            GeoIP2IspDBField.ip = self.value

class GeoIP2IspDBIspField(GeoIP2IspDBField):
    def clean(self):
        self.value = super(GeoIP2IspDBIspField, self).clean()
        try:
            return self.db.isp # autonomous_system_organization
        except:
            return ''

class GeoIP2IspDBAsnField(GeoIP2IspDBField):
    def clean(self):
        self.value = super(GeoIP2IspDBAsnField, self).clean()
        try:
            return self.db.autonomous_system_number # autonomous_system_organization
        except:
            return 0

# GeoIP2-Connection-Type.mmdb
class GeoIP2ConnTypeDBField(IPv4Field):
    ip = None
    def __init__(self, value, *args, **kwargs):
        super(GeoIP2ConnTypeDBField, self).__init__(value, *args, **kwargs)
    def clean(self):
        self.value = super(GeoIP2ConnTypeDBField, self).clean()
        if self.ip != self.value:
            try:
                return geoip_conn_type.connection_type(self.value).connection_type
            except geoip2.errors.AddressNotFoundError:
                return ''
            GeoIP2ConnTypeDBField.ip = self.value

# class GeoIP2AsnDBField(IPv4Field):
#     ip = None
#     def __init__(self, value, *args, **kwargs):
#         super(GeoIP2AsnDBField, self).__init__(value, *args, **kwargs)
#     def clean(self):
#         self.value = super(GeoIP2AsnDBField, self).clean()
#         if self.ip != self.value:
#             try:
#                 return geoip_conn_type.asn(self.value).autonomous_system_number
#             except geoip2.errors.AddressNotFoundError:
#                 return 0


class GeoIP2CityDBCityField(GeoIP2CityDBField):
    def clean(self):
        self.value = super(GeoIP2CityDBCityField, self).clean()

        try:
            return  { \
                        'id':       self.db.city.geoname_id, \
                        'title':    self.db.city.names['en'] if 'en' in self.db.city.names else None, \
                        'title_ru': self.db.city.names['ru'] if 'ru' in self.db.city.names else None, \
                    }
        except:
            return ''

class GeoIP2CityDBRegionField(GeoIP2CityDBField):
    def clean(self):
        self.value = super(GeoIP2CityDBRegionField, self).clean()

        try:
            return  { \
                        'id':       self.db.subdivisions[0].geoname_id, \
                        'iso_code': self.db.subdivisions[0].iso_code, \
                        'title':    self.db.subdivisions[0].names['en'] if 'en' in self.db.subdivisions[0].names else None, \
                        'title_ru': self.db.subdivisions[0].names['ru'] if 'ru' in self.db.subdivisions[0].names else None, \
                    }
        except:
            return ''

class GeoIP2CityDBCountryField(GeoIP2CityDBField):
    def clean(self):
        self.value = super(GeoIP2CityDBCountryField, self).clean()

        try:
            return  { \
                        'id':       self.db.country.geoname_id, \
                        'iso_code': self.db.country.iso_code, \
                        'title':    self.db.country.names['en'] if 'en' in self.db.country.names else None, \
                        'title_ru': self.db.country.names['ru'] if 'ru' in self.db.country.names else None, \
                    }
        except:
            return ''


class IntField(LogField):
    def clean(self):
        if isinstance(self.value, basestring):
            if len(self.value) == 0:
                return None
        return int(self.value)

class FloatField(LogField):
    def clean(self):
        if isinstance(self.value, basestring):
            if len(self.value) == 0:
                return None

        res = float(self.value)
        if math.isnan(res):
            return None
        if math.isinf(res):
            return None
        return res
 
class NullableField(LogField):
    def clean(self):
        if isinstance(self.value, basestring):
            if self.value.lower() == 'undefined':
                return None
        return self.value

class EscapedField(LogField):
    def clean(self):
        return self.value.encode('string-escape') 

class MultiLineField(LogField):
    def clean(self):
        return ''.join(self.value.splitlines())

class URLDecodedField(LogField):
    def clean(self):
        return urllib.unquote(self.value).decode('utf8', 'replace').encode('utf8')

class RecursiveField(LogField):
    def clean(self):
        action_value = self.field_class(self.value).clean()

        if self.value == action_value:
            return self.value

        self.value = action_value
        
        return self.clean() 

def RecursiveFieldType(field_class):
    res = RecursiveField
    res.field_class = field_class

    return res

class RegexpField(LogField):
    def clean(self):
        assert re.match(self.regexp, self.value)

        return self.value

class LowerField(LogField):
    def clean(self):
        return self.value.lower()


def LimitedLengthFieldType(length_limit):
    res = LimitedLengthField
    res.length_limit = length_limit

    return res

class LimitedLengthField(LogField):
    def clean(self):
        return self.value[:self.length_limit]

class MultiTraitField(LogField):
    def clean(self):
        for base_class in type(self).__bases__:
            if base_class != MultiTraitField:
                self.value = base_class(self.value).clean()
                if self.value is None:
                    return self.value

        return self.value

class GUIDField(RegexpField):
    regexp = '(?i)[0-9a-f]{8}-?([0-9a-f]{4}-?){3}[0-9a-f]{12}'

class LogGUIDField(MultiTraitField, NullableField, GUIDField, LowerField):
    pass

class LogFloatField(MultiTraitField, NullableField, FloatField):
    pass

class LogCharField(MultiTraitField, NullableField, RecursiveFieldType(URLDecodedField)):
    pass

class TimestampField(MultiTraitField, FloatField, IntField):
    pass


class RefererField(MultiTraitField, RecursiveFieldType(URLDecodedField), EscapedField, LimitedLengthFieldType(1024)):
    def clean(self):
        super(RefererField, self).clean()

        o = urlparse.urlsplit(self.value)

        if len(o.scheme) == 0:
            o = urlparse.urlsplit('undef://%s' % self.value)

        hostname = o.hostname or ''

        return  { \
                    'scheme':   o.scheme, \
                    'netloc':   hostname, \
                    'colten':   '.'.join(reversed(hostname.split('.'))), \
                    'path':     o.path, \
                    'query':    urlparse.parse_qs(o.query), \
                    'site':     '.'.join(hostname.split('.')[-2:]), \
                }   

# с дополнительным реферером из dl
class RefererNestingField(MultiTraitField, RecursiveFieldType(URLDecodedField), EscapedField, LimitedLengthFieldType(1024)):
    def clean(self):
        super(RefererNestingField, self).clean()

        o = urlparse.urlsplit(self.value)

        if len(o.scheme) == 0:
            o = urlparse.urlsplit('undef://%s' % self.value)

        hostname = o.hostname or ''
        ref = None
        if len(o.query)>0:
            q = urlparse.parse_qs(o.query)
            if len(q)>0:
                ref_dl = q.get('dl')
                if ref_dl and len(ref_dl)>0:
                    ref = RefererField(ref_dl[0]).clean()
            return  { \
                        'scheme':   o.scheme, \
                        'netloc':   hostname, \
                        'colten':   '.'.join(reversed(hostname.split('.'))), \
                        'path':     o.path, \
                        'query':    q, \
                        'site':     '.'.join(hostname.split('.')[-2:]), \
                        'ref':	ref, \
                    } 

# с выделением файла и расширения /hls-vod/knllw1laxhdhbf3qmiztfq/1491700172/124/0x500003970b8829ca/5b8aefaf3df14ea8ab5e375cb187868c.mp4.m3u8
class RefererWithFileField(MultiTraitField, RecursiveFieldType(URLDecodedField), EscapedField, LimitedLengthFieldType(1024)):
    def clean(self):
        super(RefererWithFileField, self).clean()

        o = urlparse.urlsplit(self.value)

        if len(o.scheme) == 0:
            o = urlparse.urlsplit('undef://%s' % self.value)

        hostname = o.hostname or ''

        dirname = '' # basename = ''
        filename = ''
        fileext = ''
        if len(o.path)>1:
            dirname, basename = os.path.split(o.path) # filename = o.path.split('/')[-1]
            if len(basename)>2:
                filename, fileext = os.path.splitext(basename)
            else:
                filename = basename


        return  { \
                    'scheme':   o.scheme, \
                    'netloc':   hostname, \
                    'colten':   '.'.join(reversed(hostname.split('.'))), \
                    'dirname':     dirname, \
                    'filename': filename,\
                    'fileext': fileext,\
                    'query':    urlparse.parse_qs(o.query), \
                    'site':     '.'.join(hostname.split('.')[-2:]), \
                }  


def ErrorFieldType(error_type):
    res = ErrorField
    res.error_type = error_type
    return res

class ErrorField(MultiTraitField, RecursiveFieldType(URLDecodedField), EscapedField):
    def clean(self):
        super(ErrorField, self).clean()

        res = {}
        res['name'] = self.error_type

        if self.value.isdigit():
            res['code'] = int(self.value)
        else:
            field_parts = self.value.split(',', 1) # re.split('[,]', self.value)
            if len(field_parts)==1:
                field_parts = self.value.split('%2C', 1)
            if len(field_parts)==1:
                field_parts = self.value.split('_', 1)

            try:
                if len(field_parts)==2:
                    res['code'] = int(field_parts[0])
                    res['msg'] = field_parts[1]
                else:
                    res['msg'] = self.value
            except:
                res['msg'] = self.value

        return res

class UserAgentField(MultiTraitField, URLDecodedField, EscapedField, LimitedLengthFieldType(1024)):
    pass
