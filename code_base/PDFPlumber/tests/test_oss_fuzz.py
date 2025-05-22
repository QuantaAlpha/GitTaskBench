#!/usr/bin/env python
import logging
import os
import unittest
from pathlib import Path

import pdfplumber
from pdfplumber.utils.exceptions import MalformedPDFException, PdfminerException

logging.disable(logging.ERROR)

HERE = Path(os.path.abspath(os.path.dirname(__file__)))

ACCEPTABLE_EXCEPTIONS = (MalformedPDFException, PdfminerException)


class Test(unittest.TestCase):
    def test_load(self):
        def test_conversions(pdf):
            methods = [pdf.to_dict, pdf.to_json, pdf.to_csv, pdf.pages[0].to_image]
            for method in methods:
                try:
                    method()
                except ACCEPTABLE_EXCEPTIONS:
                    continue
                except Exception as e:
                    print(f"Failed on: {path.name}")
                    raise e

        paths = sorted((HERE / "pdfs/from-oss-fuzz/load/").glob("*.pdf"))
        for path in paths:
            try:
                with pdfplumber.open(path) as pdf:
                    assert pdf.pages
                    test_conversions(pdf)
            except ACCEPTABLE_EXCEPTIONS:
                continue
            except Exception as e:
                print(f"Failed on: {path.name}")
                raise e
