"""
Tomcat Blueprint
==============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.tomcat

    settings:
      tomcat:
        empty_webapps: true  # default: true
        catalina_options:
          xms: 128m  # default 128m
          xmx: 256m  # default: 256m

"""
import os
from HTMLParser import HTMLParser
from urllib2 import urlopen

from fabric.context_managers import cd, settings, hide
from fabric.contrib import files
from fabric.decorators import task

from refabric.api import info, run
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import user
from . import debian

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('tomcat', 'start', check_status=True)
stop = debian.service_task('tomcat', 'stop', check_status=True)

tomcat_home = '/usr/share/tomcat'


@task
def setup():
    """
    Install Tomcat
    """
    install()
    configure()


def install():
    # Ensure Java is installed
    from blues import java
    java.install()

    # Create solr user, group and directories
    install_user()

    # Download and extract tomcat
    install_tomcat()


def install_user():
    with sudo():
        user.create_service_user('tomcat')


def install_tomcat():
    with sudo():
        tomcat_version = get_current_version().decode('utf-8')  # could return None!
        version_file = 'apache-tomcat-{}'.format(tomcat_version)
        tar_file = '{}.tar.gz'.format(version_file)
        url = 'http://apache.mirrors.spacedump.net/tomcat/tomcat-7/v{}/bin/{}'.format(tomcat_version, tar_file)

        with cd('/tmp'):
            info('Download {} ({})', 'Tomcat', tomcat_version)
            run('wget {}'.format(url))

            info('Extracting archive...')
            with silent():
                run('tar xzf {}'.format(tar_file))
                tomcat_version_dir = os.path.splitext(os.path.splitext(tar_file)[0])[0]
                tomcat_version_path = os.path.join('/usr', 'share', tomcat_version_dir)
                debian.chmod(tomcat_version_dir, 755, 'tomcat', 'tomcat', recursive=True)
                if files.exists(tomcat_version_path):
                    info('Found same existing version, removing it...')
                    debian.rm(tomcat_version_path, recursive=True)
                if blueprint.get('empty_webapps', True):
                    debian.rm(os.path.join(tomcat_version_dir, 'webapps'), recursive=True)
                debian.mv(tomcat_version_dir, '/usr/share/')
                debian.ln(tomcat_version_path, tomcat_home)
                debian.rm(tar_file)

                debian.ln(os.path.join(tomcat_home, 'logs'), '/var/log/tomcat')


@task
def configure():
    """
    Configure Tomcat
    """
    updated_confs = blueprint.upload(
        'config/', os.path.join(tomcat_home, 'conf'), user='tomcat')
    if debian.lsb_release() >= '16.04':
        updated_init = blueprint.upload('system/', '/etc/systemd/system/')
        if updated_init:
            run('systemctl daemon-reload', use_sudo=True)
    else:
        updated_init = blueprint.upload('init/', '/etc/init/')

    tomcat_xms = blueprint.get('catalina_options', {}).get('xms', '128m')
    tomcat_xmx = blueprint.get('catalina_options', {}).get('xmx', '256m')
    updated_default = blueprint.upload(
        './default', '/etc/default/tomcat',
        context={
            'xms': tomcat_xms,
            'xmx': tomcat_xmx
        }
    )

    context_dir = os.path.join(tomcat_home, 'conf', 'Catalina', 'localhost')
    if not files.exists(context_dir):
        debian.mkdir(context_dir, owner='tomcat', group='tomcat')
    updated_contexts = False
    for context in blueprint.get('contexts', []):
        updated_context = blueprint.upload(
            './context_template.xml',
            os.path.join(context_dir, context['name'] + '.xml'),
            context=context
        )
        if updated_context:
            updated_contexts = True

    if any([updated_confs, updated_init, updated_default, updated_contexts]):
        stop()
        start()


class VersionParser(HTMLParser):
    """Parse Tomcat download page and figure out the current version.
    Once the <pre> block is entered look for a <a> that has a href that starts
    with 'v7.' and return that elements content.
    @see get_current()
    """
    def __init__(self):
        HTMLParser.__init__(self)  # old style class ...
        self._state_found_pre = False  # only <a> within <pre> matter
        self._state_found_version_a = False  # marker for the right <a> tag
        self._version = None  # placeholder for the result

    def handle_starttag(self, tag, attrs):
        # Look for pre tag.
        if tag == u'pre':
            self._state_found_pre = True
        # Look for a tag, if within pre tag
        if self._state_found_pre and tag == u'a':
            attrs = dict(attrs)  # attrs comes in tuple
            href = attrs.get(u'href', u'')  # get link
            if href.startswith(u'v7'):  # check if this is the one
                self._state_found_version_a = True

    def handle_endtag(self, tag):
        if tag == u'pre':
            self._state_found_pre = False

    def handle_data(self, data):
        if self._state_found_version_a:  # found right <a> tag?
            # Save result and reset marker.
            v = data.strip()
            if v[0] == u'v':  # remove leading 'v'
                v = v[1:]
            if v[-1] == u'/':  # remove trailing /
                v = v[:-1]
            self._version = v
            self._state_found_version_a = False


def get_current_version():
    """Parse directory HTML page and extract current tomcat 7 version.

    To download a Tomcat, the current version is needed, to be able to build
    the correct download URL.

    @return: the current Tomcat version, like 7.0.32

    Example HTML file:
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
    <html>
     <head>
      <title>Index of /tomcat/tomcat-7</title>
     </head>
     <body>
    <h1>Index of /tomcat/tomcat-7</h1>
    <pre><img src="/icons/blank.gif" alt="Icon "> <a href="?C=N;O=D">Name</a>
                        <a href="?C=M;O=A">Last modified</a>
          <a href="?C=S;O=A">Size</a>
      <a href="?C=D;O=A">Description</a><hr>
    <img src="/icons/back.gif" alt="[DIR]">
     <a href="/tomcat/">Parent Directory</a>                             -
    <img src="/icons/folder.gif" alt="[DIR]"> <a href="v7.0.32/">v7.0.32/</a>
                    07-Oct-2012 20:37    -
    <img src="/icons/unknown.gif" alt="[   ]"> <a href="KEYS">KEYS</a>
                        14-Jun-2012 14:19   29K
    <hr></pre>
    <address>Apache/2.2.14 (Ubuntu) Server at apache.mirrors.spacedump.net
     Port 80</address>
    </body></html>
    """
    parser = VersionParser()
    res = urlopen('http://apache.mirrors.spacedump.net/tomcat/tomcat-7/')
    # Try to get encoding, without crashing!
    # Example: text/html;charset=UTF-8
    ctype = res.info().getheader('Content-Type', ';charset=ASCII')
    ctype = ''.join(ctype.split(';')[1:])  # remove mimetype
    ctype = ''.join(ctype.split('=')[1:])  # remove 'charset', keep encoding part
    content = res.read()
    try:
        content = content.decode(ctype)
    except TypeError:
        content = content.decode('ascii', 'ignore')
    parser.feed(content)
    return parser._version
