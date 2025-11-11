"""
File parsing utilities for different document formats.
Supports PDF, TXT, and DOCX files.
"""
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

from app.core.exceptions import DocumentProcessingError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FileParser:
    """Parser for various file formats."""

    @staticmethod
    async def parse_file(file_path: str, content_type: str) -> str:
        """
        Parse a file and extract text content.

        Args:
            file_path: Path to the file
            content_type: MIME type of the file

        Returns:
            Extracted text content

        Raises:
            DocumentProcessingError: If parsing fails
        """
        try:
            if content_type == "application/pdf" or file_path.endswith(".pdf"):
                return await FileParser.parse_pdf(file_path)
            elif content_type == "text/plain" or file_path.endswith(".txt"):
                return await FileParser.parse_txt(file_path)
            elif content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"] or file_path.endswith(".docx"):
                return await FileParser.parse_docx(file_path)
            else:
                raise DocumentProcessingError(
                    f"Unsupported file type: {content_type}",
                    details={"content_type": content_type}
                )

        except Exception as e:
            logger.error("file_parsing_failed", file_path=file_path, error=str(e))
            raise DocumentProcessingError(
                f"Failed to parse file: {str(e)}",
                details={"file_path": file_path, "error": str(e)}
            )

    @staticmethod
    async def parse_pdf(file_path: str) -> str:
        """
        Parse a PDF file and extract text.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            reader = PdfReader(file_path)
            text_content = []

            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    logger.debug("pdf_page_parsed", page_num=page_num, chars=len(text))

            full_text = "\n\n".join(text_content)
            logger.info("pdf_parsed", file_path=file_path, pages=len(reader.pages), chars=len(full_text))

            return full_text

        except Exception as e:
            logger.error("pdf_parsing_failed", file_path=file_path, error=str(e))
            raise DocumentProcessingError(f"PDF parsing failed: {str(e)}")

    @staticmethod
    async def parse_txt(file_path: str) -> str:
        """
        Parse a text file.

        Args:
            file_path: Path to text file

        Returns:
            Text content
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info("txt_parsed", file_path=file_path, chars=len(content))
            return content

        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()
                    logger.info("txt_parsed_with_encoding", file_path=file_path, encoding=encoding)
                    return content
                except UnicodeDecodeError:
                    continue

            raise DocumentProcessingError("Unable to decode text file with any supported encoding")

        except Exception as e:
            logger.error("txt_parsing_failed", file_path=file_path, error=str(e))
            raise DocumentProcessingError(f"Text file parsing failed: {str(e)}")

    @staticmethod
    async def parse_docx(file_path: str) -> str:
        """
        Parse a DOCX file.

        Args:
            file_path: Path to DOCX file

        Returns:
            Extracted text content
        """
        try:
            # For now, return a placeholder
            # In production, use python-docx library
            logger.warning("docx_parsing_not_implemented", file_path=file_path)
            return "DOCX parsing not yet implemented. Please convert to PDF or TXT."

        except Exception as e:
            logger.error("docx_parsing_failed", file_path=file_path, error=str(e))
            raise DocumentProcessingError(f"DOCX parsing failed: {str(e)}")

    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Get file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information
        """
        path = Path(file_path)

        return {
            "name": path.name,
            "size": path.stat().st_size if path.exists() else 0,
            "extension": path.suffix,
            "exists": path.exists()
        }
