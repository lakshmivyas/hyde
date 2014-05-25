"""
 Entry Points for Hyde Engine

"""
import imp
import mimetypes
import os
import sys
import subprocess
import traceback
import urllib

from collections import defaultdict
from Queue import Queue, Empty
from threading import Thread, Event

from django.conf import settings
from django.template import add_to_builtins


from file_system import File, Folder
from path_util import PathUtil
from processor import Processor
from siteinfo import SiteInfo
from url import clean_url

try:
    from collections import OrderedDict
except ImportError:
    from _collections import OrderedDict

class _HydeDefaults:
    GENERATE_CLEAN_URLS = False
    GENERATE_ABSOLUTE_FS_URLS = False
    LISTING_PAGE_NAMES = ['index', 'default', 'listing']
    APPEND_SLASH = False
    MEDIA_PROCESSORS = {}
    CONTENT_PROCESSORS = {}
    SITE_PRE_PROCESSORS = {}
    SITE_POST_PROCESSORS = {}
    CONTEXT = {}
    RST_SETTINGS_OVERRIDES = {}

def setup_env(site_path, settings_name="settings"):
    """
    Initializes the Django Environment. NOOP if the environment is
    initialized already.

    """
    # Don't do it twice
    if hasattr(settings, "CONTEXT"):
        return

    settings_file = os.path.join(site_path, settings_name + ".py")
    if not os.path.exists(settings_file):
        print "No Site Settings File Found"
        raise ValueError("The given site_path [%s] does not contain a hyde site. "
                         "Give a valid path or run -init to create a new site." % (site_path,))

    try:
        hyde_site_settings = imp.load_source("hyde_site_settings", settings_file)
    except SyntaxError, err:
        print "The given site_path [%s] contains a settings file " \
              "that could not be loaded due syntax errors." % site_path
        print err
        exit()
    except Exception, err:
        print "Failed to import Site Settings"
        print "The settings file [%s] contains errors." % (settings_file,)
        raise

    try:
        from django.conf import global_settings
        defaults = global_settings.__dict__
        defaults.update(hyde_site_settings.__dict__)
        settings.configure(_HydeDefaults, **defaults)
    except Exception, err:
        print "Site settings are not defined properly"
        print err
        raise ValueError(
            "The given site_path [%s] has invalid settings. "
            "Give a valid path or run -init to create a new site."
            %  site_path
        )

def validate_settings():
    """
    Ensures the site settings are properly configured.

    """
    if settings.GENERATE_CLEAN_URLS and settings.GENERATE_ABSOLUTE_FS_URLS:
        raise ValueError(
            "GENERATE_CLEAN_URLS and GENERATE_ABSOLUTE_FS_URLS cannot "
            "be enabled at the same time."
        )


