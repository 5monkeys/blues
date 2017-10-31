from blues.util import RequirementTree
import unittest


class TestTree(RequirementTree):
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
