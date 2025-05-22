"""custom unstructured auto partition using eparse"""

from typing import IO, Callable, Dict, List, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.file_utils.filetype import FileType, detect_filetype
from unstructured.logger import logger
from unstructured.partition.auto import file_and_type_from_url
from unstructured.partition.auto import partition as unstructured_partition_auto
from unstructured.partition.common import exactly_one

from eparse.contrib.unstructured.xlsx import partition_xlsx as eparse_partition_xlsx


def partition(
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    file_filename: Optional[str] = None,
    url: Optional[str] = None,
    include_page_breaks: bool = False,
    strategy: str = "auto",
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    headers: Dict[str, str] = {},
    skip_infer_table_types: List[str] = ["pdf", "jpg", "png"],
    ssl_verify: bool = True,
    ocr_languages: str = "eng",
    pdf_infer_table_structure: bool = False,
    xml_keep_tags: bool = False,
    data_source_metadata: Optional[DataSourceMetadata] = None,
    **kwargs,
):
    """Partitions a document into its constituent elements. Will use libmagic to determine
    the file's type and route it to the appropriate partitioning function. Applies the default
    parameters for each partitioning function. Use the document-type specific partitioning
    functions if you need access to additional kwarg options.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    content_type
        A string defining the file content in MIME type
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    file_filename
        When file is not None, the filename (string) to store in element metadata. E.g. "foo.txt"
    url
        The url for a remote document. Pass in content_type if you want partition to treat
        the document as a specific content_type.
    include_page_breaks
        If True, the output will include page breaks if the filetype supports it
    strategy
        The strategy to use for partitioning PDF/image. Uses a layout detection model if set
        to 'hi_res', otherwise partition simply extracts the text from the document
        and processes it.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    headers
        The headers to be used in conjunction with the HTTP request if URL is set.
    skip_infer_table_types
        The document types that you want to skip table extraction with.
    ssl_verify
        If the URL parameter is set, determines whether or not partition uses SSL verification
        in the HTTP request.
    ocr_languages
        The languages to use for the Tesseract agent. To use a language, you'll first need
        to isntall the appropriate Tesseract language pack.
    pdf_infer_table_structure
        If True and strategy=hi_res, any Table Elements extracted from a PDF will include an
        additional metadata field, "text_as_html," where the value (string) is a just a
        transformation of the data into an HTML <table>.
        The "text" field for a partitioned Table Element is always present, whether True or False.
    xml_keep_tags
        If True, will retain the XML tags in the output. Otherwise it will simply extract
        the text from within the tags. Only applies to partition_xml.
    """

    exactly_one(file=file, filename=filename, url=url)

    if url is not None:
        file, filetype = file_and_type_from_url(
            url=url,
            content_type=content_type,
            headers=headers,
            ssl_verify=ssl_verify,
        )
    else:
        if headers != {}:
            logger.warning(
                "The headers kwarg is set but the url kwarg is not. "
                "The headers kwarg will be ignored.",
            )
        filetype = detect_filetype(
            filename=filename,
            file=file,
            file_filename=file_filename,
            content_type=content_type,
            encoding=encoding,
        )

    if file is not None:
        file.seek(0)

    eparse_mode = kwargs.pop("eparse_mode", None)
    fcn = unstructured_partition_auto
    is_xlsx = filetype in (FileType.XLS, FileType.XLSX)

    if is_xlsx and eparse_mode not in (None, "unstructured"):
        fcn = eparse_partition_xlsx
        kwargs["eparse_mode"] = eparse_mode

    if file is not None and file_filename is not None:
        kwargs.setdefault("metadata_filename", file_filename)

    return fcn(
        filename=filename,
        content_type=content_type,
        file=file,
        file_filename=file_filename,
        url=url,
        include_page_breaks=include_page_breaks,
        strategy=strategy,
        encoding=encoding,
        paragraph_grouper=paragraph_grouper,
        headers=headers,
        skip_infer_table_types=skip_infer_table_types,
        ssl_verify=ssl_verify,
        ocr_languages=ocr_languages,
        pdf_infer_table_structure=pdf_infer_table_structure,
        xml_keep_tags=xml_keep_tags,
        data_source_metadata=data_source_metadata,
        **kwargs,
    )
