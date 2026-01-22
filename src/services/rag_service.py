"""RAG (Retrieval Augmented Generation) service for document-aware AI assistance."""

import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import anthropic


@dataclass
class DocumentChunk:
    """A chunk of text from a document."""
    content: str
    source: str  # Document name
    page: Optional[int] = None
    chunk_index: int = 0


@dataclass
class DocumentStore:
    """Simple in-memory document store for RAG."""
    chunks: List[DocumentChunk] = field(default_factory=list)
    documents: Dict[str, str] = field(default_factory=dict)  # filename -> full text

    def add_document(self, filename: str, text: str, chunk_size: int = 1500):
        """Add a document and chunk it for retrieval."""
        self.documents[filename] = text

        # Split into chunks with overlap
        chunks = self._chunk_text(text, chunk_size, overlap=200)
        for i, chunk in enumerate(chunks):
            self.chunks.append(DocumentChunk(
                content=chunk,
                source=filename,
                chunk_index=i
            ))

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks."""
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def get_relevant_context(self, query: str, max_chunks: int = 5) -> str:
        """Get relevant document context for a query (simple keyword matching)."""
        if not self.chunks:
            return ""

        # Simple relevance scoring based on keyword matching
        query_words = set(query.lower().split())
        scored_chunks = []

        for chunk in self.chunks:
            chunk_words = set(chunk.content.lower().split())
            score = len(query_words.intersection(chunk_words))
            scored_chunks.append((score, chunk))

        # Sort by score and take top chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [chunk for _, chunk in scored_chunks[:max_chunks] if _ > 0]

        if not top_chunks:
            # Return first few chunks as general context
            top_chunks = self.chunks[:max_chunks]

        context_parts = []
        for chunk in top_chunks:
            context_parts.append(f"[From {chunk.source}]:\n{chunk.content}")

        return "\n\n---\n\n".join(context_parts)

    def get_document_summary(self) -> str:
        """Get a summary of loaded documents."""
        if not self.documents:
            return "No reference documents loaded."

        summaries = []
        for filename, text in self.documents.items():
            word_count = len(text.split())
            summaries.append(f"- {filename} ({word_count} words)")

        return "Loaded reference documents:\n" + "\n".join(summaries)


@dataclass
class ConversationMessage:
    """A message in the conversation."""
    role: str  # "user" or "assistant"
    content: str


class RAGAssistant:
    """Interactive AI assistant with RAG capabilities for I/O allocation."""

    SYSTEM_PROMPT = """You are an expert I/O allocation assistant for industrial control systems (DCS, SIS, RTU).
You help engineers design optimal I/O card allocations for Yokogawa systems (CENTUM VP, ProSafe-RS, STARDOM).

Your role is to:
1. Understand the user's requirements through conversation
2. Reference any uploaded specification documents to ensure compliance
3. Make intelligent assumptions based on industry best practices when information is not specified
4. Proactively identify potential issues and suggest solutions
5. Confirm the allocation rules before calculation

Key knowledge areas:
- Yokogawa DCS: CENTUM VP with AI (8ch), AO (8ch), DI (32ch), DO (32ch) cards
- Yokogawa SIS: ProSafe-RS with AI (8ch), AO (4ch), DI (16ch), DO (8ch) SIL-rated cards
- Yokogawa RTU: STARDOM for remote locations
- Standard 20% spare capacity unless specified otherwise
- Segregation rules: DCS/SIS separation, analog/digital separation, IS/non-IS separation
- SIL ratings and safety system requirements

IMPORTANT BEHAVIORAL GUIDELINES:
1. **Be Proactive, Not Interrogative**: Don't ask for information you can reasonably infer or assume
2. **Apply Industry Best Practices**: Make standard assumptions and state them clearly
3. **Use Uploaded Data**: If the I/O list is uploaded, analyze it directly - don't ask user to re-state counts
4. **Smart Defaults**:
   - No IS/non-IS segregation mentioned? → Assume standard non-IS system
   - No SIL rating mentioned? → Assume non-safety DCS
   - No spare percentage mentioned? → Use 20% standard
   - No specific segregation rules? → Standard area-based distribution
