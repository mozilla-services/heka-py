NOTE: THIS PROJECT IS DEPRECATED
--------------------------------

This project is no longer being maintained, and it is strongly recommended
that you not use it. While the idea of a Python client that speaks in Heka's
"native" language is not without merit, there are many ways to get data
into Heka (log files, statsd client, feeding directly into a UDP/TCP socket,
etc.), and the Heka team doesn't have the resources to maintain a standalone
Python client at our desired quality / performance level.

If you're interested in feeding data from custom Python software into a Heka
server and you need help figuring out the best way to do so, please ask for
assistance on the Heka mailing list (https://mail.mozilla.org/listinfo/heka)
or on the #heka channel on irc.mozilla.org and we'll be happy to assist.


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

More information about how Mozilla Services is using Heka (including what is
being used for a router and what endpoints are in use / planning to be used)
can be found on `heka-docs <http://heka-docs.readthedocs.org>`_.

A pre-rendered version of this documentation is available on
`heka-py <http://heka-py.readthedocs.org>`_.
