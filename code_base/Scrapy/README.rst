.. image:: https://scrapy.org/img/scrapylogo.png
   :target: https://scrapy.org/

======
Scrapy
======

.. image:: https://img.shields.io/pypi/v/Scrapy.svg
   :target: https://pypi.org/pypi/Scrapy
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/Scrapy.svg
   :target: https://pypi.org/pypi/Scrapy
   :alt: Supported Python Versions

.. image:: https://github.com/scrapy/scrapy/workflows/Ubuntu/badge.svg
   :target: https://github.com/scrapy/scrapy/actions?query=workflow%3AUbuntu
   :alt: Ubuntu

.. .. image:: https://github.com/scrapy/scrapy/workflows/macOS/badge.svg
   .. :target: https://github.com/scrapy/scrapy/actions?query=workflow%3AmacOS
   .. :alt: macOS


.. image:: https://github.com/scrapy/scrapy/workflows/Windows/badge.svg
   :target: https://github.com/scrapy/scrapy/actions?query=workflow%3AWindows
   :alt: Windows

.. image:: https://img.shields.io/badge/wheel-yes-brightgreen.svg
   :target: https://pypi.org/pypi/Scrapy
   :alt: Wheel Status

.. image:: https://img.shields.io/codecov/c/github/scrapy/scrapy/master.svg
   :target: https://codecov.io/github/scrapy/scrapy?branch=master
   :alt: Coverage report

.. image:: https://anaconda.org/conda-forge/scrapy/badges/version.svg
   :target: https://anaconda.org/conda-forge/scrapy
   :alt: Conda Version


Overview
========

Scrapy is a BSD-licensed fast high-level web crawling and web scraping framework, used to
crawl websites and extract structured data from their pages. It can be used for
a wide range of purposes, from data mining to monitoring and automated testing.

Scrapy is maintained by Zyte_ (formerly Scrapinghub) and `many other
contributors`_.

.. _many other contributors: https://github.com/scrapy/scrapy/graphs/contributors
.. _Zyte: https://www.zyte.com/

Check the Scrapy homepage at https://scrapy.org for more information,
including a list of features.


Requirements
============

* Python 3.9+
* Works on Linux, Windows, macOS, BSD

Install
=======

The quick way:

.. code:: bash

    pip install scrapy

See the install section in the documentation at
https://docs.scrapy.org/en/latest/intro/install.html for more details.

Documentation
=============

Documentation is available online at https://docs.scrapy.org/ and in the ``docs``
directory.

Walk-through of an Example Spider
================================

In order to show you what Scrapy brings to the table, we’ll walk you through an example of a Scrapy Spider using the simplest way to run a spider.

Here’s the code for a spider that scrapes famous quotes from the website https://quotes.toscrape.com, following the pagination:

```python
import scrapy


class QuotesSpider(scrapy.Spider):
    name = "quotes"
    start_urls = [
        "https://quotes.toscrape.com/tag/humor/",
    ]

    def parse(self, response):
        for quote in response.css("div.quote"):
            yield {
                "author": quote.xpath("span/small/text()").get(),
                "text": quote.css("span.text::text").get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)
Put this in a text file, name it something like quotes_spider.py, and run the spider using the runspider command:

.. code:: bash
scrapy runspider quotes_spider.py -o quotes.jsonl
When this finishes, you will have in the quotes.jsonl file a list of the quotes in JSON Lines format, containing the text and author. Here is an example of how the file will look:
{"author": "Jane Austen", "text": "\u201cThe person, be it gentleman or lady, who has not pleasure in a good novel, must be intolerably stupid.\u201d"}
{"author": "Steve Martin", "text": "\u201cA day without sunshine is like, you know, night.\u201d"}
{"author": "Garrison Keillor", "text": "\u201cAnyone who thinks sitting in church can make you a Christian must also think that sitting in a garage can make you a car.\u201d"}
...


Releases
========

You can check https://docs.scrapy.org/en/latest/news.html for the release notes.

Community (blog, twitter, mail list, IRC)
=========================================

See https://scrapy.org/community/ for details.

Contributing
============

See https://docs.scrapy.org/en/master/contributing.html for details.

Code of Conduct
---------------

Please note that this project is released with a Contributor `Code of Conduct <https://github.com/scrapy/scrapy/blob/master/CODE_OF_CONDUCT.md>`_.

By participating in this project you agree to abide by its terms.
Please report unacceptable behavior to opensource@zyte.com.

Companies using Scrapy
======================

See https://scrapy.org/companies/ for a list.

Commercial Support
==================

See https://scrapy.org/support/ for details.
