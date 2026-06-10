from __future__ import annotations

import shutil
import uuid
import re
from dataclasses import dataclass
from pathlib import Path

import joblib
from fastapi import UploadFile
from openai import AsyncOpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import Settings
from app.document_loader import SUPPORTED_EXTENSIONS, extract_text
from app.schemas import DocumentInfo, SourceChunk


@dataclass
class ChunkRecord:
    document_id: str
    filename: str
    chunk_id: str
    text: str


class RagService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.chunks: list[ChunkRecord] = []
        self.word_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
        self.word_matrix = None
        self.char_matrix = None
        self._load()

    async def add_upload(self, file: UploadFile) -> tuple[str, int]:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type. Supported types: {supported}")

        content = await file.read()
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(f"File is larger than {self.settings.max_upload_mb} MB")

        document_id = str(uuid.uuid4())
        safe_name = Path(file.filename or f"document{suffix}").name
        saved_path = self.settings.upload_dir / f"{document_id}_{safe_name}"
        saved_path.write_bytes(content)

        text = extract_text(saved_path).strip()
        if not text:
            saved_path.unlink(missing_ok=True)
            raise ValueError("No readable text found in the uploaded file")

        new_chunks = self._chunk_text(text, document_id, safe_name)
        self.chunks.extend(new_chunks)
        self._rebuild_index()
        self._save()
        return document_id, len(new_chunks)

    def retrieve(self, question: str, top_k: int) -> list[SourceChunk]:
        if not self.chunks or self.word_matrix is None or self.char_matrix is None:
            return []

        expanded_question = self._expand_query(question)
        word_query = self.word_vectorizer.transform([expanded_question])
        char_query = self.char_vectorizer.transform([expanded_question])
        word_scores = cosine_similarity(word_query, self.word_matrix)[0]
        char_scores = cosine_similarity(char_query, self.char_matrix)[0]
        scores = (word_scores * 0.7) + (char_scores * 0.3)
        ranked_indexes = scores.argsort()[::-1][:top_k]

        sources: list[SourceChunk] = []
        seen_texts: set[str] = set()
        for index in ranked_indexes:
            score = float(scores[index])
            chunk = self.chunks[int(index)]
            text_key = " ".join(chunk.text.lower().split())
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)
            sources.append(
                SourceChunk(
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=round(score, 4),
                )
            )
        return sources

    async def answer(
        self,
        question: str,
        sources: list[SourceChunk],
        use_documents: bool = True,
    ) -> tuple[str, str | None]:
        if not use_documents:
            return await self._answer_without_documents(question)

        if not sources:
            return "I could not find relevant information in the uploaded documents.", None

        if not self.settings.openai_api_key:
            return self._extractive_answer(question, sources), None

        context = "\n\n".join(
            f"[Source: {source.filename}, chunk {source.chunk_id}]\n{source.text}"
            for source in sources
        )
        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful RAG chatbot. Answer only from the supplied context. "
                        "Read the context carefully because field names may be abbreviated, such as Mob for mobile. "
                        "If the answer is not in the context, say you do not know."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}",
                },
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or "", self.settings.openai_model

    async def _answer_without_documents(self, question: str) -> tuple[str, str | None]:
        if not self.settings.openai_api_key:
            return (
                "OPENAI_API_KEY is not configured, so I cannot generate a generic LLM answer yet.",
                None,
            )

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful general-purpose assistant. Answer clearly and concisely.",
                },
                {"role": "user", "content": question},
            ],
            temperature=0.4,
        )
        return response.choices[0].message.content or "", self.settings.openai_model

    def _extractive_answer(self, question: str, sources: list[SourceChunk]) -> str:
        context = "\n".join(source.text for source in sources)
        lowered = question.lower()

        if any(term in lowered for term in ["phone", "mobile", "contact", "number", "mob"]):
            mobile_match = re.search(r"(?:mob|mobile|phone|contact)\s*:?\s*([+()\d\s-]{7,})", context, re.IGNORECASE)
            if mobile_match:
                return f"The mobile/contact number mentioned in the document is {mobile_match.group(1).strip()}."

        if any(term in lowered for term in ["email", "mail", "gmail"]):
            email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", context)
            if email_match:
                return f"The email mentioned in the document is {email_match.group(0)}."

        if "linkedin" in lowered:
            linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/\S+", context, re.IGNORECASE)
            if linkedin_match:
                return f"The LinkedIn profile mentioned in the document is {linkedin_match.group(0).rstrip('|,.;')}."

        sentences = self._split_sentences(context)
        if not sentences:
            return "I found the document, but could not extract a readable answer from it."

        query_terms = {
            term
            for term in re.findall(r"[a-zA-Z0-9+#.-]+", self._expand_query(question).lower())
            if len(term) > 2
        }
        ranked_sentences = sorted(
            sentences,
            key=lambda sentence: sum(1 for term in query_terms if term in sentence.lower()),
            reverse=True,
        )
        best = [sentence for sentence in ranked_sentences[:4] if sentence.strip()]
        return " ".join(best) if best else sentences[0]

    def _split_sentences(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|(?=\b[A-Z][A-Z ]{3,}\b)", normalized)
            if len(sentence.strip()) > 20
        ]

    def list_documents(self) -> list[DocumentInfo]:
        grouped: dict[tuple[str, str], int] = {}
        for chunk in self.chunks:
            key = (chunk.document_id, chunk.filename)
            grouped[key] = grouped.get(key, 0) + 1

        return [
            DocumentInfo(document_id=document_id, filename=filename, chunks=count)
            for (document_id, filename), count in sorted(grouped.items(), key=lambda item: item[0][1])
        ]

    def reset(self) -> None:
        self.chunks = []
        self.word_matrix = None
        self.char_matrix = None
        if self.settings.data_dir.exists():
            for child in self.settings.data_dir.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)

    def _chunk_text(self, text: str, document_id: str, filename: str) -> list[ChunkRecord]:
        words = text.split()
        chunks: list[ChunkRecord] = []
        start = 0
        chunk_number = 1
        step = max(1, self.settings.chunk_size - self.settings.chunk_overlap)

        while start < len(words):
            end = min(start + self.settings.chunk_size, len(words))
            chunk_text = " ".join(words[start:end]).strip()
            if chunk_text:
                chunks.append(
                    ChunkRecord(
                        document_id=document_id,
                        filename=filename,
                        chunk_id=str(chunk_number),
                        text=chunk_text,
                    )
                )
            start += step
            chunk_number += 1

        return chunks

    def _rebuild_index(self) -> None:
        if not self.chunks:
            self.word_matrix = None
            self.char_matrix = None
            return
        texts = [chunk.text for chunk in self.chunks]
        self.word_matrix = self.word_vectorizer.fit_transform(texts)
        self.char_matrix = self.char_vectorizer.fit_transform(texts)

    def _expand_query(self, question: str) -> str:
        aliases = {
            "phone": "phone mobile mob contact number",
            "mobile": "mobile mob phone contact number",
            "contact": "contact mobile mob phone email",
            "mail": "mail email gmail",
            "email": "email mail gmail",
            "linkedin": "linkedin profile url",
            "education": "education degree qualification academic",
            "experience": "experience internship training programme work",
            "skills": "skills technical laboratory techniques",
        }
        lowered = question.lower()
        expansions = [terms for key, terms in aliases.items() if key in lowered]
        return " ".join([question, *expansions])

    def _save(self) -> None:
        self.settings.index_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "chunks": self.chunks,
                "word_vectorizer": self.word_vectorizer,
                "char_vectorizer": self.char_vectorizer,
                "word_matrix": self.word_matrix,
                "char_matrix": self.char_matrix,
            },
            self.settings.index_path,
        )

    def _load(self) -> None:
        if not self.settings.index_path.exists():
            return
        data = joblib.load(self.settings.index_path)
        self.chunks = data.get("chunks", [])
        self.word_vectorizer = data.get("word_vectorizer", data.get("vectorizer", self.word_vectorizer))
        self.char_vectorizer = data.get("char_vectorizer", self.char_vectorizer)
        self.word_matrix = data.get("word_matrix", data.get("matrix"))
        self.char_matrix = data.get("char_matrix")
        if self.chunks and (self.word_matrix is None or self.char_matrix is None):
            self._rebuild_index()
            self._save()
