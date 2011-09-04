# -*- coding: utf-8 -*-
#
# Author: Yuanhao Li <jay_21cn [at] hotmail [dot] com>


import logging
from copy import deepcopy

from pymongo.dbref import DBRef

from connection import get_db
from property import Property, ObjectIdProperty, ReferenceProperty
from property import EmbedDocumentProperty
from validator import ValidationError


class DocumentNotSavedError(Exception):
    pass


class DocumentInheritError(Exception):
    pass


class CollectionManager(object):
    def __init__(self, collection_name, doc_cls):
        self._collection_name = collection_name
        self._document_class = doc_cls
        self._db = None

    def _wrap_arguments(self, *args, **kw):
        if self._document_class.__inherit_enabled__:
            extra_spec = { '_classes': self._document_class.__class_name__ }
            if args:
                args[0].update(extra_spec)
            else:
                if 'spec' in kw.keys():
                    kw['spec'].update(extra_spec)
                else:
                    kw['spec'] = extra_spec
        return args, kw

    def all(self):
        args, kw = self._wrap_arguments(spec={})
        return CursorProxy(self._document_class, self.collection.find(*args, **kw))

    def find(self, *args, **kw):
        args, kw = self._wrap_arguments(*args, **kw)
        return CursorProxy(self._document_class, self.collection.find(*args, **kw))

    def find_one(self, *args, **kw):
        args, kw = self._wrap_arguments(*args, **kw)
        result = self.collection.find_one(*args, **kw)
        if not result:
            return None
        return self._document_class(**result)

    @property
    def db(self):
        if not self._db:
            self._db = get_db()
        return self._db

    @property
    def collection(self):
        return self.db[self._collection_name]

    def save(self, doc, **kwargs):
        _id = self.collection.save(doc, **kwargs)
        doc._id = _id

    def __getattr__(self, name):
        return getattr(self.collection, name)


class CursorProxy(object):
    def __init__(self, doc_cls, pymongo_cursor):
        self._doc_cls = doc_cls
        self._pymongo_cursor = pymongo_cursor

    def next(self):
        result = self._pymongo_cursor.next()
        return self._wrap_result(result)

    def _wrap_result(self, result):
        if self._doc_cls.__inherit_enabled__:
            class_name = result.get('_class_name')
            if class_name in self._doc_cls.__super_classes__:
                return self._doc_cls.__super_classes__[class_name].from_raw_data(**result)
            elif class_name in self._doc_cls.__sub_classes__:
                return self._doc_cls.__sub_classes__[class_name].from_raw_data(**result)
        return self._doc_cls.from_raw_data(**result)

    def sort(self, *args, **kwargs):
        self._pymongo_cursor.sort(*args, **kwargs)
        return self

    def __getattr__(self, name):
        return getattr(self._pymongo_cursor, name)

    def __getitem__(self, index):
        result = self._pymongo_cursor.__getitem__(index)

        if isinstance(index, slice):
            return self
        else:
            return self._wrap_result(result)

    def __len__(self):
        return self._pymongo_cursor.count(with_limit_and_skip=True)

    def __iter__(self):
        return self


def _bind_to_superclasses(parent_cls, child_cls):
    if parent_cls.__class_name__ in child_cls.__super_classes__.keys():
        if hasattr(parent_cls, '__sub_classes__'):
            parent_cls.__sub_classes__.update({ child_cls.__class_name__: child_cls })
        else:
            raise Exception('no sub classes')


def _digg_bases(properties, super_classes, base):
    if isinstance(base, DocumentMeta):
        if hasattr(base, '__properties__'):
            # XXX
            if base.__class_name__ == 'EmbedDocument':
                return
            properties.update(deepcopy(base.__properties__))
            super_classes[base.__class_name__] = base
            if base.__super_classes__:
                # super_classes.update(deepcopy(base.__super_classes__))
                super_classes.update(base.__super_classes__)


def _digg_required_or_unique_properties(properties):
    required_properties = {}
    unique_properties = {}
    for k, v in properties.iteritems():
        if v.required:
            required_properties[k] = v
        if v.unique:
            unique_properties[k] = v
            # unique properties are required too
            if k not in required_properties.keys():
                required_properties[k] = v
    return (required_properties, unique_properties)


