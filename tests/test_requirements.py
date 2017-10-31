import os
from blues import util
import unittest

TESTS_ROOT = os.path.dirname(__file__)
PACKAGE_ROOT = os.path.dirname(TESTS_ROOT)


class TestTree(util.RequirementTree):
    def __init__(self, paths, test_dict):
        self.test_dict = test_dict
        super(TestTree, self).__init__(paths=paths)

    def get_content(self, path):
        return self.test_dict[path]


class RequirementTreeTests(unittest.TestCase):
    def setUp(self):
        self.tree = TestTree(paths=['a.txt'], test_dict={
            'a.txt': 'banan\n-r b.txt\n-r c.txt',
            'b.txt': '-r c.txt',
            'c.txt': '-r a.txt',
        })

    def test_tree(self):
        self.assertDictEqual(self.tree.tree, {
            None: ['a.txt'],
            'a.txt': ['b.txt', 'c.txt'],
            'b.txt': ['c.txt'],
            'c.txt': ['a.txt'],
        })

    def test_parents(self):
        self.assertDictEqual(self.tree.parents, {
            'a.txt': [], 'b.txt': ['a.txt'], 'c.txt': ['a.txt', 'b.txt']})

    def test_changed_child(self):
        result = self.tree.get_changed(all_changed_files=['b.txt'])
        self.assertListEqual(result, ['b.txt'])

    def test_changed_parent(self):
        result = self.tree.get_changed(all_changed_files=['a.txt'])
        self.assertListEqual(result, ['a.txt'])

    def test_changed_child_and_parent(self):
        result = self.tree.get_changed(all_changed_files=['a.txt', 'b.txt'])
        self.assertListEqual(result, ['a.txt'])


class ParseRequirementsTests(unittest.TestCase):
    def test_parse_requirements_txt(self):
        file_name = os.path.join(PACKAGE_ROOT, 'requirements.txt')

        with open(file_name) as fp:
            text = fp.read()

        gh = 'git+https://github.com/5monkeys/'
        self.assertListEqual(list(util.iter_requirements(text)), [
            'paramiko==1.16.0', 'enum34==1.1.2',
            'Jinja2==2.7.3', 'PyYAML==3.11',
            gh + 'fabric.git@470a5d91fab350aa7d4aa0f952e1f0eb16ea9d5c',
            gh + 'refabric.git@594b5a5fc9d3e2e184e2580a90866a8dc0aea85d'
        ])

    def test_parse_referred(self):
        text = '-r a.txt\nDjango==1.2.3'
        self.assertListEqual(list(util.iter_requirements(text)),
                             ['-r a.txt', 'Django==1.2.3'])
