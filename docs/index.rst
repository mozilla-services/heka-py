.. heka-py documentation master file, created by
   sphinx-quickstart on Wed Feb  8 17:50:44 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. include:: ../README.rst

There are two primary components to the heka-py library, the :doc:`api/client`
client class which exposes the primary heka client API, and the various
:doc:`api/senders` classes, one of which must be provided to the HekaClient and
which handles the actual delivery of the message to the router component.

The HekaClient can be instantiated directly, but heka-py also provides some
utility functions that will parse config files and set up a configured client
instance for you. Folks new to using Heka will probably find :doc:`config` a
good place to get started.

Contents
========

.. toctree::
   :maxdepth: 5

   getstarted
   config
   api/config
   api/client
   api/senders
   api/decorators
   api/exceptions


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