def _digg_referenced_and_embed_docs(properties):
    embed_docs = {}
    referenced_docs = {}
    for k, v in properties.iteritems():
        if isinstance(v, ReferenceProperty):
            referenced_docs[k] = v
        if isinstance(v, EmbedDocumentProperty):
            embed_docs[k] = v
    return (referenced_docs, embed_docs)


class DocumentMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(DocumentMeta, cls).__new__

        parents = [b for b in bases if isinstance(b, DocumentMeta)]

        if not parents:
            return super_new(cls, name, bases, attrs)

        attrs['__class_name__'] = name

        collection_name = None
        inherit_enabled = False

        for b in bases:
            if hasattr(b, '__collection_name__'):
                collection_name = b.__collection_name__
            if hasattr(b, '__inherit_enabled__'):
                inherit_enabled = b.__inherit_enabled__

        if collection_name:
            attrs['__collection_name__'] = collection_name
        else:
            if '__collection_name__' not in attrs.keys():
                collection_name = name.lower()
                attrs['__collection_name__'] = collection_name
            else:
                collection_name = attrs['__collection_name__']

        properties = {}
        super_classes = {}
        [_digg_bases(properties, super_classes, b) for b in bases]

        for name, attr in attrs.iteritems():
            if isinstance(attr, Property):
                properties[name] = attr

        attrs['__properties__'] = properties
        attrs['__required_properties__'], attrs['__unique_properties__'] = _digg_required_or_unique_properties(properties)
        attrs['__super_classes__'] = super_classes
        attrs['__sub_classes__'] = {}
        attrs['__referenced_documents__'], attrs['__embed_documents__'] = _digg_referenced_and_embed_docs(properties)

        if super_classes:
            if not inherit_enabled:
                raise DocumentInheritError("Document class inherit not enabled")

        new_cls = super_new(cls, name, bases, attrs)
        collection_manager = CollectionManager(collection_name, new_cls)
        setattr(new_cls, '__collection_manager__', collection_manager)
        setattr(new_cls, 'm', collection_manager)
        if hasattr(new_cls, '__properties__'):
            for name, prop in new_cls.__properties__.iteritems():
                prop.attach(new_cls, name)

        [_bind_to_superclasses(s, new_cls) for s in super_classes.values()]

        return new_cls

    def __init__(cls, name, bases, attrs):
        super(DocumentMeta, cls).__init__(name, bases, attrs)

    def __iter__(cls):
        return iter(cls.__properties__)


class Document(dict):
    __metaclass__ = DocumentMeta
    # __collection_name__ = "collection_name"
    __inherit_enabled__ = False
    __expandable__ = False

    # def __new__(cls, *args, **kw):
        # return dict.__new__(cls, *args, **kw)

    def __init__(self, *args, **kw):
        self.__dict__['__documents_cache__'] = dict()

        # the initial value of referenced documents only stored in cache
        for k in self.__referenced_documents__.keys():
            if k in kw.keys():
                v = kw.pop(k)
                self.__documents_cache__[k] = v

        super(Document, self).__init__(*args, **kw)

    def __getattr__(self, name):
        if name in self.__properties__.keys():
            return self.__properties__[name].__get__(self, self.__class__)
        elif name == '_id':
            return None
        else:
            return super(Document, self).__getattribute__(name)

    def __setattr__(self, key, value):
        def _install_property():
            self.__properties__.update({ key: value })
            self.__properties__[key]._field_name = key
            self.__properties__[key]._document_class = self.__class__
            self.__properties__[key].__set__(self, value._value)

        if key in self.__properties__.keys():
            self.__properties__[key].__set__(self, value)
        elif key == '_id':
            if not isinstance(value, ObjectIdProperty):
                value = ObjectIdProperty(value)
            _install_property()
        else:
            if isinstance(value, Property) and self.__expandable__:
                _install_property()

    def __setitem__(self, key, value):
        if key not in self.__properties__.keys():
            if key == '_id' and not isinstance(value, Property):
                self.__setattr__(key, ObjectIdProperty(value))
            else:
                self.__setattr__(key, value)
        else:
            value = self.__properties__[key].get_value_for_mongo(value)
            super(Document, self).__setitem__(key, value)

    def __getitem__(self, key):
        try:
            value = super(Document, self).__getitem__(key)
        except KeyError:
            if key == '_id':
                return None
            value = self.__properties__[key].default_value()

        if isinstance(self.__properties__[key], ReferenceProperty):
            return self.__documents_cache__[key]

        return self.__properties__[key].make_value_from_mongo(value)

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, e:
            raise AttributeError, e

    def __repr__(self):
        return '<Document ' + dict.__repr__(self) + '>'

    def _validate_required_properties(self):
        for k in self.__required_properties__.keys():
            if not self.get(k):
                raise ValidationError('%s is required' % k)

    def _validate_unique_properties(self):
        for k in self.__unique_properties__.keys():
            value = self.get(k)
            if value:
                if self.m.find_one({ k: value }):
                    raise ValidationError('Value %s for %s exist already. ' % (value, k))
            else:
                raise ValidationError('%s is required' % k)

    def validate(self):
        #property validators validate
        [v.validate(self[k]) for k, v in self.__properties__.iteritems()]

        #required properties validate
        self._validate_required_properties()

        #unique properties validate
        self._validate_unique_properties()

    @classmethod
    def from_raw_data(cls, **data):
        return cls(**data)

    @property
    def id(self):
        if not hasattr(self, '_id'):
            raise DocumentNotSavedError
        return self._id

    def _save_children(self):
        [prop.save(self) for prop in self.__referenced_documents__.values()]
        [prop.save(self) for prop in self.__embed_documents__.values()]

    def save(self, *args, **kw):
        #do validate before save into db
        self.validate()

        #save referenced and embed documents at first
        self._save_children()

        if self.__inherit_enabled__:
            classes = self.__super_classes__.keys()
            classes.append(self.__class_name__)
            super(Document, self).__setitem__('_classes', classes)
            super(Document, self).__setitem__('_class_name', self.__class_name__)

        self.m.save(self, *args, **kw)

    def remove(self):
        self.m.remove(self)


