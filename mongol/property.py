# -*- coding: utf-8 -*-
#
# Author: Yuanhao Li <jay_21cn [at] hotmail [dot] com>


from copy import deepcopy

from pymongo.objectid import ObjectId
from pymongo.dbref import DBRef
from validator import *


class Property(object):
    def __init__(self, value=None, default=None, required=False, unique=False, validators=None):
        self._value = value
        self.required = required
        self.unique = unique
        self.default = default
        self._validators = validators or []
        self._field_name = None
        self._document_class = None

    def __get__(self, obj, cls):
        if obj is None:
            return self

        value = obj[self._field_name]
        return value

    def __set__(self, obj, value):
        self._value = value
        obj[self._field_name] = value

    def attach(self, cls, name):
        self._document_class = cls
        self._field_name = name

    def make_value_from_mongo(self, value):
        return value

    def get_value_for_mongo(self, value):
        return value

    def validate(self, value):
        if value:
            [v(value) for v in self._validators]
        else:
            # print 'Value is not set'
            pass

    def default_value(self):
        if callable(self.default):
            return self.default()
        return self.default


class BooleanProperty(Property):
    def __init__(self, *args, **kw):
        if kw.get('default') is None:
            kw['default'] = False
        super(BooleanProperty, self).__init__(*args, **kw)
        self._validators.append(Boolean())


class StringProperty(Property):
    def __init__(self, *args, **kw):
        if kw.get('default') is None:
            kw['default'] = u''
        super(StringProperty, self).__init__(*args, **kw)
        self._validators.append(String())

    # def make_value_from_mongo(self, value):
        # return super(StringProperty, self).make_value_from_mongo(unicode(value))


class EmailProperty(StringProperty):
    def __init__(self, *args, **kw):
        super(EmailProperty, self).__init__(*args, **kw)
        self._validators.append(Email())


class IPAdressProperty(StringProperty):
    def __init__(self, *args, **kw):
        super(IPAdressProperty, self).__init__(*args, **kw)
        self._validators.append(IPAdress())


class URLProperty(StringProperty):
    def __init__(self, *args, **kw):
        require_tld = kw.pop('require_tld', True)
        super(URLProperty, self).__init__(*args, **kw)
        self._validators.append(URL(require_tld=require_tld))


class IntegerProperty(Property):
    def __init__(self, *args, **kw):
        if kw.get('default') is None:
            kw['default'] = 0
        super(IntegerProperty, self).__init__(*args, **kw)
        self._validators.append(Integer())

    # def make_value_from_mongo(self, value):
        # return super(IntegerProperty, self).make_value_from_mongo(int(value))


class ObjectIdProperty(Property):
    def __init__(self, *args, **kw):
        super(ObjectIdProperty, self).__init__(*args, **kw)
        self._validators.append(ObjectIdValidator())

    # def get_value_for_mongo(self, value):
        # if not isinstance(value, ObjectId):
            # return ObjectId(unicode(value))
        # return value


class FloatProperty(Property):
    def __init__(self, *args, **kw):
        if kw.get('default') is None:
            kw['default'] = 0.0
        super(FloatProperty, self).__init__(*args, **kw)
        self._validators.append(Float())

    # def make_value_from_mongo(self, value):
        # return float(value)


class GeoPtProperty(Property):
    def __init__(self, *args, **kw):
        super(GeoPtProperty, self).__init__(*args, **kw)
        self._validators.append(GeoPt())


class DateTimeProperty(Property):
    def __init__(self, *args, **kw):
        self.auto_now = kw.pop('auto_now', False)
        self.auto_now_add = kw.pop('auto_now_add', False)
        # XXX, TODO
        super(DateTimeProperty, self).__init__(*args, **kw)
        self._validators.append(DateTime())


class ReferenceProperty(Property):
    def __init__(self, reference_class, *args,**kw):
        super(ReferenceProperty, self).__init__(*args, **kw)
        self._reference_class = reference_class
        self._validators.append(DocumentValidator())

    def __get__(self, obj, cls):
        if obj is None:
            return self

        if self._field_name not in obj.__documents_cache__.keys():
            value = obj.get(self._field_name)
            print 'XDSxdfa'
            print value
            if value:
                value = self._reference_class.from_raw_data(
                    **(self._reference_class.m.db.dereference(value)))
                obj.__documents_cache__[self._field_name] = value
            else:
                return None
        # XXX
        value = obj.__documents_cache__[self._field_name]
        if isinstance(value, DBRef):
            value =self._reference_class.from_raw_data(
                **(self._reference_class.m.db.dereference(value)))
            obj.__documents_cache__[self._field_name] = value
        return obj.__documents_cache__[self._field_name]

    def __set__(self, obj, value):
        obj.__documents_cache__[self._field_name] = value

    def save(self, obj):
        doc = obj.__documents_cache__[self._field_name]
        if doc._id is None:
            doc.save()
        collection_name = doc.__collection_name__
        db_name = doc.m.db.name # if has a database name argument can support across database
        obj[self._field_name] = DBRef(collection_name, doc.id, db_name)


