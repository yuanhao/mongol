# -*- coding: utf-8 -*-
#
# Author: Yuanhao Li <jay_21cn [at] hotmail [dot] com>


import unittest
from datetime import datetime

from mongol.document import Document, DocumentNotSavedError, DocumentInheritError
from mongol.document import EmbedDocument
from mongol.property import *
from mongol.validator import ValidationError
from mongol.connection import db, connect


class PropertyTest(unittest.TestCase):
    def setUp(self):
        self.db = connect('mongoltest')

    def tearDown(self):
        if 'person' in self.db.collection_names():
            self.db.drop_collection('person')

    def test_required_values(self):
        class Person(Document):
            name = StringProperty(required=True)
            age = IntegerProperty(required=True)
            email = EmailProperty()

        person = Person(name="Slash")
        self.assertRaises(ValidationError, person.validate)
        person = Person(age=30)
        self.assertRaises(ValidationError, person.validate)

    def test_unique_value(self):
        class Person(Document):
            userid = StringProperty(unique=True)

        Person(userid='slash').save()
        person = Person(userid='slash')
        self.assertRaises(ValidationError, person.validate)

    def test_objectid_property(self):
        class Person(Document):
            name = StringProperty()

        person = Person(name="Slash")
        self.assertEqual(person._id, None)

        person._id = 47
        self.assertRaises(ValidationError, person.validate)

        person._id = 'abc'
        self.assertRaises(ValidationError, person.validate)

        person._id = '4c98c26624a7264cef000011'
        person.validate()

    def test_string_property(self):
        class Person(Document):
            name = StringProperty()

        person = Person(name=30)
        self.assertRaises(ValidationError, person.validate)

        person = Person(name='hallo')
        person.validate()

        person = Person(name=u'')
        person.validate()

    def test_email_property(self):
        class Person(Document):
            email = EmailProperty()

        person = Person(email='spam@spam')
        self.assertRaises(ValidationError, person.validate)

        person = Person(email='spam@nospam.com')
        person.validate()

    def test_ip_property(self):
        class Person(Document):
            ip = IPAdressProperty()

        person = Person(ip='256.1.1')
        self.assertRaises(ValidationError, person.validate)

        person = Person(ip='192.168.0.1')
        person.validate()

    def test_url_property(self):
        class Person(Document):
            url = URLProperty()

        person = Person(url='http://google')
        self.assertRaises(ValidationError, person.validate)

        person = Person(url='http://google.com')
        person.validate()

    def test_int_property(self):
        class Person(Document):
            age = IntegerProperty(validators=[NumberRange(min=1, max=80)])

        person = Person(age=30)
        person.validate()

        person.age = 100
        self.assertRaises(ValidationError, person.validate)

        person.age = -1
        self.assertRaises(ValidationError, person.validate)

    def test_boolean_property(self):
        class Person(Document):
            married = BooleanProperty()

        person = Person(married='True')
        self.assertRaises(ValidationError, person.validate)

        person.married = True
        person.validate()

    def test_float_property(self):
        class Person(Document):
            height = FloatProperty(validators=[NumberRange(min=1.2, max=2.2)])

        person = Person()
        person.height = 1.70
        person.validate()

        person.height = '2.0'
        self.assertRaises(ValidationError, person.validate)

        person.height = 2
        self.assertRaises(ValidationError, person.validate)

        person.height = 1.19
        self.assertRaises(ValidationError, person.validate)

        person.height = 2.21
        self.assertRaises(ValidationError, person.validate)

    def test_geo_property(self):
        class Person(Document):
            loc = GeoPtProperty()

        person = Person()
        person.loc = 5
        self.assertRaises(ValidationError, person.validate)

        person.loc = [39.9074977, 116.3972282]
        person.validate()

    def test_datetime_property(self):
        class Person(Document):
            joined = DateTimeProperty()

        person = Person()
        person.joined = datetime.utcnow
        person.validate()

        person.joined = datetime.utcnow()
        person.validate()

        person.joined = '2012-12-25'
        self.assertRaises(ValidationError, person.validate)

    def test_referenced_doc(self):
        class Doc2(Document):
            name = StringProperty()

        class Doc1(Document):
            name = StringProperty()
            doc = ReferenceProperty(Doc2)

        class Doc(Document):
            name = StringProperty()
            doc = ReferenceProperty(Doc1)

        doc2 = Doc2()
        doc2.name = "I'm a referenced doc in a referenced doc"

        doc1 = Doc1()
        doc1.name = "I'm a referenced doc"
        doc1.doc = doc2

        doc = Doc()
        doc.name = "I'm the most top doc"
        doc.doc = doc1

        self.assertEqual("I'm a referenced doc", doc.doc.name)
        self.assertEqual("I'm a referenced doc", doc['doc']['name'])
        self.assertEqual("I'm a referenced doc in a referenced doc", doc.doc.doc.name)
        self.assertEqual("I'm a referenced doc in a referenced doc", doc['doc']['doc']['name'])

        doc.save()
        self.assertTrue(doc.id is not None)
        self.assertTrue(doc.doc.id is not None)
        self.assertTrue(doc.doc.doc.id is not None)

        new_doc = Doc.m.find_one()
        self.assertEqual("I'm a referenced doc", new_doc.doc.name)
        self.assertEqual("I'm a referenced doc", new_doc['doc']['name'])
        self.assertEqual("I'm a referenced doc in a referenced doc", new_doc.doc.doc.name)
        self.assertEqual("I'm a referenced doc in a referenced doc", new_doc['doc']['doc']['name'])

        new_ref_doc1 = Doc1.m.find_one()
        self.assertEqual("I'm a referenced doc", new_ref_doc1.name)
        self.assertEqual("I'm a referenced doc", new_ref_doc1['name'])

        new_ref_doc2 = Doc2.m.find_one()
        self.assertEqual("I'm a referenced doc in a referenced doc", new_ref_doc2.name)
        self.assertEqual("I'm a referenced doc in a referenced doc", new_ref_doc2['name'])

        Doc.m.drop()
        Doc1.m.drop()
        Doc2.m.drop()

    def test_embed_doc(self):
        class Doc2(EmbedDocument):
            name = StringProperty()

        class Doc1(EmbedDocument):
            name = StringProperty()
            doc = EmbedDocumentProperty(Doc2)

        class Doc(Document):
            name = StringProperty()
            doc = EmbedDocumentProperty(Doc1)

        doc2 = Doc2()
        doc2.name = "I'm a embed doc in a embed doc"

        doc1 = Doc1()
        doc1.name = "I'm a embed doc"
        doc1.doc = doc2

        doc = Doc()
        doc.name = "I'm the most top doc"
        doc.doc = doc1

        self.assertEqual("I'm a embed doc", doc.doc.name)
        self.assertEqual("I'm a embed doc", doc['doc']['name'])
        self.assertEqual("I'm a embed doc in a embed doc", doc.doc.doc.name)
        self.assertEqual("I'm a embed doc in a embed doc", doc['doc']['doc']['name'])

        doc.save()

        self.assertTrue(doc.id is not None)
        self.assertTrue(doc1.id is None,)
        self.assertTrue(doc1._id is None,)
        self.assertTrue(doc2.id is None,)
        self.assertTrue(doc2._id is None,)

        new_doc = Doc.m.find_one()
        self.assertEqual("I'm a embed doc", new_doc.doc.name)
        self.assertEqual("I'm a embed doc", new_doc['doc']['name'])
        self.assertEqual("I'm a embed doc in a embed doc", new_doc.doc.doc.name)
        self.assertEqual("I'm a embed doc in a embed doc", new_doc['doc']['doc']['name'])
        self.assertFalse('doc1' in self.db.collection_names())
        self.assertFalse('doc2' in self.db.collection_names())

        Doc.m.drop()


if __name__ == "__main__":
    unittest.main()


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