class Server(object):
    """
    Initializes and runs a cherrypy webserver serving static files from the deploy
    folder

    """
    def __init__(self, site_path, address='localhost', port=8080):
        super(Server, self).__init__()
        self.site_path = os.path.abspath(os.path.expandvars(
                                        os.path.expanduser(site_path)))
        self.address = address
        self.port = port

    def serve(self, deploy_path, exit_listner, settings_name="settings"):
        """
        Starts the cherrypy server at the given `deploy_path`.  If exit_listner is
        provided, calls it when the engine exits.
        """
        try:
            import cherrypy
            from cherrypy.lib.static import serve_file
        except ImportError:
            print "Cherry Py is required to run the webserver"
            raise

        setup_env(self.site_path, settings_name)
        validate_settings()
        deploy_folder = Folder(
                            (deploy_path, settings.DEPLOY_DIR)
                            [not deploy_path])
        if not 'site' in settings.CONTEXT:
            generator = Generator(self.site_path)
            generator.create_siteinfo()
        site = settings.CONTEXT['site']
        url_file_mapping = defaultdict(bool)
        # This following bit is for supporting listing pages with arbitrary
        # filenames.
        if settings.GENERATE_CLEAN_URLS:
            for page in site.walk_pages(): # build url to file mapping
                if page.listing and page.file.name_without_extension not in \
                   (settings.LISTING_PAGE_NAMES + [page.node.name]):
                    filename = page.target_file.path
                    url = page.url.strip('/')
                    url_file_mapping[url] = filename

        class WebRoot:
            @cherrypy.expose
            def index(self):
                page =  site.listing_page
                return serve_file(deploy_folder.child(page.name))

            if settings.GENERATE_CLEAN_URLS:
                @cherrypy.expose
                def default(self, *args):
                    # TODO notice that this method has security flaws
                    # TODO for every url_file_mapping not found, we will
                    #      save that in url_file_mapping. not optimal.

                    # first, see if the url is in the url_file_mapping
                    # dictionary
                    file = url_file_mapping[os.sep.join(args)]
                    if file:
                        return serve_file(file)
                    # next, try to find a listing page whose filename is the
                    # same as its enclosing folder's name
                    file = os.path.join(deploy_folder.path, os.sep.join(args),
                        args[-1] + '.html')
                    if os.path.isfile(file):
                        return serve_file(file)
                    # try each filename in LISTING_PAGE_NAMES setting
                    for listing_name in settings.LISTING_PAGE_NAMES:
                        file = os.path.join(deploy_folder.path,
                                        os.sep.join(args),
                                        listing_name + '.html')
                        if os.path.isfile(file):
                            return serve_file(file)
                    # failing that, search for a non-listing page
                    file = os.path.join(deploy_folder.path,
                                        os.sep.join(args[:-1]),
                                        args[-1] + '.html')
                    if os.path.isfile(file):
                        return serve_file(file)
                    # failing that, page not found
                    raise cherrypy.NotFound

        cherrypy.config.update({'environment': 'production',
                                  'log.error_file': 'site.log',
                                  'log.screen': True,
                                  'server.socket_host': self.address,
                                  'server.socket_port': self.port,
                                  })

        # even if we're still using clean urls, we still need to serve media.
        if settings.GENERATE_CLEAN_URLS:
            media_web_path = '/%s/media' % settings.SITE_ROOT.strip('/')
            # if SITE_ROOT is /, we end up with //media
            media_web_path = media_web_path.replace('//', '/')

            conf = {media_web_path: {
            'tools.staticdir.dir':os.path.join(deploy_folder.path,
                                               settings.SITE_ROOT.strip('/'),
                                               'media'),
            'tools.staticdir.on':True
            }}
        else:
            conf = {'/': {
            'tools.staticdir.dir': deploy_folder.path,
            'tools.staticdir.on':True
            }}
        cherrypy.tree.mount(WebRoot(), settings.SITE_ROOT, conf)
        if exit_listner:
            cherrypy.engine.subscribe('exit', exit_listner)
        cherrypy.engine.start()

    @property
    def alive(self):
        """
        Checks if the webserver is alive.

        """
        import cherrypy
        return cherrypy.engine.state == cherrypy.engine.states.STARTED

    def block(self):
        """
        Blocks and waits for the engine to exit.

        """
        import cherrypy
        cherrypy.engine.block()

    def quit(self):
        import cherrypy
        cherrypy.engine.exit()


# TODO split into a generic wsgi handler, combine it with the current server
def GeventServer(*args, **kwargs):
    import gevent.greenlet
    import gevent.wsgi

    class GeventServerWrapper(Server):
        STOP_TIMEOUT = 10
        CHUNK_SIZE = 4096
        FALLBACK_CONTENT_TYPE = 'application/octet-stream'

        def __init__(self, *args, **kwargs):
            super(GeventServerWrapper, self).__init__(*args, **kwargs)

            addr = (self.address, self.port)
            self.server = gevent.wsgi.WSGIServer(addr, self.request_handler)

            self.paths = {}
            self.root = None

            # FIXME
            mimetypes.init()

        def serve(self, deploy_path, exit_listener, settings_name="settings"):
            setup_env(self.site_path, settings_name)
            validate_settings()

            self.root = deploy_path or settings.DEPLOY_DIR

            if not 'site' in settings.CONTEXT:
                generator = Generator(self.site_path)
                generator.create_siteinfo()

            def add_url(url, path, listing):
                # TODO fix this ugly url hack
                if settings.GENERATE_CLEAN_URLS and '.' in url:
                    url = clean_url(url)

                # strip names from listing pages
                head, tail = os.path.split(url)
                parent = os.path.basename(head)
                name = os.path.splitext(tail)[0]
                if listing and (name == parent or
                                name in settings.LISTING_PAGE_NAMES):
                    url = os.path.dirname(url)
                self.paths.setdefault(url, path)

            # gather all urls (only works if you generate it)
            """
            site = settings.CONTEXT['site']
            for page in site.walk_pages():
                url = page.url.strip('/')
                add_url(url, page.target_file.path, page.listing)
            """

            # register all other static files
            # FIXME we just register all files, we should do this properly
            # FIXME we're relying on os.sep is /, fine for now
            for dirpath, dirnames, filenames in os.walk(self.root):
                path = dirpath[len(self.root)+1:]
                for filename in filenames:
                    url = os.path.join(path, filename)
                    # do we know if it's listing or not?
                    add_url(url, os.path.join(dirpath, filename), listing=True)

            import pprint
            #print 'I currently serve: \n', pprint.pformat(sorted(self.paths.items()))

            self.server.start()
            print 'Started %s on %s:%s' % (self.server.base_env['SERVER_SOFTWARE'],
                                           self.server.server_host,
                                           self.server.server_port)


        def block(self):
            # XXX is there a nicer way of doing this?
            try:
                self.server._stopped_event.wait()
            finally:
                gevent.greenlet.Greenlet.spawn(self.server.stop,
                                               timeout=self.STOP_TIMEOUT).join()

        def quit(self):
            self.server.stop(timeout=self.STOP_TIMEOUT)

        def request_handler(self, env, start_response):
            # extract the real requested file
            path = os.path.abspath(urllib.unquote_plus(env['PATH_INFO']))

            # check if file exists
            filename = self.paths.get(path.strip('/'))
            if not filename or not os.path.exists(filename):
                start_response('404 Not Found', [('Content-Type', 'text/plain')])
                yield 'Not Found\n'
                return

            # TODO how do we easiest detect mime types?
            content_type, encoding = mimetypes.guess_type(filename)
            if not content_type:
                content_type = self.FALLBACK_CONTENT_TYPE
            start_response('200 OK', [('Content-Type', content_type)])

            # TODO make this async?
            f = file(filename, 'rb')
            try:
                chunk = f.read(self.CHUNK_SIZE)
                while chunk:
                    yield chunk
                    chunk = f.read(self.CHUNK_SIZE)
            finally:
                f.close()

    return GeventServerWrapper(*args, **kwargs)

