Getting Started
===============

There are two primary components with which users of the heka-py library
should be aware. The first is the :doc:`api/client` client class. The
HekaClient exposes the Heka API, and is generally your main point of
interaction with the Heka system. The client doesn't do very much, however;
it just provides convenience methods for constructing messages of various types
and then passes the messages along. Actual message delivery is handled by a
encoding a message object into a wireformat using :doc:`encoders:
<api/encoders>` and then transported using :doc:`streams <api/streams>`.
without a properly configured encoder and stream, a hekaclient is useless.

The first question you're likely to ask when using heka-py, then, will
probably be "How the heck do I get my hands on a properly configured client?"
You could read the source and instantiate and configure these
objects yourself, but for your convenience we've provided a :doc:`config`
module that simplifies this process considerably. The config module provides
utility functions that allow you pass in a declarative representation of the
settings you'd like for your client and sender objects, and it will create and
configure them for you based on the provided specifications.

Configuration formats
---------------------

As described in detail on the :doc:`config` page, you can create a HekaClient
from either an INI-file style text configuration (using
`client_from_text_config` or `client_from_stream_config`) or a dictionary
(using `client_from_dict_config`). The text version is simply parsed and turned
into a dictionary internally, so the following text config::

  [heka]
  logger = myapp
  severity = 4
  disabled_timers = foo
                    bar
  stream_class = heka.streams.UdpStream
  stream_host = localhost
  stream_port = 5565

Will be converted into this dictionary config::

   {'disabled_timers': ['foo', 'bar'],
    'filters': [],
    'hmac': {},
    'logger': 'myapp',
    'plugins': {},
    'severity': 4,
    'stream': {'class': 'heka.streams.UdpStream',
               'host': 'localhost',
               'port': 5565},
    'stream_class':
    'heka.streams.UdpStream',
    'stream_host': 'localhost',
    'stream_port': 5565}


Let's ignore the details of the config options for now (again, see
:doc:`config` for the nitty-gritty) and just assume that you have a working
client configuration. How might you actually use this within your code to
generate a client and make that client avaialable for use? A couple of
mechanisms are described below.

Example 1: Use your framework
-----------------------------

It is of course possible to simply define or load your configuration up at
module scope and then use it to create a client that is then available to the
rest of the module, like so::

    from heka.config import client_from_stream_config

    with open('/path/to/config.ini', 'r') as inifile:
        hekager = client_from_stream_config(inifile, 'heka')

    hekager.heka('msgtype', payload='Message payload')

However, this is considered by many (including the Heka authors) to be `A Bad
Idea® <http://www.plope.com/Members/chrism/import_time_side_effects>`_. Instead
of creating import time side effects, you can use your application's bootstrap
code to initialize your client and make it available as needed. How exactly
this should work varies from application to application. For instance, the
`Pyramid <http://www.pylonsproject.org/>`_ web framework expects a `main`
function to be defined at the root of your application's package. This might
contain the following code::

    from heka.config import client_from_stream_config
    from pyramid.config import Configurator

    def main(global_config, **settings):
        """ This function returns a Pyramid WSGI application.
        """
        config = Configurator(settings=settings)
        with open('/path/to/config.ini', 'r') as heka_ini:
            heka_client = client_from_stream_config(heka_ini, 'heka')
            config.registry['heka'] = heka_client
        config.add_static_view('static', 'static', cache_max_age=3600)
        config.add_route('home', '/')
        config.scan()
        return config.make_wsgi_app()

Then the HekaClient instance will be available on Pyramid's "registry", which
is always available through the request object or a library call. With a bit
more code you could put your Heka configuration info into Pyramid's default
config file and then extract it from the `settings` values passed in to the
`main` function. The idea is that you make use of whatever infrastructure or
patterns that your application and/or framework provide and cooperate with
those to create and make available a client for logging and metrics-gathering
needs.

Example 2: Module scope, if you must
------------------------------------

Despite the fact that some consider it to be an `anti-pattern
<http://www.plope.com/Members/chrism/logging_blues>`_, there are those who are
quite fond of the `import logging; logger = logging.getLogger('foo')` idiom
that the stdlib logging package provides for making a logger available at
module scope. We recommend that you consider not doing so and instead making
your client available through some application- or framework-specific
mechanism, but if you really want to stick to your guns then there's a bit of
convenience that heka-py provides.

The short version is that where you would have done this::

    from logging import getLogger
    logger = getLogger('myapp')

Instead you'd do the following::

    from heka.holder import get_client
    heka_log = get_client('myapp')

Every time throughout your application's process, a call to
`get_client('myapp')` will return the same HekaClient instance. At this
point, however, the client in question is still not usable, because it doesn't
have a working sender. Again, the recommendation is that somewhere in your
application code you use one of the config functions to initialize the client,
which might look like this::

    from heka.config import client_from_stream_config
    from heka.holder import get_client
    heka_log = get_client('myapp')

    def some_init_function():
        with open('/path/to/heka.ini', 'r') as heka_ini:
            client_from_stream_config(heka_ini, 'heka', heka_log)

Note that the `heka_log` client was passed in to the
`client_from_stream_config` call, which causes the configuration to be applied
to that client rather than a new client being created.

If you *really* want to do all of your initialization at module scope, you can
pass a config dict to the `get_client` function. This is a minimal working
configuration that will cause all Heka output to be sent to stdout::

    from heka.holder import get_client
    heka_config = {'stream': {'class': 'heka.streams.StdOutStream'}}
    heka_log = get_client('myapp', heka_config)
