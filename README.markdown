**Note:**
While this remains the most complete and functional version of hyde, the new
version (potentially 1.0) is [under heavy development](https://github.com/hyde/hyde).

# HYDE

0.5.3

This document should give enough information to get you up and running. Check
the [wiki](http://wiki.github.com/lakshmivyas/hyde) for detailed documentation.
To use Clyde, the online content editor for hyde see the
[clyde readme](http://github.com/lakshmivyas/hyde/tree/master/clydeweb/).

Hyde is a static website generator with the power of Django templates behind it.
You can read more about its conception, history and features [here][1] and
[here][2].

[1]: http://www.ringce.com/products/hyde/hyde.html
[2]: http://www.ringce.com/blog/2009/introducing_hyde.html


## Basic Installation

Get the hyde source by cloning this repository.

The very basic installation of hyde only needs Django, Markdown and pyYAML. More
python goodies are needed based on the features you may use.

    pip install -r requirements.txt


## Running with Hyde

The hyde engine has three entry points:

1. Initializer

        python hyde.py -i -s path/to/your/site [-t template_name = default] [-f]

    During initialization hyde creates a basic website by copying the specified
    template (or default). This template contains the skeleton site layout, some
    content pages and settings.py.

    Be careful with the -f setting, though: it will overwrite your website.


2. Generator

        python hyde.py -g -s path/to/your/site [-d deploy_dir=path/to/your/site/deploy] [-k]

    This will process the content and media and copy the generated website to your deploy directory.

    If the -k option is specified, hyde will monitor the source folder for changes and automatically process them when the changes are encountered. This option is very handy when tweaking css or markup to quickly check the results. Note of caution: This option does not update listing files or excerpt files. It is recommended that you run -g again before you deploy the website.

    If you are on Mac OS X and would like to get Growl notifications, just set the GROWL setting to the `growlnotify` script path.

3. Web Server

        python hyde.py -w -s path/to/your/site [-d deploy_dir=path/to/your/site/deploy]

    This will start an instance of a cherrypy server and serve the generated website at localhost:8080.


## Site structure

* layout - Template files that are used as base templates for content. None of the files in the layout folder are copied over to the deploy directory.
* content - Any file that is not prefixed with \_, . or suffixed with ~ are processed by running through the template engine.
* media - Contains site media, css, js and images.
* settings.py - Django and hyde settings.

### Recommended conventions

These conventions will make it easier to configure hyde plugins.

* Prefix files in layout and other template files in content with underscores
* Keep media folder organized by file type[css, flash, js, images].

## Configuring your website

Most of the boilerplate configuration comes as a part of the initialized website. The only setting you _have to_ override is the SITE_NAME setting.


### Media Processors

Media processors are defined in the following format:

    {<folder>:{
        <file_extension_with_dot>:(<processor_module_name1>, <processor_module_name2>)}
    }

The processors are executed in the order in which they are defined. The output from the first processor becomes the input of the next.

A \* instead of folder will apply the setting to all folders. There is no wildcard support for folder name yet, \* is just a catch all special case.

File extensions should be specified as .css, .js, .png etc. Again no wildcard support yet.

Hyde retains the YUI Compressor, Clever CSS and HSS processors from aym-cms.

#### Template Processor

Template processor allows the use of context variables inside your media files.

#### YUI Compressor

Runs through all the files defined in the configuration associated with ``'hydeengine.media_processors.YUICompressor'`` and compresses them.

[yuic]: http://developer.yahoo.com/yui/compressor/

In the settings file, set ``YUI_COMPRESSOR`` to
the path of a [YUI Compressor][yuic] jar on your computer.

#### Closure Compiler

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.ClosureCompiler'`` and compresses them.

[closure]: http://closure-compiler.googlecode.com/

In the settings file, set ``CLOSURE_COMPILER`` to
the path of [Closure Compiler][closure] jar on your computer
if you don't want to use the hosted Google Closure Compiler service.

#### UglifyJS

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.UglifyJS'`` and compresses them.

[uglifyjs]: http://marijn.haverbeke.nl/uglifyjs/

In the settings file, set ``UGLIFYJS`` to
the path of [UglifyJS][uglifyjs] script on your computer
if you don't want to use the hosted UglifyJS service.

#### Clever CSS Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.CleverCSS'`` and converts them to css.

You need to install Clever CSS using ``sudo easy_install CleverCSS`` command for this processor to work.

[clever_css]: http://sandbox.pocoo.org/clevercss/

#### HSS Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.HSS'`` and converts them to css.

You need to download HSS from [the project website][hss] and set the ``HSS_PATH`` variable to the downloaded path. A version for OS X is installed in the ``lib`` folder by default. To use it, just uncomment the ``HSS_PATH`` line in the settings.py file of your template.

[hss]: http://ncannasse.fr/projects/hss

#### SASS Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.SASS'`` and converts them to css.

You need to install SASS (see [the project website][sass]) and set the ``SASS_PATH`` variable to the path to the ``sass`` script.

[sass]: http://sass-lang.com/

#### Less CSS Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.LessCSS'`` and converts them to css.

You need to install Less (see [the project website][lesscss]) and set the ``LESS_CSS_PATH`` variable to the path to the ``lessc`` script.

[lesscss]: http://lesscss.org/

#### Stylus Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.Stylus'`` and converts them to css.

You need to install Stylus (see [the project website][stylus]) and set the ``STYLUS_PATH`` variable to the path to the ``stylus`` script.

[stylus]: http://learnboost.github.com/stylus/

#### CSSPrefixer Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.CSSPrefixer'`` and adds vendor prefixed versions of CSS3 rules.

You need to install [CSSPrefixer][cssprefixer] using ``sudo easy_install cssprefixer`` command
if you don't want to use the hosted CSSPrefixer service.

[cssprefixer]: http://cssprefixer.appspot.com

#### CSSmin Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.CSSmin'`` and minifies them.

You need to install [cssmin][cssmin] using ``sudo easy_install cssmin`` command for this processor to work.

[cssmin]: http://github.com/zacharyvoase/cssmin

#### CoffeeScript Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.CoffeeScript'`` and converts them to javascript.

You need to install CoffeeScript (see [the project website][coffeescript]) and set the ``COFFEE_PATH`` variable to the path to the ``coffee`` script.

[coffeescript]: http://jashkenas.github.com/coffee-script/

#### JSmin Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.JSmin'`` and minifies them.

You need to install [jsmin][jsmin] using ``sudo easy_install jsmin`` command for this processor to work.

[jsmin]: http://pypi.python.org/pypi/jsmin

#### Thumbnail Processor

Runs through the all the files defined in the configuration associated with ``'hydeengine.media_processors.Thumbnail'`` and creates small "thumbnailed" copies. The aspect ratios of the images will be preserved.

You need to install the [Python Imaging Library][PIL] with the ``sudo easy_install PIL`` command.

You also need to set the ``THUMBNAIL_MAX_WIDTH`` and ``THUMBNAIL_MAX_HEIGHT`` variables.

You can set the ``THUMBNAIL_FILENAME_POSTFIX`` to change the string that is appended to the filename of thumbnails. By default this is ``-thumb`` (i.e. the thumbnail of ``my-image.png`` will be called ``my-image-thumb.png``).

You can optionally set the ``THUMBNAIL_JPEG_QUALITY`` (between 0 and 100) to control the JPEG compression quality.

[PIL]: http://www.pythonware.com/products/pil/

### Content Processors

Content processors are run against all files in the content folder whereas the media processors are run against the media folder. No content processors have been created yet.


## Page Context Variables

Pages can define their own context variables that are passed to the entire template hierarchy when the page is processed. This is accomplished by using a special tag at the top of the content page(after any extends tags you may have).

    {%hyde
        <Your variables>
    %}

Every page in the template hierarchy gets these context variables: ``site`` and ``page``. The site variable contains information about the entire site. The ``page`` variable represents the current content page that is being processed. The variables defined at the top of the content pages using the {% hyde %} tags are available through the page variable as attributes.

On your content pages you can define the page variables using the standard YAML format.

    {%hyde
        title: A New Post
        list:
            - One
            - Two
            - Three
    %}

## Template Tags

Hyde retains the markdown and syntax template tags from aym_cms. Additionally hyde introduces a few tags for excerpts. These tags are added to the Django built in tags so there is no need for the load statements.

### Markdown

Requires markdown to be installed.

    sudo easy_install markdown

``markdown`` renders the enclosed text as [Markdown](http://daringfireball.net/projects/markdown/) markup.
It is used as follows:

    <p> I love templates. </p>
    {% markdown %}
    Render this **content all in Markdown**.

    >> Writing in Markdown is quicker than
    >> writing in HTML.

    1.  Or at least that is my opinion.
    2.  What about you?
    {% endmarkdown %}

#### Markdown2

Hyde also supports markdown2 with the `{%markdown2%}{%endmarkdown2%}` block template tag.


### Textile

Requires textile to be installed.

    sudo easy_install textile

``textile`` renders the enclosed text as [Textile](http://www.textism.com/tools/textile/) markup.
It is used as follows:

    <p> I love templates. </p>
    {% textile %}
    Render this *content all in Textile*.

    bq.  Writing in Textile is also quicker than
         writing in HTML.

    # Or at least that is my opinion.
    # What about you?

    {% endtextile %}


### reStructuredText

Requires docutils to be installed.

    sudo easy_install docutils

``restructuredtext`` renders the enclosed text as [reStructuredText](http://docutils.sourceforge.net/rst.html) markup.
It is used as follows:

    <p> I love templates. </p>
    {% restructuredtext %}
    Render this **content all in reStructuredText**.

         Writing in reStructuredText is also quicker than
         writing in HTML.

    #. Or at least that is my opinion.
    #. What about you?

    {% endrestructuredtext %}

The default reStructuredText settings may be changed by assigning a dictionary of setting names and values to the ``RST_SETTINGS_OVERRIDES`` setting in the settings file.  For information on the various configuration options, see the [docutils configuration documentation](http://docutils.sourceforge.net/docs/user/config.html).


### asciidoc

Requires asciidoc to be installed.

``asciidoc`` renders the enclosed text as [asciidoc](http://www.methods.co.nz/asciidoc/) markup.
It is used as follows:

    <p> I love templates. </p>
    {% asciidoc %}
    Render this *content all in asciidoc*.

    ________________________________________
    Writing in asciidoc is also quicker than
    writing in HTML.
    ________________________________________

    . Or at least that is my opinion.
    . What about you?

    {% endasciidoc %}


### Syntax

Requires Pygments.

    sudo easy_install Pygments

``syntax`` uses Pygments to render the enclosed text with
a code syntax highlighter. Usage is:

    <del>{% load aym %}</del>
    <p> blah blah blah </p>
    {% syntax objc %}
    [obj addObject:[NSNumber numberWithInt:53]];
    return [obj autorelease];
    {% endsyntax %}

To generate the corresponding CSS, first list the available styles

    python
    >>> from pygments.styles import get_all_styles
    >>> list(get_all_styles())
    ['manni', 'perldoc', 'borland', 'colorful', 'default', 'murphy', 'vs', 'trac', 'tango', 'fruity', 'autumn', 'bw', 'emacs', 'pastie', 'friendly', 'native']

Then choose a style and generate a style sheet

    pygmentize -f html -S native -a .highlight > pygments.css

They are both intended to make writing static content
quicker and less painful.

### Hyde

The ``{%hyde%}`` tag is used for the page variables, as a template tag all it does is swallow the contents and prevent them from showing up in the html. The even safer approach is to define this tag outside of all blocks so that it is automatically ignored.

### Excerpt

The ``{%excerpt%}{%endexcerpt%}`` tag decorates the output with html comments that mark the excerpt area. Excerpts marked in this manner can be referenced in other pages using the ``{%render_excerpt%}`` or the ``{%latest_excerpt%}`` tag.

### Render Excerpt

Render Excerpt takes a page variable and optional number of words argument to render the excerpt from the target page.

### Latest Excerpt

Latest Excerpt takes a content folder path and optional number of words as input. It parses through the content pages looking for page variables named ``created`` and gets the page with the maximum value and renders the excerpt from that page.

### Article

The ``{%article%}{%endarticle%}`` tags mark content enclosed in them to be included as inline content when the atom feed is generated.

### Render Article

Render Article renders the html content bracketed by the `{%article%}` tag from the given page.

### Typogrify

To enable Typogrify, use ``{% filter typogrify %}`` in your code. Typogrify is "a collection of Django template filters that help prettify your web typography by preventing ugly quotes and widows", according to the [project web site][typogrify_site]. It is automatically enabled in the default template. Some features require you to have [smartypants] installed.

[typogrify_site]:http://code.google.com/p/typogrify/
[smartypants]:http://web.chad.org/projects/smartypants.py/


## Preprocessors

Main information about preprocessors can be found in
[hyde wiki]:https://github.com/lakshmivyas/hyde/wiki/Site-Preprocessors

### Properties inclusion

Is preprocessor that includes new properties into nodes.
Simple configuration:
  SITE_PRE_PROCESSORS = {
      '/': {
        'hydeengine.site_pre_processors.TranslationManager': {
          'include' : {
             'node_field': {'field':'page_field','fallback':'node_field2'}
          }
        }
    }
  }

Processors find listing page for node and then include page.field into node.node_field, and if there is no title it falls back to node.node_field2 field.
One can use it for translation, for example use field: page_field on native language and the use node field in template (to overcome node.name) or even add additiona menu_title to give title name to module.
N.B. you should explisitly create listing page otherwise preprocessor will not add any attribute to node.

## Base Templates

There are two layouts currently available: default and simple.

The default site layout contains templates for basic site structure, navigation, breadcrumbs, listing, posts and Atom feed and a very basic stylesheet.


# Examples

The following websites are built using hyde and are open sourced.

* [SteveLosh.com][stevelosh]
* [The Old Ringce Website][ringce]

[stevelosh]:http://github.com/sjl/stevelosh
[ringce]:http://github.com/lakshmivyas/ringce


# CONTRIBUTORS

(Please let me know if I have missed someone here.)

- [lakshmivyas](http://github.com/lakshmivyas)
- [joshrosen](http://github.com/JoshRosen)
- [Harry Lachenmayer](http://github.com/h3yl9r)
- [Kailoa Kadano](http://github.com/kailoa)
- [Tom von Schwerdtner](http://github.com/tvon)
- [montecristo](http://github.com/montecristo)
- [dbr/Ben](https://github.com/dbr)
- [Valentin Jacquemin](http://github.com/poxd)
- [Johannes Reinhard](http://github.com/SpeckFleck)
- [Steve Losh](http://github.com/sjl)
- [William Amberg](http://github.com/wamberg)
- [James Clarke](http://github.com/jc)
- [Benjamin Pollack](http://github.com/bpollack)
- [Andrey](http://github.com/andrulik)
- [Toby White](http://github.com/tow)
- [Tim Freund](http://github.com/timfreund)
- [Russell Haering](http://github.com/russellhaering)
- [timo](http://github.com/timo)
- [Alex Schworer](http://github.com/schworer)
- [holmboe](http://github.com/holmboe)
- [James Wilcox](http://github.com/snorp)
- [Hugo Vincent](http://github.com/hugovincent)
- [Örjan Persson](http://github.com/op)
- [Ken](http://github.com/xythian)
- [Nico Mandery](http://github.com/nmandery)
- [Chetan Surpur](http://github.com/chetan51)
- [Pascal Widdershoven](https://github.com/PascalW)
- [Kai](https://github.com/limist)
- [myfreeweb](http://github.com/myfreeweb)
- [Paul Bonser](https://github.com/pib)
- [Yoann Pigné](https://github.com/pigne)
- [Hubert HANGHOFER](https://github.com/brewbert)
- [sirex](https://github.com/sirex)
- [Alexander Vershilov](https://github.com/qnikst)
- [Boris Smus](https://github.com/borismus)
