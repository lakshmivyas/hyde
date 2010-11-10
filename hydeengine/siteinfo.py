import sys
import re
import time as sleeper
import operator

from datetime import date, datetime, time
from threading import Thread, Event

from hydeengine import url
from hydeengine.file_system import File, Folder

class SiteResource(object):
    def __init__(self, a_file, node):
        super(SiteResource, self).__init__()
        self.node = node
        self.file = a_file
        self.source_file = self.file
        self.prerendered = False
        if self.node.target_folder:
            self.target_file = File(
                        self.node.target_folder.child(self.file.name))
            self.temp_file = File(
                        self.node.temp_folder.child(self.file.name))
        self.last_known_modification_time = a_file.last_modified

    @property
    def is_layout(self):
        return (self.node.type == "layout" or
            self.file.name.startswith("_"))

    @property
    def has_changes(self):
        return (not self.last_known_modification_time ==
                    self.file.last_modified)

    @property
    def url(self):
        if self.node.url is None:
            return None
        return url.join(self.node.url, self.file.name)

    @property
    def last_modified(self):
        return self.file.last_modified

    @property
    def name(self):
        return self.file.name

    @property
    def full_url(self):
        if not self.node.full_url:
            return None
        return url.join(self.node.full_url, self.file.name)

    def __repr__(self):
        return str(self.file)

class Page(SiteResource):
    def __init__(self, a_file, node):
        if not node:
            raise ValueError("Page cannot exist without a node")
        super(Page, self).__init__(a_file, node)
        self.created = datetime.strptime("2000-01-01", "%Y-%m-%d")
        self.updated = None
        listing_pages = self.node.site.settings.LISTING_PAGE_NAMES

        self.listing = a_file.name_without_extension in listing_pages
        self.exclude = False
        self.display_in_list = None
        self.module = node.module
        self.process()
        if type(self.created) == date:
            self.created = datetime.combine(self.created, time())

        if type(self.updated) == date:
            self.updated = datetime.combine(self.updated, time())
        elif type(self.updated) != datetime:
            self.updated = self.created

    @property
    def page_name(self):
        return self.file.name_without_extension

    def get_context_text(self):
        start = re.compile(r'.*?{%\s*hyde\s+(.*?)(%}|$)')
        end = re.compile(r'(.*?)(%})')
        fin = open(self.file.path,'r')
        started = False
        text = ''
        matcher = start
        for line in fin:
            match = matcher.match(line)
            if match:
                text = text + match.group(1)
                if started:
                    break
                else:
                    matcher = end
                    started = True
            elif started:
                text = text + line
        fin.close()
        return text

    def add_variables(self, page_vars):
        if not page_vars: return
        for key, value in page_vars.iteritems():
            if not hasattr(Page, key):
                setattr(Page, key, None)
            setattr(self, key, value)

    def process(self):
        text = self.get_context_text()
        import yaml
        context = yaml.load(text)
        if not context:
            context = {}
        self.add_variables(context)
        if (self.file.name_without_extension.lower() ==
                self.node.folder.name.lower()   or
            self.file.name_without_extension.lower() in
                self.node.site.settings.LISTING_PAGE_NAMES):

            self.listing = True

        if self.display_in_list is None:
            self.display_in_list = (not self.listing and
                                    not self.exclude and
                                    not self.file.name.startswith("_") and
                                    self.file.kind == "html")

    def _make_clean_url(self, page_url):
        if self.node.listing_page == self:
            page_url = self.node.url
        else:
            page_url = url.clean_url(page_url)
        if self.node.site.settings.APPEND_SLASH or not page_url:
            page_url += "/"
        return page_url


    @property
    def url(self):
        page_url = super(Page, self).url
        # clean url generation requires knowing whether or not a page is a
        # listing page prior to generating its url
        if self.node.site.settings.GENERATE_CLEAN_URLS:
            page_url = self._make_clean_url(page_url)
        return page_url

    @property
    def full_url(self):
        page_url = super(Page, self).full_url
        # clean url generation requires knowing whether or not a page is a
        # listing page prior to generating its url
        if self.node.site.settings.GENERATE_CLEAN_URLS:
            page_url = self._make_clean_url(page_url)
        return page_url