5. **Provide Value**: Instead of asking "what's your spare capacity?", say "I'll use 20% spare (industry standard) unless you need different"

RESPONSE FORMAT:
When reviewing I/O lists or providing recommendations:
- Lead with analysis and recommendations
- State assumptions clearly in a NOTES section
- Only ask questions when truly ambiguous or critical for safety

Example of GOOD response:
"Based on your I/O list (655 instruments: 150 AI, 300 DI, 180 DO, 25 AO), I recommend:
- 19 AI cards (with 20% spare)
- 10 DI cards (with 20% spare)
...

DESIGN NOTES:
- Assuming standard 20% spare capacity
- No IS/non-IS segregation (standard practice for non-hazardous areas)
- Area-based cabinet distribution for optimal cable routing

Proceed with this configuration, or let me know if you need different requirements."

Example of BAD response (DON'T DO THIS):
"I need more information:
1. What's your spare capacity requirement?
2. Do you need IS/non-IS segregation?
3. What are the signal types?
Please provide these details so I can help."

When the user is ready to proceed with calculation, summarize the understood rules clearly and ask them to type "proceed" or "yes" to show the allocation button.

IMPORTANT - DRAWING GENERATION:
When user asks to "generate drawing" or "create allocation":
- DO NOT generate ASCII art or text-based drawings in chat
- Summarize the allocation approach with assumptions
- Then say: "Ready to generate professional PDF allocation. Type 'proceed' or 'yes' to show the allocation button, which will create:
  * Detailed channel-by-channel assignments
  * Professional PDF reports with proper formatting
  * Excel exports for documentation
  * Cabinet/card layouts with specifications"
- The button appears after user confirms by typing "proceed", "yes", "confirm", or "go ahead"

Use professional language appropriate for instrumentation engineers.

If reference documents are provided, cite them when relevant (e.g., "Per the ACME philosophy document...").
"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the RAG assistant."""
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
        self.document_store = DocumentStore()
        self.conversation_history: List[ConversationMessage] = []
        self.confirmed_rules: Optional[Dict] = None

    def add_reference_document(self, filename: str, text: str):
        """Add a reference document for RAG."""
        self.document_store.add_document(filename, text)

    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response.

        Args:
            user_message: The user's message

        Returns:
            Assistant's response
        """
        # Add user message to history
        self.conversation_history.append(ConversationMessage(
            role="user",
            content=user_message
        ))

        # Build context from documents
        doc_context = ""
        if self.document_store.chunks:
            relevant_context = self.document_store.get_relevant_context(user_message)
            doc_summary = self.document_store.get_document_summary()
            doc_context = f"""
REFERENCE DOCUMENTS:
{doc_summary}

RELEVANT EXCERPTS:
{relevant_context}

---
IMPORTANT INSTRUCTIONS:
1. You HAVE ACCESS to the above reference documents
2. When user asks about uploaded/attached documents, ALWAYS acknowledge them by name
3. Reference specific content from the excerpts above when responding
4. If asked to review a document for anomalies or content, analyze the excerpts provided above
5. The user has already uploaded these documents - they are in your knowledge base
"""

        # Build messages for API
        messages = []
        for msg in self.conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add document context to system prompt
        system = self.SYSTEM_PROMPT
        if doc_context:
            system = system + "\n\n" + doc_context

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=system,
                messages=messages
            )

            assistant_message = response.content[0].text

            # Add assistant response to history
            self.conversation_history.append(ConversationMessage(
                role="assistant",
                content=assistant_message
            ))

            return assistant_message

        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}. Please try again."
            self.conversation_history.append(ConversationMessage(
                role="assistant",
                content=error_msg
            ))
            return error_msg

    def extract_confirmed_rules(self) -> Optional[Dict]:
        """
        Extract confirmed rules from the conversation.

        Returns:
            Dictionary of confirmed rules or None if not confirmed
        """
        if not self.conversation_history:
            return None

        # Use Claude to extract rules from conversation
        extraction_prompt = """Based on the conversation history, extract the confirmed I/O allocation rules.
Return a JSON object with these fields:
{
    "confirmed": true/false (whether user confirmed the rules),
    "spare_percent": <float 0.0-1.0>,
    "segregate_by_area": <bool>,
    "segregate_is_non_is": <bool>,
    "max_cabinets_per_area": <int or null>,
    "group_by_loop": <bool>,
    "custom_rules": [<list of any other rules mentioned>],
    "summary": "<brief summary of all rules>"
}

If the user hasn't confirmed yet, set "confirmed" to false.
"""

        # Build conversation text
        conv_text = "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in self.conversation_history
        ])

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"Conversation:\n{conv_text}\n\n{extraction_prompt}"
                }]
            )

            import json
            response_text = response.content[0].text

            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            self.confirmed_rules = json.loads(response_text)
            return self.confirmed_rules

        except Exception as e:
            print(f"Error extracting rules: {e}")
            return None

    def get_initial_greeting(self, io_list_filename: str, instrument_count: int) -> str:
        """Get initial greeting after I/O list is uploaded."""
        doc_info = ""
        if self.document_store.documents:
            doc_info = f"\n\nI also see you've uploaded reference documents:\n{self.document_store.get_document_summary()}\nI'll ensure the allocation complies with these specifications."

        greeting = f"""I've received your I/O list: **{io_list_filename}** with **{instrument_count} instruments**.
{doc_info}

Before I calculate the I/O card allocation, I'd like to understand your specific requirements:

1. **Spare Capacity**: The standard is 20% spare. Do you need a different percentage?
2. **Segregation Rules**: Any specific requirements for separating signals (by area, IS/non-IS, etc.)?
3. **Cabinet Constraints**: Any space limitations or maximum cabinet counts?
4. **Special Requirements**: Any project-specific rules I should follow?

Please share your requirements, or say "proceed with defaults" if standard rules are acceptable."""

        self.conversation_history.append(ConversationMessage(
            role="assistant",
            content=greeting
        ))

        return greeting

    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.confirmed_rules = None


def extract_text_from_pdf(filepath: str, max_pages: int = 50, dpi: int = 150) -> str:
    """
    Extract text from a PDF file.

    Uses a hybrid approach:
    1. First tries fast text extraction (for text-based PDFs) - INSTANT
    2. Falls back to OCR only if text extraction yields little content
    3. Uses optimized DPI (150) for balance of speed and quality

    Args:
        filepath: Path to PDF file
        max_pages: Maximum pages to process with OCR (default: 50)
        dpi: DPI for OCR image conversion (default: 150 - good quality, 2.25x faster than 200)

    Returns:
        Extracted text content
    """
    try:
        # STEP 1: Try fast text extraction first (for text-based PDFs)
        try:
            import PyPDF2
            with open(filepath, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)
                text_parts = []

                # Extract from all pages (fast for text-based PDFs)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"--- Page {i+1} ---\n{text}")

                extracted_text = "\n\n".join(text_parts)

                # If we got substantial text (>200 chars), return it
                if len(extracted_text.strip()) > 200:
                    print(f"✓ Extracted text from {total_pages} pages (text-based PDF, instant)")
                    return extracted_text
                else:
                    print(f"⚠ Text extraction yielded little content ({len(extracted_text)} chars), falling back to OCR...")
        except ImportError:
            print("PyPDF2 not available, using OCR directly")
        except Exception as e:
            print(f"Text extraction failed ({e}), falling back to OCR")

        # STEP 2: Fall back to OCR (slower, for scanned PDFs)
        from pdf2image import convert_from_path
        import pytesseract

        print(f"Starting OCR extraction (max {max_pages} pages at {dpi} DPI for quality)...")

        # Use 150 DPI - good balance of quality and speed
        # 150 DPI: Good OCR quality, 2.25x faster than 200 DPI
        # 200 DPI: Best quality but very slow
        images = convert_from_path(filepath, dpi=dpi, last_page=max_pages)
        text_parts = []

        for i, image in enumerate(images):
            print(f"  OCR processing page {i+1}/{len(images)}...")
            # Use Tesseract with optimization for better quality
            text = pytesseract.image_to_string(image, config='--psm 1')  # PSM 1 = auto page segmentation with OSD
            text_parts.append(f"--- Page {i+1} ---\n{text}")

        result = "\n\n".join(text_parts)
        print(f"✓ OCR completed: {len(images)} pages processed at {dpi} DPI")
        return result

    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""