class Generator(object):
    """
    Generates a deployable website from the templates. Can monitor the site for
    """
    def __init__(self, site_path):
        super(Generator, self).__init__()
        self.site_path = os.path.abspath(os.path.expandvars(
                                        os.path.expanduser(site_path)))
        self.regenerate_request = Event()
        self.regeneration_complete = Event()
        self.queue = Queue()
        self.watcher = Thread(target=self.__watch__)
        self.regenerator = Thread(target=self.__regenerate__)
        self.processor = Processor(settings)
        self.quitting = False

    def notify(self, title, message):
        if hasattr(settings, "GROWL") and settings.GROWL and File(settings.GROWL).exists:
            try:
                subprocess.call([settings.GROWL, "-n", "Hyde", "-t", title, "-m", message])
            except:
                pass
        elif hasattr(settings, "NOTIFY") and settings.NOTIFY and File(settings.NOTIFY).exists:
            try:
                subprocess.call([settings.NOTIFY, "Hyde: " + title, message])
            except:
                pass

    def pre_process(self, node):
        self.processor.pre_process(node)

    def process(self, item, change="Added"):
        if change in ("Added", "Modified"):
            settings.CONTEXT['node'] = item.node
            settings.CONTEXT['resource'] = item
            return self.processor.process(item)
        elif change in ("Deleted", "NodeRemoved"):
            return self.processor.remove(item)

    def build_siteinfo(self, deploy_path=None):
        tmp_folder = Folder(settings.TMP_DIR)
        deploy_folder = Folder(
                            (deploy_path, settings.DEPLOY_DIR)
                            [not deploy_path])

        if deploy_folder.exists and settings.BACKUP:
            backup_folder = Folder(settings.BACKUPS_DIR).make()
            deploy_folder.backup(backup_folder)

        tmp_folder.delete()
        tmp_folder.make()
        settings.DEPLOY_DIR = deploy_folder.path
        if not deploy_folder.exists:
            deploy_folder.make()
        add_to_builtins('hydeengine.templatetags.hydetags')
        add_to_builtins('hydeengine.templatetags.aym')
        add_to_builtins('hydeengine.templatetags.typogrify')
        self.create_siteinfo()

    def create_siteinfo(self):
        srcroot = self.site_path
        if hasattr(settings, 'SRC_DIR') and Folder(settings.SRC_DIR).exists:
            srcroot = settings.SRC_DIR
        self.siteinfo  = SiteInfo(settings, srcroot)
        self.siteinfo.refresh()
        settings.CONTEXT['site'] = self.siteinfo.content_node

    def post_process(self, node):
        self.processor.post_process(node)

    def process_all(self):
        self.notify(self.siteinfo.name, "Website Generation Started")
        try:
            self.pre_process(self.siteinfo)
            for resource in self.siteinfo.walk_resources():
                self.process(resource)
            self.complete_generation()
        except Exception, e:
            print >> sys.stderr, "Generation Failed"
            traceback.print_exc(file=sys.stderr)
            self.notify(self.siteinfo.name, "Generation Failed")
            return
        self.notify(self.siteinfo.name, "Generation Complete")

    def complete_generation(self):
        self.post_process(self.siteinfo)
        self.siteinfo.target_folder.copy_contents_of(
               self.siteinfo.temp_folder, incremental=True)
        if(hasattr(settings, "post_deploy")):
            settings.post_deploy()

    def __regenerate__(self):
        pending = False
        while True:
            try:
                if self.quit_event.isSet():
                    self.notify(self.siteinfo.name, "Exiting Regenerator")
                    print "Exiting regenerator..."
                    break

                # Wait for the regeneration event to be set
                self.regenerate_request.wait(5)

                # Wait until there are no more requests
                # Got a request, we dont want to process it
                # immedietely since other changes may be under way.

                # Another request coming in renews the initil request.
                # When there are no more requests, we go are and process
                # the event.
                if not self.regenerate_request.isSet() and pending:
                    pending = False
                    self.process_all()
                    self.regeneration_complete.set()
                elif self.regenerate_request.isSet():
                    self.regeneration_complete.clear()
                    pending = True
                    self.regenerate_request.clear()
            except:
                print >> sys.stderr, "Error during regeneration"
                traceback.print_exc(file=sys.stderr)
                self.notify(self.siteinfo.name, "Error during regeneration")
                self.regeneration_complete.set()
                self.regenerate_request.clear()
                pending = False

    def __watch__(self):
        regenerating = False
        while True:
            try:
                if self.quit_event.isSet():
                    print "Exiting watcher..."
                    self.notify(self.siteinfo.name, "Exiting Watcher")
                    break
                try:
                    pending = self.queue.get(timeout=10)
                except Empty:
                    continue

                self.queue.task_done()
                if pending.setdefault("exception", False):
                    self.quit_event.set()
                    print "Exiting watcher"
                    self.notify(self.siteinfo.name, "Exiting Watcher")
                    break

                if 'resource' in pending:
                    resource = pending['resource']

                if self.regeneration_complete.isSet():
                    regenerating = False

                if pending['change'] == "Deleted":
                    self.process(resource, pending['change'])
                elif pending['change'] == "NodeRemoved":
                    self.process(pending['node'], pending['change'])

                if (pending['change']  in ("Deleted", "NodeRemoved") or
                   resource.is_layout or regenerating):
                    regenerating = True
                    self.regenerate_request.set()
                    continue

                self.notify(self.siteinfo.name, "Processing " + resource.name)
                if self.process(resource, pending['change']):
                    self.complete_generation()
                    self.notify(self.siteinfo.name, "Completed processing " + resource.name)
            except:
                print >> sys.stderr, "Error during regeneration"
                traceback.print_exc(file=sys.stderr)
                self.notify(self.siteinfo.name, "Error during regeneration")
                self.regeneration_complete.set()
                self.regenerate_request.clear()
                regenerating = False

    def generate(self, deploy_path=None,
                       keep_watching=False,
                       exit_listner=None,
                       settings_name="settings"):

        self.exit_listner = exit_listner
        self.quit_event = Event()
        setup_env(self.site_path, settings_name)
        validate_settings()
        self.build_siteinfo(deploy_path)
        self.process_all()
        self.siteinfo.temp_folder.delete()
        if keep_watching:
            try:
                self.siteinfo.temp_folder.make()
                self.watcher.start()
                self.regenerator.start()
                self.siteinfo.monitor(self.queue)
            except (KeyboardInterrupt, IOError, SystemExit):
                self.quit()
            except:
                self.quit()
                raise

    def block(self):
        try:
            while self.watcher.isAlive():
                self.watcher.join(0.1)
            while self.regenerator.isAlive():
                self.regenerator.join(0.1)
            self.siteinfo.dont_monitor()
        except (KeyboardInterrupt, IOError, SystemExit):
            self.quit()
        except:
            self.quit()
            raise

    def quit(self):
        if self.quitting:
            return
        self.quitting = True
        print "Shutting down..."
        self.notify(self.siteinfo.name, "Shutting Down")
        self.siteinfo.dont_monitor()
        self.quit_event.set()
        if self.exit_listner:
            self.exit_listner()


class Initializer(object):
    def __init__(self, site_path):
        super(Initializer, self).__init__()
        self.site_path = Folder(site_path)

    def initialize(self, root, template=None, force=False):
        if not template:
            template = "default"
        root_folder = Folder(root)
        template_dir = root_folder.child_folder("templates", template)

        if not template_dir.exists:
            raise ValueError(
            "Cannot find the specified template[%s]." % template_dir)

        if self.site_path.exists:
            files = os.listdir(self.site_path.path)
            PathUtil.filter_hidden_inplace(files)
            if len(files) and not force:
                raise ValueError(
                "The site_path[%s] is not empty." % self.site_path)
            elif force:
                self.site_path.delete()
        self.site_path.make()
        self.site_path.copy_contents_of(template_dir)