class SiteNode(object):
    def __init__(self, folder, parent=None):
        super(SiteNode, self).__init__()
        self.folder = folder
        self.parent = parent
        self.site = self
        if self.parent:
            self.site = self.parent.site
        self.children = []
        self.resources = []

    def __repr__(self):
        return str(self.folder)

    @property
    def simple_dict(self):
        ress = []
        for resource in self.walk_resources():
            fragment =  Folder(
                            resource.node.folder.get_fragment(
                                self.site.folder.path)).child(resource.file.name)
            res = dict(
                        name=resource.file.name,
                        path=fragment)
            ress.append(res)
        nodes = []
        for node in self.children:
            nodes.append(node.simple_dict)
        return dict(
                name=self.folder.name,
                path=self.folder.get_fragment(self.site.folder.path),
                resources=ress,
                nodes=nodes)

    @property
    def isroot(self):
        return not self.parent

    @property
    def name(self):
        return self.folder.name

    @property
    def author(self):
        return self.site.settings.SITE_AUTHOR

    @property
    def has_listing(self):
        return not self.listing_page is None

    def walk(self):
        yield self
        for child in self.children:
            for node in child.walk():
                yield node

    def walk_reverse(self):
        yield self
        for child in reversed(self.children):
            for node in child.walk_reverse():
                yield node

    def walk_resources(self):
        for node in self.walk():
            for resource in node.resources:
                yield resource

    def walk_resources_reverse(self):
        for node in self.walk_reverse():
            for resource in reversed(node.resources):
                yield resource

    def add_child(self, folder):
        if ContentNode.is_content(self.site, folder):
            node = ContentNode(folder, parent=self)
        elif LayoutNode.is_layout(self.site, folder):
            node = LayoutNode(folder, parent=self)
        elif MediaNode.is_media(self.site, folder):
            node = MediaNode(folder, parent=self)
        else:
            node = SiteNode(folder, parent=self)
        self.children.append(node)
        self.site.child_added(node)
        return node

    def add_resource(self, a_file):
        resource = self._add_resource(a_file)
        self.site.resource_added(resource)
        return resource

    def remove_resource(self, resource):
        self.resources.remove(resource)
        self.site.resource_removed(resource)

    def _add_resource(self, a_file):
        resource = SiteResource(a_file, self)
        self.resources.append(resource)
        return resource

    def find_node(self, folder):
        try:
            #print 'FIND NODE', folder, self.site.nodemap.get(folder.path)
            return self.site.nodemap[folder.path]
        except KeyError:
            #print 'FAILED FIND NODE', folder
            return None

    find_child = find_node

    def find_resource(self, a_file):
        try:
            return self.site.resourcemap[a_file.path]
        except KeyError:
            return None

    @property
    def source_folder(self):
        return self.folder

    @property
    def target_folder(self):
        return None

    @property
    def temp_folder(self):
        return None

    @property
    def url(self):
        return None

    @property
    def full_url(self):
        if self.url is None:
            return None
        return url.join(self.site.settings.SITE_WWW_URL, self.url)

    @property
    def type(self):
        return None

class ContentNode(SiteNode):

    def __init__(self, folder, parent=None):
        super(ContentNode, self).__init__(folder, parent)
        self.listing_page = None
        self.feed_url = None

    walk_pages = SiteNode.walk_resources
    walk_pages_reverse = SiteNode.walk_resources_reverse

    @property
    def module(self):
        module = self
        while (module.parent and
                not module.parent == self.site.content_node):
            module = module.parent
        return module

    @property
    def name(self):
        if self == self.site.content_node:
            return self.site.name
        else:
            return super(ContentNode, self).name

    @property
    def pages(self):
        return self.resources

    @property
    def ancestors(self):
        node = self
        ancestors = []
        while not node.isroot:
            ancestors.append(node)
            node = node.parent
        ancestors.reverse()
        return ancestors


    @staticmethod
    def is_content(site, folder):
        return (site.content_folder.same_as(folder) or
                site.content_folder.is_ancestor_of(folder))

    def _add_resource(self, a_file):
        page = Page(a_file, self)
        if page.listing and not self.listing_page:
            self.listing_page = page
        self.resources.append(page)
        page.node.sort()
        if not page.module == self.site:
            page.module.flatten_and_sort()
        return page

    def sort(self):
        self.resources.sort(key=operator.attrgetter("created"), reverse=True)
        prev = None
        for page in self.resources:
            page.prev = None
            page.next = None
            if page.display_in_list:
                if prev:
                    prev.next = page
                    page.prev = prev
                page.next = None
                prev = page
        for node in self.children:
            node.sort()

    def flatten_and_sort(self):
        flattened_pages = []
        prev_in_module = None
        for page in self.walk_pages():
            flattened_pages.append(page)
        flattened_pages.sort(key=operator.attrgetter("created"), reverse=True)
        for page in flattened_pages:
            page.next_in_module = None
            if page.display_in_list:
                if prev_in_module:
                    prev_in_module.next_in_module = page
                    page.prev_in_module = prev_in_module
                page.next_in_module = None
                prev_in_module = page

    @property
    def target_folder(self):
        deploy_folder = self.site.target_folder
        return deploy_folder.child_folder_with_fragment(self.fragment)

    @property
    def temp_folder(self):
        temp_folder = self.site.temp_folder
        return temp_folder.child_folder_with_fragment(self.fragment)

    @property
    def fragment(self):
        return self.folder.get_fragment(self.site.content_folder)

    @property
    def url(self):
        return url.join(self.site.settings.SITE_ROOT,
                url.fixslash(
                    self.folder.get_fragment(self.site.content_folder)))

    @property
    def type(self):
      return "content"

    @property
    def listing_url(self):
        return self.listing_page.url

class LayoutNode(SiteNode):

    @staticmethod
    def is_layout(site, folder):
        return (site.layout_folder.same_as(folder) or
                site.layout_folder.is_ancestor_of(folder))

    @property
    def fragment(self):
        return self.folder.get_fragment(self.site.layout_folder)

    @property
    def type(self):
        return "layout"