class EmbedDocument(Document):
    def __repr__(self):
        return '<Embed Document %s >' % dict.__repr__(self)

    def validate(self):
        #property validators validate
        [v.validate(self[k]) for k, v in self.__properties__.iteritems()]

        #required properties validate
        self._validate_required_properties()

    @property
    def id(self):
        return None

    def save(self, *args, **kw):
        self.validate()
        self._save_children()


# if __name__ == "__main__":
    # from connection import connect
    # from property import *
    # from document import Document
    # from validator import Length
    # connect('test')

    # class TestDocument(Document):
        # __collection_name__ = 'tiny_test'
        # __expandable__ = False
        # __inherit_enabled__ = True

        # title = Property(validators=[Length(min=100)])
        # body = Property()


    # class TestInherit(TestDocument):
        # author = DictProperty()


    # class TestC(TestInherit):
        # tags = ListProperty()


    # class TestD(TestC):
        # more_tags = ListProperty()


    # doc = TestDocument(title="this is title", body="this is body")

    # print doc.title
    # print doc.body

    # doc.title = "changing title"

    # print doc.title
    # print doc['title']

    # doc.band = DictProperty({ 'name': { 'first': 'Yuanhao', 'last': 'Li' } })

    # print doc.band
    # print doc['band']

    # print doc.band.name
    # print doc.band.name.first

    # members = ['Slash', 'Axl Rose', ['A', 'B', 'C'], {'a':1, 'b':2, 'c': ['x', 'y', 'z'] }]

    # print members

    # doc['members'] = ListProperty(members)

    # print doc.members
    # print doc.members[2]
    # print doc.members[2][2]
    # print doc.members[3].a
    # print doc['members'][3].c[2]

    # doc.save()

    # inherited_doc1 = TestInherit(title="Sub document title", author={'name': 'Li'})
    # inherited_doc2 = TestInherit(title="DOC2 OK")

    # print inherited_doc1.__expandable__
    # print inherited_doc1.__collection_name__
    # print inherited_doc1.__class_name__

    # print inherited_doc1.title
    # print inherited_doc1.author.name

    # doc3 = TestC(tags=['a', 'b'])
    # doc4 = TestD(more_tags=['c', 'd'])

    # print doc3.__super_classes__
    # print doc4.__super_classes__
    # print doc.__sub_classes__
    # print inherited_doc1.__sub_classes__
    # print inherited_doc2.__sub_classes__

    # inherited_doc1.save()
    # inherited_doc2.save()
    # doc3.save()

    # print [x for x in TestDocument.m.find()]
    # print [x for x in TestInherit.m.find()]


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


