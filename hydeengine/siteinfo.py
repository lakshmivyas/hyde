from hydeengine.file_system import File, Folder

class SiteResource(object):
    def __init__(self, a_file):
        super(SiteResource, self).__init__()
        self.resource_file = a_file
        
    def __repr__(self):
        return str(self.resource_file)

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
    def isroot(self):
        return not self.parent
        
    @property
    def name(self):
        return self.folder.name
        
    def walk(self):
        yield self
        for child in self.children:
            for node in child.walk():                
                yield node
    
    def find_child(self, folder):
        for node in self.walk():
            if node.folder.same_as(folder):
                return node
        return None
        
    def add_child(self, folder):
        node = SiteNode(folder, parent=self)
        self.children.append(node)
        return node
        
    def add_resource(self, a_file):
        resource = SiteResource(a_file)
        self.resources.append(resource)
        return resource
        
    def find_node(self, folder):
        if self.folder.same_as(folder):
            return self
        found_node = None
        # Check parents first
        #
        if not self.isroot:
            found_node = self.parent.find_node(folder)
        # Check children
        #     
        if not found_node:
            found_node = self.find_child(folder)
        return found_node
    
    def find_resource(self, a_file):
        node = self.find_node(a_file.parent)
        if not node:
            return None
        for resource in node.resources:
            if resource.resource_file.same_as(a_file):
                return resource
        return None
    
    @property
    def source_folder(self):
        return self.folder

    @property
    def target_folder(self):
        if self.type not in ("content", "media"):
            return None
        deploy_folder = self.site.target_folder
        return deploy_folder.child_folder_with_fragment(self.url)
        
    @property
    def temp_folder(self):
        if self.type not in ("content", "media"):
            return None
        temp_folder = self.site.temp_folder
        return temp_folder.child_folder_with_fragment(self.url)

    @property
    def url(self):
        if self.type == "content":
            return self.folder.get_fragment(self.site.content_folder)
        elif self.type == "layout":
            return None    
        else: 
            return self.folder.get_fragment(self.site.folder)
            
    @property   
    def full_url(self):
        return self.site.settings.SITE_WWW_URL.rstrip("/") + \
                "/" + self.url.lstrip("/")
        
    @property
    def type(self):
        folders = { self.site.content_folder:"content",
                    self.site.media_folder:"media",
                    self.site.layout_folder:"layout"
                  }
        for folder, type in folders.iteritems():
            if (folder.same_as(self.folder) or
                folder.is_ancestor_of(self.folder)):
                return type
        return None
        
class ContentNode(SiteNode):
      def __init__(self, folder):
          super(ContentNode, self).__init__(folder)
          
      def type(self):
          return "content"
          
class LayoutNode(SiteNode):
    def __init__(self, folder):
        super(LayoutNode, self).__init__(folder)

    def type(self):
        return "layout"          
          
class MediaNode(SiteNode):
      def __init__(self, folder):
          super(MediaNode, self).__init__(folder)

      def type(self):
          return "media"          
    
class SiteInfo(SiteNode):
    def __init__(self, settings, site_path, visitor=None):
        super(SiteInfo, self).__init__(Folder(site_path))
        self.settings = settings
        self.update(visitor)
     
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

        
    def update(self, visitor):
        class Visitor(object):
            def __init__(self, siteinfo):
                self.current_node = siteinfo
                
            def visit_file(self, a_file):
                resource = self.current_node.add_resource(a_file)
                try:
                    visitor.visit_resource(resource)
                except AttributeError:
                    pass
                    
            def visit_folder(self, folder):
                node = self.current_node.find_node(folder)
                if node:
                    self.current_node = node
                else:
                    parent = self.current_node.find_node(folder.parent)
                    self.current_node = parent.add_child(folder)
                try:
                    visitor.visit_node(self.current_node)
                except AttributeError:
                    pass
                    
            def visit_complete(self):
                try:
                    visitor.visit_complete()
                except AttributeError:
                    pass
                    
        self.folder.walk(visitor=Visitor(self))