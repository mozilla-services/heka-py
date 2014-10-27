NOTE: THIS PROJECT IS DEPRECATED
--------------------------------

This project is no longer being maintained. A simplified version of the core
of this library is available at the following fork:

https://github.com/kalail/heka-py

Support for Heka is available on the Heka mailing list
(https://mail.mozilla.org/listinfo/heka) or on the #heka channel on
irc.mozilla.org.


=========
heka-py
=========

.. image:: https://secure.travis-ci.org/mozilla-services/heka-py.png

heka-py is a Python client for the "Heka" system of application logging and
metrics gathering developed by the `Mozilla Services
<https://wiki.mozilla.org/Services>`_ team. The Heka system is meant to make
life easier for application developers with regard to generating and sending
logging and analytics data to various destinations. It achieves this goal (we
hope!) by separating the concerns of message generation from those of message
delivery and analysis. Front end application code no longer has to deal
directly with separate back end client libraries, or even know what back end
data storage and processing tools are in use. Instead, a message is labeled
with a type (and possibly other metadata) and handed to the Heka system,
which then handles ultimate message delivery.

A pre-rendered version of this documentation is available on
`heka-py <http://heka-py.readthedocs.org>`_.
