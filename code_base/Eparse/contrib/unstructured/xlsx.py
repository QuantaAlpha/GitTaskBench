"""custom unstructured xlsx partition module using eparse"""

from tempfile import SpooledTemporaryFile
from typing import IO, BinaryIO, List, Optional, Union, cast

import lxml.html
from unstructured.documents.elements import (
    DataSourceMetadata,
    Element,
    ElementMetadata,
    Table,
    process_metadata,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
    spooled_to_bytes_io_if_needed,
)

from eparse.core import df_serialize_table, get_df_from_file, get_table_digest

_eparse_modes = (
    "eparse",
    "digest",
    "table-digest",
    "unstructured",
)


@process_metadata()
@add_metadata_with_filetype(FileType.XLSX)
def partition_xlsx(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    metadata_last_modified: Optional[str] = None,
    include_header: bool = True,
    **kwargs,
) -> List[Element]:
    """Partitions Microsoft Excel Documents in .xlsx format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_metadata
        Determines whether or not metadata is included in the output.
    metadata_last_modified
        The day of the last modification
    include_header
        Determines whether or not header info info is included in text and medatada.text_as_html
    """
    exactly_one(filename=filename, file=file)
    last_modification_date = None
    if filename:
        tables = get_df_from_file(filename)
        last_modification_date = get_last_modified_date(filename)

    elif file:
        f = spooled_to_bytes_io_if_needed(
            cast(Union[BinaryIO, SpooledTemporaryFile], file),
        )
        tables = get_df_from_file(f)
        last_modification_date = get_last_modified_date_from_file(file)

    elements: List[Element] = []
    eparse_mode: Optional[str] = kwargs.pop("eparse_mode", None)
    eparse_max_rows: Optional[int] = kwargs.pop("eparse_max_rows", 75)
    eparse_max_cols: Optional[int] = kwargs.pop("eparse_max_cols", 20)
    table_number = 0
    for table, excel_RC, table_name, sheet_name in tables:
        table_number += 1
        html_text = table.to_html(index=False, header=include_header, na_rep="")

        if include_metadata:
            datasource_metadata = DataSourceMetadata(
                record_locator={
                    "excel_RC": excel_RC,
                    "table_name": table_name,
                },
            )
            metadata = ElementMetadata(
                text_as_html=html_text,
                page_name=sheet_name,
                page_number=table_number,
                filename=metadata_filename or filename,
                last_modified=metadata_last_modified or last_modification_date,
                data_source=datasource_metadata,
            )
        else:
            metadata = ElementMetadata()

        text = ""

        if eparse_mode == "eparse":
            text = str(table.iloc[:eparse_max_rows, :eparse_max_cols])

            if "digest" in eparse_mode:
                digest = get_table_digest(
                    df_serialize_table(table),
                    table_name=table_name,
                )
                if eparse_mode == "table-digest":
                    text = (
                        f"{table_name} is a spreadsheet table. This is "
                        f"the head of the table:\n{table.head(eparse_max_rows)}\n"
                        f"Summary: {digest}."
                    )
                else:
                    text = digest

        elif eparse_mode == "unstructured":
            text = lxml.html.document_fromstring(html_text).text_content()

        table = Table(text=text, metadata=metadata)
        elements.append(table)

    return elements


if __name__ == "__main__":
    try:
        partition_xlsx("tests/eparse_unit_test_data.xlsx")
    except Exception as e:
        print(f"xlsx failed with {e}")
