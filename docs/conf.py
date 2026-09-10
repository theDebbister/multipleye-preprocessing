# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from datetime import UTC, datetime

# from sphinx.search import languages

project = "MultiplEYE Preprocessing pEYEpline"
copyright = f"2024–{datetime.now(tz=UTC).year}, Deborah N. Jakobi et al"
author = "Deborah N. Jakobi et al."
release = "2026.09.09"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_nb",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.autosectionlabel",
    "sphinxcontrib.bibtex",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

bibtex_bibfiles = ["refs.bib"]
bibtex_encoding = "utf-8"
bibtex_default_style = "alpha"

language = "en"

myst_enable_extensions = ["colon_fence", "deflist", "dollarmath", "amsmath"]
myst_links_external_new_tab = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
html_js_files = ["custom-icons.js", "faq-search.js"]
html_css_files = ["custom.css"]
html_sidebars = {
    "**": [
        "navbar-logo.html",
        "icon-links.html",
        "search-button-field.html",
        "sbt-sidebar-nav.html",
    ],
    "index": ["navbar-logo.html", "icon-links.html", "search-button-field.html"],
}
html_logo_path = "_static/logo.svg"
html_favicon = "_static/favicon.svg"
html_theme_options = {
    "repository_url": "https://github.com/MultiplEYE-COST/multipleye-preprocessing/",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "path_to_docs": "docs",
    "navbar_persistent": [],
    "icon_links": [
        {
            "name": "MultiplEYE",
            "url": "https://multipleye.eu/",
            "icon": "fa-solid fa-eye",
            "type": "fontawesome",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/MultiplEYE-COST/multipleye-preprocessing",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
        {
            "name": "Digital Linguistics Group",
            "url": "https://www.cl.uzh.ch/en/research-groups/digital-linguistics.html",
            "icon": "fa-solid fa-graduation-cap",
            "type": "fontawesome",
        },
        {
            "name": "PyMovements",
            "url": "https://pymovements.readthedocs.io/",
            "icon": "fa-custom fa-pymovements",
            "type": "fontawesome",
        },
    ],
    "logo": {
        "image_light": "_static/logo.svg",
        "image_dark": "_static/logo.svg",
    },
}
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "pymovements": ("https://pymovements.readthedocs.io/en/stable/", None),
}
