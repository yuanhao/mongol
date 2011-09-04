# -*- coding: utf-8 -j*-
# Author: Yuanhao Li <jay_21cn [at] hotmail [dot] com>


import re
from datetime import datetime

from pymongo.objectid import ObjectId


__all__ = ['Length', 'NumberRange', 'Regexp', 'Email', 'IPAdress', 'URL',
    'String', 'Integer', 'ObjectIdValidator', 'Boolean', 'Float', 'GeoPt',
    'DateTime', 'DocumentValidator', 'EmbeddedDocumentValidator', 
    'ValidationError']


class ValidationError(ValueError):
    pass


class Validator(object):
    pass


class Boolean(Validator):
    def __call__(self, value):
        if not isinstance(value, bool):
            raise ValidationError('The value must be a boolean')


class String(Validator):
    """validates if the value is a string
    """
    def __call__(self, value):
        if not isinstance(value, basestring):
            raise ValidationError('The value must be a string')


class Integer(Validator):
    def __call__(self, value):
        if not isinstance(value, (int, long)):
            raise ValidationError('The value must be a integer')


class Float(Validator):
    def __call__(self, value):
        if not isinstance(value, float):
            raise ValidationError('The value must be a float number')


class Length(Validator):
    """validates length of string
    """
    def __init__(self, min=-1, max=-1):
        assert min != -1 or max != -1
        assert max == -1 or min <= max
        self.min = min
        self.max = max

    def __call__(self, value):
        x = value and len(value) or 0
        if x < self.min or self.max != -1 and x > self.max:
            if self.min == -1:
                error = 'String value is too long'
            elif self.max == -1:
                error = 'String value is too short'
            else:
                error = 'String value length must between %d and %d' % (
                    self.min, self.max)
            raise ValidationError(error)


class NumberRange(Validator):
    """ validates that a number must be in a range from `min` to `max`
    """
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def __call__(self, value):
        if value is None or (self.min is not None and value < self.min) or \
            (self.max is not None and value > self.max):
            if self.max is None:
                error = 'Number must be greater than %s' % self.min
            elif self.min is None:
                error = 'Number must be less than %s' % self.max
            else:
                error = 'Number must be between %s and %s' % (self.min, self.max)
            raise ValidationError(error)


class Regexp(Validator):
    def __init__(self, regex, flags):
        if isinstance(regex, basestring):
            regex = re.compile(regex, flags)
        self.regex = regex

    def __call__(self, value):
        if not self.regex.match(value or u''):
            raise ValidationError('Invalid string value')


class Email(Regexp):
    def __init__(self):
        super(Email, self).__init__(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE)

    def __call__(self, value):
        try:
            super(Email, self).__call__(value)
        except ValidationError:
            raise ValidationError('Invalid email address')


class IPAdress(Regexp):
    def __init__(self):
        super(IPAdress, self).__init__(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$', re.IGNORECASE)

    def __call__(self, value):
        try:
            super(IPAdress, self).__call__(value)
        except ValidationError:
            raise ValidationError('Invalid IP address')


class URL(Regexp):
    def __init__(self, require_tld=True):
        tld_part = (require_tld and ur'\.[a-z]{2,10}' or u'')
        regex = ur'^[a-z]+://([^/:]+%s|([0-9]{1,3}\.){3}[0-9]{1,3})(:[0-9]+)?(\/.*)?$' % tld_part
        super(URL, self).__init__(regex, re.IGNORECASE)

    def __call__(self, value):
        try:
            super(URL, self).__call__(value)
        except ValidationError:
            raise ValidationError('Invalid URL')


class ObjectIdValidator(Validator):
    def __call__(self, value):
        try:
            ObjectId(unicode(value))
        except:
            raise ValidationError('Invalid Object ID')


class GeoPt(Validator):
    def __call__(self, value):
        if not isinstance(value, (tuple, list)):
            raise ValidationError('GeoPt can only hold a tuple or list of (x, y) ')

        if len(value) <> 2:
            raise ValidationError('GeoPt must have exactly two elements (x, y) ')


class DateTime(Validator):
    def __call__(self, value):
        if callable(value):
            value = value()
        if not isinstance(value, datetime):
            raise ValidationError('Invalid datetime type')


class DocumentValidator(Validator):
    def __call__(self, value):
        from document import Document
        if not isinstance(value, Document):
            raise ValidationError('Invalid Document type')


class EmbeddedDocumentValidator(Validator):
    def __call__(self, value):
        from document import EmbedDocument
        if not isinstance(value, EmbedDocument):
            raise ValidationError('Invalid Document type')
        if value._id is not None:
            raise ValidationError('A Embed Document should not have a ID')


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


