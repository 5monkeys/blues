from contextlib import contextmanager, nested
from refabric.operations import run
import os
import shlex
from .compat import req_file, req_file_build_parser


@contextmanager
def maybe_managed(*context_managers):
    if any(map(lambda x: x is not None, context_managers)):
        with nested(*context_managers):
            yield
    else:
        yield


def parse_requirements(text):
    lines_enum = req_file.preprocess(text, options=None)
    for line_number, line in lines_enum:
        parser = req_file_build_parser(line=line)
        defaults = parser.get_default_values()
        defaults.index_url = None
        args_str, options_str = req_file.break_args_options(line)
        opts, _ = parser.parse_args(shlex.split(options_str), defaults)
        yield args_str, options_str, opts


def iter_requirements(text):
    for a, o, _ in parse_requirements(text=text):
        yield a + o


class RequirementTree(object):
    def __init__(self, paths):
        self.paths = paths
        self.tree = {}
        self._build(paths)

        self.parents = {}
        for parent, children in self.tree.items():
            for child in children:
                self.parents.setdefault(child, [])
                if parent and child not in self.paths:
                    self.parents[child].append(parent)

    def _build(self, paths, parent=None):
        for path in paths:
            self.tree.setdefault(parent, [])
            if path not in self.tree[parent]:
                self.tree[parent].append(path)
            if path not in self.tree:
                self._build(paths=self.parse(path), parent=path)

    def parse(self, path):
        text = self.get_content(path=path)
        for args_str, options_str, opts in parse_requirements(text=text):
            if opts.constraints:
                raise NotImplementedError
            if opts.requirements:
                r = opts.requirements[0]
                if req_file.SCHEME_RE.search(r):
                    raise NotImplementedError
                yield os.path.join(os.path.dirname(path), r)

    def get_content(self, path):
        return run('cat {}'.format(path))

    def all_files(self):
        all_children = set()
        for parent, children in self.tree.items():
            all_children = all_children.union(children)
        return all_children

    def get_changed(self, all_changed_files):
        changed = []
        for path in all_changed_files:
            if not self.is_parent_changed(path, all_changed_files):
                changed.append(path)
        return sorted(changed, key=self.get_order)

    def is_parent_changed(self, child, all_changed_files, tried=None):
        if tried is None:
            tried = []
        if child not in tried:
            tried.append(child)
            for parent in self.parents[child]:
                if parent in all_changed_files or \
                        self.is_parent_changed(parent, all_changed_files,
                                               tried=tried):
                    return True
        return False

    def get_order(self, path, tried=None):
        orders = []
        if tried is None:
            tried = []
        if path in self.paths:
            orders.append(self.paths.index(path))
        if path not in tried:
            tried.append(path)
            for parent in self.parents[path]:
                orders.append(self.get_order(parent, tried=tried))
        return min(orders)