class MediaNode(SiteNode):

    @staticmethod
    def is_media(site, folder):
        return (site.media_folder.same_as(folder) or
                site.media_folder.is_ancestor_of(folder))

    @property
    def fragment(self):
        return self.folder.get_fragment(self.site.media_folder)

    @property
    def url(self):
        return url.join(self.site.settings.SITE_ROOT,
                url.fixslash(
                    self.folder.get_fragment(self.site.folder)))

    @property
    def type(self):
        return "media"

    @property
    def target_folder(self):
        deploy_folder = self.site.target_folder
        return deploy_folder.child_folder_with_fragment(
            Folder(self.site.media_folder.name).child(self.fragment))

    @property
    def temp_folder(self):
        temp_folder = self.site.temp_folder
        return temp_folder.child_folder_with_fragment(
            Folder(self.site.media_folder.name).child(self.fragment))

class SiteInfo(SiteNode):
    def __init__(self, settings, site_path):
        super(SiteInfo, self).__init__(Folder(site_path))
        self.settings = settings
        self.m = None
        self._stop = Event()
        self.nodemap = {site_path:self}
        self.resourcemap = {}

    @property
    def name(self):
        return self.settings.SITE_NAME

    @property
    def content_node(self):
        return self.nodemap[self.content_folder.path]

    @property
    def fragment(self):
        return ""

    @property
    def media_node(self):
        return self.nodemap[self.media_folder.path]

    @property
    def layout_node(self):
        return self.nodemap[self.layout_folder.path]

    @property
    def content_folder(self):
        return Folder(self.settings.CONTENT_DIR)

    @property
    def layout_folder(self):
        return Folder(self.settings.LAYOUT_DIR)

    @property
    def media_folder(self):
        return Folder(self.settings.MEDIA_DIR)

    @property
    def temp_folder(self):
        return Folder(self.settings.TMP_DIR)

    @property
    def target_folder(self):
        return Folder(self.settings.DEPLOY_DIR)

    def child_added(self, node):
        self.nodemap[node.folder.path] = node

    def resource_added(self, resource):
        self.resourcemap[resource.file.path] = resource

    def resource_removed(self, resource):
        if resource.file.path in self.resourcemap:
            del self.resourcemap[resource.file.path]

    def remove_node(self, node):
        for node in node.walk():
            if node.folder.path in self.nodemap:
                del self.nodemap[node.folder.path]
        for resource in node.walk_resources():
            self.resource_removed(resource)
        if node.parent and node in node.parent.children:
            node.parent.children.remove(node)

    def monitor(self, queue=None, waittime=1):
        if self.m and self.m.isAlive():
            raise "A monitor is currently running."
        self._stop.clear()
        self.m = Thread(target=self.__monitor_thread__,
                            kwargs={"waittime":waittime, "queue": queue})
        self.m.start()
        return self.m

    def dont_monitor(self):
        if not self.m or not self.m.isAlive():
            return
        self._stop.set()
        self.m.join()
        self._stop.clear()

    def __monitor_thread__(self, queue, waittime):
        while not self._stop.isSet():
            try:
                self.refresh(queue)
            except:
                if queue:
                    queue.put({"exception": True})
                raise
            if self._stop.isSet():
                break
            sleeper.sleep(waittime)

    def find_and_add_resource(self, a_file):
        resource = self.find_resource(a_file)
        if resource:
            return resource
        node = self.find_and_add_node(a_file.parent)
        return node.add_resource(a_file)

    def find_and_add_node(self, folder):
        node = self.find_node(folder)
        if node:
            return node
        node = self.find_and_add_node(folder.parent)
        return node.add_child(folder)

    def refresh(self, queue=None):
        site = self
        # Have to poll for changes since there is no reliable way
        # to get notification in a platform independent manner
        class Visitor(object):
            def visit_folder(self, folder):
                return folder.allow(**site.settings.FILTER)

            def visit_file(self, a_file):
                if not a_file.allow(**site.settings.FILTER):
                   return
                resource = site.find_resource(a_file)
                change = None
                if not resource:
                   resource = site.find_and_add_resource(a_file)
                   change = "Added"
                elif resource.has_changes:
                   change = "Modified"
                   resource.last_known_modification_time = a_file.last_modified
                if change:
                    if queue:
                       queue.put({
                           "change": change,
                           "resource": resource,
                           "exception": False
                       })

        visitor = Visitor()
        self.layout_folder.walk(visitor)
        self.content_folder.walk(visitor)
        self.media_folder.walk(visitor)

        nodes_to_remove = []
        for node in self.walk():
            if not node.folder.exists:
                queue.put({
                    "change":"NodeRemoved",
                    "node":node,
                    "exception": False
                })
                nodes_to_remove += [node]

        for node in nodes_to_remove:
            self.remove_node(node)

        for resource in self.walk_resources():
            if not resource.file.exists:
                if queue:
                    queue.put({
                        "change":"Deleted",
                        "resource":resource,
                        "exception": False
                    })
                resource.node.remove_resource(resource)
