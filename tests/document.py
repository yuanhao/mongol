# -*- coding: utf-8 -*-
#
# Author: Yuanhao Li <jay_21cn [at] hotmail [dot] com>

import unittest

from pymongo.objectid import ObjectId
from pymongo import DESCENDING, ASCENDING

from mongol.document import Document, DocumentNotSavedError, DocumentInheritError
from mongol.property import *
from mongol.connection import db, connect


class DocumentTest(unittest.TestCase):
    def setUp(self):
        self.db = connect('mongoltest')

        class Blog(Document):
            title = Property()
            tags = ListProperty()
            author = DictProperty()

        self.Blog = Blog

    def tearDown(self):
        self.Blog.m.drop()

    def test_drop_collection(self):
        # instance test
        blog = self.Blog(title='Blog Title')
        blog.save()

        collection_name = blog.__collection_name__
        self.assertTrue(collection_name in self.db.collection_names())

        blog.m.drop()
        self.assertFalse(collection_name in self.db.collection_names())

        # class method test
        blog = self.Blog(title='Blog Title')
        blog.save()

        collection_name = self.Blog.__collection_name__
        self.assertTrue(collection_name in self.db.collection_names())

        self.Blog.m.drop()
        self.assertFalse(collection_name in self.db.collection_names())

    def test_definition(self):
        name_field = Property()
        age_field = Property()

        class Person(Document):
            name  = name_field
            age = age_field
            non_field = True

        self.assertTrue(Person.__properties__['name'], name_field)
        self.assertTrue(Person.__properties__['age'], age_field)
        self.assertFalse('non_field' in Person.__properties__)

        properties = list(Person)
        self.assertTrue('name' in properties and 'age' in properties)
        self.assertFalse(hasattr(Document, '__properties__'))
        Person.m.drop()

    def test_default_value(self):
        class Person(Document):
            name = StringProperty()
            age = IntegerProperty(default=30)
            user_id = StringProperty(default=lambda: 'test callable')

        person = Person(name='Slash')
        self.assertTrue(person.age, 30)
        self.assertTrue(person['age'], 30)
        self.assertTrue(person.user_id, 'test callable')
        self.assertTrue(person['user_id'], 'test callable')

    def test_collection_definition(self):
        class Person(Document):
            __collection_name__ = 'rocker'
            name = Property()
        Person(name='Slash').save()
        self.assertTrue('rocker' in self.db.collection_names())
        Person.m.drop()

    def test_object_id_create(self):
        blog = self.Blog(title="Slash rocks")
        self.assertEqual(None, blog._id)
        self.assertEqual(None, blog['_id'])
        blog.save()
        self.assertTrue(isinstance(blog.id, ObjectId))
        self.assertTrue(blog.id == blog._id)

    def test_save_and_find(self):
        self.Blog.m.drop()
        self.Blog(title="1 Slash rocks").save()
        self.Blog(title="2 Slash rocks again", tags=['gibson', 'classic',
            '1960']).save()
        self.Blog.m.ensure_index([('title', ASCENDING)])
        blogs = self.Blog.m.all()
        self.assertEqual(2, len(blogs))

        blogs = list(blogs)
        self.assertEqual("1 Slash rocks", blogs[0].title)
        self.assertEqual("2 Slash rocks again", blogs[1].title)

        self.assertEqual("2 Slash rocks again", self.Blog.m.find({'tags':
            '1960'})[0].title)

    def test_custom_method(self):
        class Person(Document):
            name = Property()

            def eat(self, food):
                return '%s eat %s'% (self.name, food)

        person = Person(name="Slash")
        self.assertEqual("Slash eat suguar", person.eat('suguar'))
        Person.m.drop()

    def test_find_one(self):
        self.Blog(title="Gun & Rose", tags=['rock', 'metal']).save()
        self.Blog(title="Guitar Hero Slash", tags=['guitar', 'slash']).save()
        blog = self.Blog.m.find_one({'title': "Gun & Rose"})
        self.assertEqual("Gun & Rose", blog.title)

    def test_update(self):
        blog = self.Blog(title="Slash rocks")
        blog.update({ 'tags': ['rocker', 'guitar hero'] })
        self.assertEqual(['rocker', 'guitar hero'], blog.tags)

    def test_find_one_can_return_none(self):
        blog = self.Blog.m.find_one({'title': 'The Who'})
        self.assertEqual(None, blog)

    def test_doc_can_be_subscriptable(self):
        blog = self.Blog(title="Slash rocks")
        self.assertEqual("Slash rocks", blog['title'])

    def test_expandable_doc_properties(self):
        class Person(Document):
            __expandable__ = True
            name = Property()
        person = Person(name="Slash")
        person.band = Property("gnr")
        self.assertTrue("band" in person.__properties__.keys())
        self.assertEqual("gnr", person.band)
        self.assertEqual("gnr", person['band'])

    def test_access_to_inner_attributes(self):
        blog = self.Blog(title="Slash rocks", tags=['rock', 'roll'],
            author={
                'name': 'Yuanhao Li',
                'email': 'nospam@nospam.org',
                'address': {
                    'country': 'China',
                }
            })
        self.assertEqual('Yuanhao Li', blog.author.name)
        self.assertEqual('China', blog.author.address.country)

    def test_change_attributes(self):
        blog = self.Blog(title="Slash", tags=['rock', 'roll'])
        blog.author = {}
        blog.author.name = "Axl Rose"
        blog.tags = ['rocks']
        blog.save()

        blog = self.Blog.m.find_one()
        self.assertEqual('Slash', blog.title)
        self.assertEqual(dict(name='Axl Rose'), blog.author)
        self.assertEqual(['rocks'], blog.tags)

    def test_del_attributes(self):
        blog = self.Blog(title="Slash", tags=['rock', 'roll'])
        blog.author = {}
        blog.author.name = "Axl Rose"
        blog.author.last = "Rose"
        del blog.author.name
        self.assertEqual(dict(last="Rose"), blog.author)

    def test_sort_documents(self):
        class Person(Document):
            name = Property()

        names = ["Rose", "Axl", "Slash", "Yuanhao", "Li"]
        for name in names:
            Person(name=name).save()
        Person.m.ensure_index([('name', ASCENDING)])
        docs = list(Person.m.all().sort([('name', ASCENDING)])[:2])

        self.assertEqual(2, len(docs))
        self.assertEqual("Axl", docs[0].name)
        self.assertEqual("Li", docs[1].name)

    def test_remove(self):
        self.Blog(title="Axl Rocks").save()
        blog = self.Blog(title="Slash Rocks")
        blog.save()
        self.assertEqual(2, self.Blog.m.all().count())

        blog.remove()
        self.assertEqual(1, self.Blog.m.all().count())

    def test_polymorphic_queries(self):
        class Shape(Document):
            __inherit_enabled__ = True

            x = Property()
            y = Property()

        class Rectangle(Shape):
            rect = Property()

        class Circle(Shape):
            cir = Property()

        class Square(Rectangle):
            squ = Property()

        Shape().save()
        Rectangle().save()
        Circle().save()
        Square().save()

        self.assertEqual(['Shape', 'Rectangle', 'Circle', 'Square'], [obj.__class_name__ for obj in Shape.m.all()])
        self.assertEqual(['Rectangle', 'Square'], [obj.__class_name__ for obj in Rectangle.m.all()])
        self.assertEqual(['Circle'], [obj.__class_name__ for obj in Circle.m.all()])
        self.assertEqual(['Square'], [obj.__class_name__ for obj in Square.m.all()])

        Shape.m.drop()
        Rectangle.m.drop()
        Circle.m.drop()
        Square.m.drop()

    def test_inheritance(self):
        class A(Document):
            __inherit_enabled__ = True
            x = Property()

        class B(A):
            y = Property()

        self.assertTrue('x' in B.__properties__)
        self.assertTrue('y' in B.__properties__)
        self.assertEqual(A.__collection_name__, B.__collection_name__)


    def test_disabled_inheritance(self):
        class A(Document): pass
        def create_inherited_class():
            class B(A): pass
        self.assertRaises(DocumentInheritError, create_inherited_class)


if __name__ == "__main__":
    unittest.main()


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


