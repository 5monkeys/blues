.. Blues documentation master file, created by
   sphinx-quickstart on Sat Nov 22 18:49:32 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Blues's documentation!
=================================

Dependencies
------------

* `fabric` https://github.com/5monkeys/fabric/tree/develop
* `refabric` https://github.com/5monkeys/refabric/tree/develop
* `blues` https://github.com/5monkeys/blues

*Fabric fork is not needed when v1.11 is released.*

Install
-------

.. code-block:: sh

    $ virtualenv fabric
    $ pip install -e git+git@github.com:5monkeys/fabric.git@develop#egg=fabric
    $ pip install Jinja2
    $ pip install PyYAML
    $ pip install -e git+git@github.com:5monkeys/blues.git@master#egg=blues
    $ pip install -e git+git@github.com:5monkeys/refabric.git@develop#egg=refabric


Contents
--------

.. toctree::
   :maxdepth: 2

.. toctree::
   :maxdepth: 3

   api/blues


Indices and tables
==================

* :ref:`modindex`
* :ref:`search`
