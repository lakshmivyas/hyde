import os
import re
import sys
import urllib
import urllib2
from django.template.loader import render_to_string
from django.conf import settings
from file_system import File
from subprocess import check_call, CalledProcessError

class TemplateProcessor:
    @staticmethod
    def process(resource):
        try:
            rendered = render_to_string(resource.source_file.path, settings.CONTEXT)
            resource.source_file.write(rendered)
        except:
            print >> sys.stderr, \
            "***********************\nError while rendering page %s\n***********************" % \
            resource.url
            raise


## aym-cms code refactored into processors.
class CleverCSS:
    @staticmethod
    def process(resource):
        import clevercss
        data = resource.source_file.read_all()
        out = clevercss.convert(data)
        out_file = File(resource.source_file.path_without_extension + ".css")
        out_file.write(out)
        resource.source_file.delete()

class HSS:
    @staticmethod
    def process(resource):
        out_file = File(resource.source_file.path_without_extension + ".css")
        hss = settings.HSS_PATH
        if not hss or not os.path.exists(hss):
            raise ValueError("HSS Processor cannot be found at [%s]" % hss)
        try:
            check_call([hss, resource.source_file.path, "-output", out_file.parent.path + '/'])
        except CalledProcessError, e:
            print 'Syntax Error when calling HSS Processor:', e
            return None
        resource.source_file.delete()
        out_file.copy_to(resource.source_file.path)
        out_file.delete()

class SASS:
    @staticmethod
    def process(resource):
        out_file = File(resource.source_file.path_without_extension + ".css")
        load_path = os.path.dirname(resource.file.path)
        sass = settings.SASS_PATH
        if not sass or not os.path.exists(sass):
            raise ValueError("SASS Processor cannot be found at [%s]" % sass)
        try:
            check_call([sass, "-I", load_path, resource.source_file.path, out_file])
        except CalledProcessError, e:
            print 'Syntax Error when calling SASS Processor:', e
            return None
        resource.source_file.delete()
        resource.source_file = out_file

class LessCSS:
    @staticmethod
    def process(resource):
        out_file = File(resource.source_file.path_without_extension + ".css")
        if not out_file.parent.exists:
            out_file.parent.make()
        less = settings.LESS_CSS_PATH
        if not less or not os.path.exists(less):
            raise ValueError("Less CSS Processor cannot be found at [%s]" % less)
        try:
            check_call([less, resource.source_file.path, out_file.path])
        except CalledProcessError, e:
            print 'Syntax Error when calling less:', e
        else:
            resource.source_file.delete()

            """
            Assign our out_file as the source_file for this resource in order for
            other processors to be able to correctly process this resource too.

            This is needed because this processor changes the extension of the source file.

            See bugreport at http://support.ringce.com/ringce/topics/lesscss_yuicompressor_fail_and_sitemap_generation_broken
            """
            resource.source_file = out_file
        if not out_file.exists:
            print 'Error Occurred when processing with Less'

class Stylus:
    @staticmethod
    def process(resource):
        stylus = settings.STYLUS_PATH
        if not stylus or not os.path.exists(stylus):
            raise ValueError("Stylus Processor cannot be found at [%s]" % stylus)
        try:
            check_call([stylus, resource.source_file.path])
        except CalledProcessError, e:
            print 'Syntax Error when calling stylus:', e
        out_file = File(resource.source_file.path_without_extension + ".css")
        if not out_file.exists:
            print 'Error Occurred when processing with Stylus'
        else:
            resource.source_file.delete()
            resource.source_file = out_file

class CSSPrefixer:
    @staticmethod
    def process(resource):
        data = resource.source_file.read_all()
        try:
            import cssprefixer
            out = cssprefixer.process(data, debug=False, minify=False)
        except ImportError:
            try:
                data = urllib.urlencode({"css": resource.source_file.read_all()})
                req = urllib2.Request("http://cssprefixer.appspot.com/process/", data)
                out = urllib2.urlopen(req).read()
            except urllib2.HTTPError, e:
                print 'HTTP Error %s when calling remote CSSPrefixer' % e.code
                return False
            except urllib2.URLError, e:
                print 'Error when calling remote CSSPrefixer:', e.reason
                return False
        resource.source_file.write(out)

class CSSmin:
    @staticmethod
    def process(resource):
        import cssmin
        data = resource.source_file.read_all()
        out = cssmin.cssmin(data)
        resource.source_file.write(out)

class CoffeeScript:
    @staticmethod
    def process(resource):
        coffee = settings.COFFEE_PATH
        if not coffee or not os.path.exists(coffee):
            raise ValueError("CoffeeScript Processor cannot be found at [%s]" % coffee)
        try:
            check_call([coffee, "-b", "-c", resource.source_file.path])
        except CalledProcessError, e:
            print 'Syntax Error when calling CoffeeScript:', e
            return None
        out_file = File(resource.source_file.path_without_extension + ".js")
        if not out_file.exists:
            print 'Error Occurred when processing with CoffeeScript'
        else:
            resource.source_file.delete()
            resource.source_file = out_file

