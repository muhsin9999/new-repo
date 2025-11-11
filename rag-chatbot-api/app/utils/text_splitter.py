"""
Text splitting utilities for chunking documents.
Implements recursive character splitting with overlap.
"""
import re
from typing import List

import tiktoken

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TextSplitter:
    """
    Text splitter for chunking documents intelligently.
    Uses recursive character splitting with configurable chunk size and overlap.
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None
    ):
        """
        Initialize text splitter.

        Args:
            chunk_size: Maximum chunk size in tokens (default from settings)
            chunk_overlap: Number of overlapping tokens (default from settings)
            separators: List of separators to use for splitting
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # Default separators in order of preference
        self.separators = separators or [
            "\n\n\n",  # Multiple newlines (section breaks)
            "\n\n",    # Double newlines (paragraph breaks)
            "\n",      # Single newlines
            ". ",      # Sentences
            "! ",
            "? ",
            "; ",
            ": ",
            ", ",      # Clauses
            " ",       # Words
            ""         # Characters (fallback)
        ]

        # Initialize tokenizer for accurate token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        except Exception as e:
            logger.warning("tokenizer_init_failed", error=str(e))
            self.tokenizer = None

    def split_text(self, text: str) -> List[dict]:
        """
        Split text into chunks.

        Args:
            text: Text to split

        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text:
            return []

        chunks = self._recursive_split(text, self.separators)

        # Create chunk objects with metadata
        chunk_objects = []
        for idx, chunk_text in enumerate(chunks):
            chunk_objects.append({
                "content": chunk_text,
                "index": idx,
                "token_count": self._count_tokens(chunk_text),
                "char_count": len(chunk_text)
            })

        logger.info(
            "text_split_complete",
            total_chunks=len(chunk_objects),
            total_tokens=sum(c["token_count"] for c in chunk_objects)
        )

        return chunk_objects

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """
        Recursively split text using separators.

        Args:
            text: Text to split
            separators: List of separators to try

        Returns:
            List of text chunks
        """
        final_chunks = []

        # Get the first separator to try
        separator = separators[0] if separators else ""

        # Split by the separator
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        # Process each split
        current_chunk = ""
        for split in splits:
            # Check if adding this split would exceed chunk size
            test_chunk = current_chunk + (separator if current_chunk else "") + split
            test_chunk_tokens = self._count_tokens(test_chunk)

            if test_chunk_tokens <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk if it exists
                if current_chunk:
                    final_chunks.append(current_chunk)

                # If split is still too large and we have more separators, recurse
                if self._count_tokens(split) > self.chunk_size and len(separators) > 1:
                    sub_chunks = self._recursive_split(split, separators[1:])
                    final_chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split

        # Add the last chunk
        if current_chunk:
            final_chunks.append(current_chunk)

        # Add overlap between chunks
        if len(final_chunks) > 1:
            final_chunks = self._add_overlap(final_chunks)

        return final_chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """
        Add overlap between consecutive chunks.

        Args:
            chunks: List of text chunks

        Returns:
            List of chunks with overlap
        """
        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        overlapped_chunks = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # Get overlap from previous chunk
                prev_chunk = chunks[i - 1]
                prev_tokens = self._tokenize(prev_chunk)

                if len(prev_tokens) > self.chunk_overlap:
                    overlap_tokens = prev_tokens[-self.chunk_overlap:]
                    overlap_text = self._detokenize(overlap_tokens)
                    overlapped_chunk = overlap_text + " " + chunk
                    overlapped_chunks.append(overlapped_chunk)
                else:
                    overlapped_chunks.append(chunk)

        return overlapped_chunks

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass

        # Fallback: approximate using words
        return len(text.split())

    def _tokenize(self, text: str) -> List[int]:
        """
        Tokenize text.

        Args:
            text: Text to tokenize

        Returns:
            List of token IDs
        """
        if self.tokenizer:
            try:
                return self.tokenizer.encode(text)
            except Exception:
                pass

        # Fallback: split by whitespace
        return text.split()

    def _detokenize(self, tokens: List[int]) -> str:
        """
        Detokenize tokens back to text.

        Args:
            tokens: List of token IDs

        Returns:
            Detokenized text
        """
        if self.tokenizer:
            try:
                return self.tokenizer.decode(tokens)
            except Exception:
                pass

        # Fallback: join words
        return " ".join(str(t) for t in tokens)

    def split_documents_by_sections(self, text: str) -> List[dict]:
        """
        Split document by detected sections (headers, titles, etc.).

        Args:
            text: Document text

        Returns:
            List of section dictionaries
        """
        # Simple section detection using common patterns
        section_pattern = r'\n#{1,6}\s.*\n|\n[A-Z][^\n]{0,100}:\n|\n\d+\.\s[A-Z][^\n]{0,100}\n'
        sections = re.split(section_pattern, text)

        section_objects = []
        for idx, section in enumerate(sections):
            if section.strip():
                section_objects.append({
                    "content": section.strip(),
                    "index": idx,
                    "type": "section"
                })

        return section_objects
