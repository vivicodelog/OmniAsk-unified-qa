"""
TextRetriever —— 混合检索：向量（BGE-M3）+ 关键词（BM25），RRF 融合。

为什么混合：纯向量检索对短文本、专有名词、精确数字不敏感（「语义相近但答案无关」），
补一路 BM25 关键词检索，用 RRF 把两路排序融合，兼顾语义召回和精确匹配。
"""
import chromadb
from chromadb.api.types import Metadata
from modelscope import snapshot_download
from sentence_transformers import SentenceTransformer
import jieba

from backend import config
from backend.schemas import PdfTextBlock
from backend.retrieval.bm25 import BM25, rrf_fusion


class TextRetriever:
    COLLECTION_NAME = "pdf_text"  # 单一 collection，靠 metadata.source 区分文件

    def __init__(self, persist_dir: str | None = None):
        model_dir = snapshot_download(config.EMBEDDING_MODEL)
        self.model = SentenceTransformer(model_dir)
        # persist_dir 缺省走 config，测试注入临时目录隔离真实库（依赖注入）
        self.client = chromadb.PersistentClient(path=persist_dir or config.CHROMA_PERSIST_DIR)
        # 关键词检索的内存索引：按 source 隔离（一个会话可能上传多个 PDF）
        self._blocks: dict[str, list[PdfTextBlock]] = {}   # source -> 原始块（含 page/bbox）
        self._bm25: dict[str, BM25] = {}                   # source -> BM25 索引

    def index(self, text_blocks: list[PdfTextBlock], source: str) -> None:
        # 单 collection + metadata.source 区分文件，多文件并存时靠 where 过滤，不建多库
        collection = self.client.get_or_create_collection(name=self.COLLECTION_NAME)
        texts = [block.text for block in text_blocks]
        # encode 返回 ndarray/Tensor，chromadb 只收 list[list[float]]，tolist 转原生 float
        embeddings = self.model.encode(texts, normalize_embeddings=True).tolist()
        metadata: list[Metadata] = [
            {
                "source": source,
                "page": block.page,
                "x0": block.bbox[0],
                "y0": block.bbox[1],
                "x1": block.bbox[2],
                "y1": block.bbox[3],
            }
            for block in text_blocks
        ]
        collection.upsert(
            ids=[f"{source}-{i}" for i in range(len(texts))],  # source 前缀保证跨文件 id 唯一
            documents=texts,
            metadatas=metadata,
            embeddings=embeddings,
        )
        # 关键词索引：分词后建 BM25（和向量库分开，存内存，随会话走）
        self._blocks[source] = text_blocks
        self._bm25[source] = BM25([self._tokenize(t) for t in texts])

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        # 中文关键词检索必须分词，否则 BM25 把整句当 token，等于没检索
        punct = set("，。、；：？！（）【】《》\"'…—·,.;:?!()[]{} \t\n")
        return [w for w in jieba.lcut(text) if w.strip() and w not in punct]

    def search(self, query: str, source: str, top_k: int = 5) -> list[dict]:
        vector_idx = self._vector_search(query, source, top_k)    # 语义路
        keyword_idx = self._keyword_search(query, source, top_k)  # 关键词路
        # RRF 融合两路排序：rank 靠前的块得分高，两路都出现的块更高
        fused_idx = rrf_fusion([vector_idx, keyword_idx], top_k=top_k)
        return [self._to_hit(source, idx) for idx in fused_idx]

    def _vector_search(self, query: str, source: str, top_k: int) -> list[int]:
        embeddings = self.model.encode([query], normalize_embeddings=True).tolist()
        collection = self.client.get_collection(name=self.COLLECTION_NAME)
        result = collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
            where={"source": source},
        )
        ids = result["ids"]
        if not ids or not ids[0]:          # chromadb 无命中返回 None（不是空列表）
            return []
        # id 形如 f"{source}-{i}"，用 rsplit 取末段拿块下标（source 文件名可能含 '-'）
        return [int(i.rsplit("-", 1)[-1]) for i in ids[0]]

    def _keyword_search(self, query: str, source: str, top_k: int) -> list[int]:
        bm25 = self._bm25.get(source)
        if bm25 is None:
            return []
        scores = bm25.scores(self._tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return ranked[:top_k]

    def _to_hit(self, source: str, idx: int) -> dict:
        block = self._blocks[source][idx]
        return {"text": block.text, "page": block.page, "bbox": block.bbox}