class JSmin:
    @staticmethod
    def process(resource):
        import jsmin
        data = resource.source_file.read_all()
        out = jsmin.jsmin(data)
        resource.source_file.write(out)

class UglifyJS:
    @staticmethod
    def process(resource):
        tmp_file = File(resource.source_file.path + ".z-tmp")
        if hasattr(settings, "UGLIFYJS"):
            compress = settings.UGLIFYJS
            if not os.path.exists(compress):
                compress = os.path.join(
                        os.path.dirname(
                        os.path.abspath(__file__)), "..", compress)

            try:
                check_call([compress, resource.source_file.path,
                            "--output", tmp_file.path])
            except CalledProcessError, e:
                print 'Syntax Error when calling UglifyJS:', e
                return False
        else:
            try:
                data = urllib.urlencode({"js_code": resource.source_file.read_all()})
                req = urllib2.Request("http://marijnhaverbeke.nl/uglifyjs", data)
                res = urllib2.urlopen(req).read()
                tmp_file.write(res)
            except urllib2.HTTPError, e:
                print 'HTTP Error %s when calling remote UglifyJS' % e.code
                return False
            except urllib2.URLError, e:
                print 'Error when calling remote UglifyJS:', e.reason
                return False
        resource.source_file.delete()
        tmp_file.move_to(resource.source_file.path)

class YUICompressor:
    @staticmethod
    def process(resource):
        if settings.YUI_COMPRESSOR == None:
            return
        compress = settings.YUI_COMPRESSOR
        if not os.path.exists(compress):
            compress = os.path.join(
                    os.path.dirname(
                    os.path.abspath(__file__)), "..", compress)

        if not compress or not os.path.exists(compress):
            raise ValueError(
            "YUI Compressor cannot be found at [%s]" % compress)

        tmp_file = File(resource.source_file.path + ".z-tmp")
        try:
            check_call(["java", "-jar", compress,
                resource.source_file.path, "-o",
                tmp_file.path])
        except CalledProcessError, e:
            print 'Syntax Error when calling YUI Compressor:', e
        else:
            resource.source_file.delete()
            tmp_file.move_to(resource.source_file.path)

class ClosureCompiler:
    @staticmethod
    def process(resource):
        tmp_file = File(resource.source_file.path + ".z-tmp")
        if hasattr(settings, "CLOSURE_COMPILER"):
            compress = settings.CLOSURE_COMPILER
            if not os.path.exists(compress):
                compress = os.path.join(
                        os.path.dirname(
                        os.path.abspath(__file__)), "..", compress)
            if not compress or not os.path.exists(compress):
                raise ValueError(
                "Closure Compiler cannot be found at [%s]" % compress)

            try:
                check_call(["java", "-jar", compress, "--js",
                    resource.source_file.path, "--js_output_file",
                    tmp_file.path])
            except CalledProcessError, e:
                print 'Syntax Error when calling Closure Compiler:', e
                return False
        else:
            try:
                data = urllib.urlencode({
                    "js_code": resource.source_file.read_all(),
                    "output_info": "compiled_code"
                })
                req = urllib2.Request("http://closure-compiler.appspot.com/compile", data)
                res = urllib2.urlopen(req).read()
                tmp_file.write(res)
            except urllib2.HTTPError, e:
                print 'HTTP Error %s when calling remote Closure Compiler' % e.code
                return False
            except urllib2.URLError, e:
                print 'Error when calling remote Closure Compiler:', e.reason
                return False
        resource.source_file.delete()
        tmp_file.move_to(resource.source_file.path)

class Thumbnail:
    @staticmethod
    def process(resource):
        from PIL import Image

        i = Image.open(resource.source_file.path)
        if i.mode != 'RGBA':
                i = i.convert('RGBA')
        i.thumbnail(
            (settings.THUMBNAIL_MAX_WIDTH, settings.THUMBNAIL_MAX_HEIGHT),
            Image.ANTIALIAS
        )

        orig_path, _, orig_extension = resource.source_file.path.rpartition('.')
        if "THUMBNAIL_FILENAME_POSTFIX" in dir(settings):
            postfix = settings.THUMBNAIL_FILENAME_POSTFIX
        else:
            postfix = "-thumb"
        thumb_path = "%s%s.%s" % (orig_path, postfix, orig_extension)

        if i.format == "JPEG" and "THUMBNAIL_JPEG_QUALITY" in dir(settings):
            i.save(thumb_path, quality = settings.THUMBNAIL_JPEG_QUALITY, optimize = True)
        else:
            i.save(thumb_path)