class BinaryProperty(Property):
    pass


class DictProperty(Property):
    def make_value_from_mongo(self, value):
        return _AttrDict(value)


class ListProperty(Property):
    def __init__(self, *args, **kw):
        self._item_type = kw.pop('item_type', None)
        super(ListProperty, self).__init__(*args, **kw)

    def make_value_from_mongo(self, value):
        return _AttrList(value, self._item_type)


class EmbedDocumentProperty(Property):
    def __init__(self, doc_cls, *args, **kw):
        super(EmbedDocumentProperty, self).__init__(*args, **kw)
        self._document_class = doc_cls
        self._validators.append(EmbeddedDocumentValidator())

    def __get__(self, obj, cls):
        if obj is None:
            return self

        if self._field_name not in obj.__documents_cache__.keys():
            try:
                value = obj[self._field_name]
                value = self._document_class.from_raw_data(**value)
                obj.__documents_cache__[self._field_name] = value
            except KeyError:
                return None

        value = obj.__documents_cache__[self._field_name]
        if isinstance(value, dict):
            value = self._document_class.from_raw_data(**value)
            obj.__documents_cache__[self._field_name] = value
        return obj.__documents_cache__[self._field_name]

    def __set__(self, obj, value):
        super(EmbedDocumentProperty, self).__set__(obj, value)
        obj.__documents_cache__[self._field_name] = value

    def save(self, obj):
        obj[self._field_name].save()


def _transform(value, value_type=None):
    #XXX
    if value_type:
        return prop_cls(value)
    if isinstance(value, dict):
        return _AttrDict(value)
    if isinstance(value, list):
        return _AttrList(value, value_type)
    return value


# class _EmbedDocument(object):
    # def __init__(self, doc):
        # self._document = doc

    # def __repr__(self):
        # return '<Embed Document %s >' % dict.__repr__(self._document)

    # def __getitem__(self, name):
        # return self._document[name]

    # def __setitem__(self, name, value):
        # self._document[name] = value

    # def __getattr__(self, name):
        # return self._document.__getattr__(name)

    # def __setattr__(self, name, value):
        # if name == '_document':
            # self.__dict__[name] = value
        # else:
            # self._document.__setattr__(name, value)

    # def __delitem__(self, name):
        # self._document.__delitem__(name)

    # def __eq__(self, doc):
        # if isinstance(doc, EmbedDocument):
            # return self._document == doc._document
        # else:
            # return self._document == doc

    # def __ne__(self, doc):
        # return not self.__eq__(doc)

    # def __iter__(self):
        # return self._document.__iter__()

    # def iteritems(self):
        # for key, value in self._document.iteritems():
            # yield (key, value)


class _AttrDict(object):
    def __init__(self, d):
        self._data = d

    def __repr__(self):
        return self._data.__repr__()

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __setitem__(self, name, value):
        self._data[name] = value

    def __getattr__(self, name):
        return _transform(self._data[name])

    def __setattr__(self, name, value):
        if name == '_data':
            self.__dict__[name] = value
        else:
            self._data[name] = value

    def __delattr__(self, name):
        self._data.__delitem__(name)

    def __eq__(self, d):
        if isinstance(d, _AttrDict):
            return self._data == d._data
        else:
            return self._data == d

    def __ne__(self, d):
        return not self.__eq__(d)

    def __iter__(self):
        return self._data.__iter__()

    def iteritems(self):
        for key, value in self._data.iteritems():
            yield (key, _transform(value))


class _AttrList(object):
    def __init__(self, l, value_type):
        self._data = l
        self._value_type = value_type

    def __getitem__(self, index):
        return _transform(self._data[index])

    def __eq__(self, l):
        if isinstance(l, _AttrList):
            return self._data == l._data
        else:
            return self._data == l

    def __ne__(self, l):
        return not self.__eq__(l)


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


