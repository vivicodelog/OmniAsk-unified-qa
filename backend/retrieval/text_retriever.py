import chromadb
from chromadb.api.types import Metadata
from modelscope import snapshot_download
from sentence_transformers import SentenceTransformer
from backend import config
from backend.schemas import PdfTextBlock


class TextRetriever:
    COLLECTION_NAME = "pdf_text"  # 单一 collection，靠 metadata.source 区分文件

    def __init__(self, persist_dir: str | None = None):
        model_dir = snapshot_download(config.EMBEDDING_MODEL)
        self.model = SentenceTransformer(model_dir)
        # persist_dir 缺省走 config，测试注入临时目录隔离真实库（依赖注入）
        self.client = chromadb.PersistentClient(path=persist_dir or config.CHROMA_PERSIST_DIR)

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

    def search(self, query: str, source: str, top_k: int = 5) -> list[dict]:
        embeddings = self.model.encode([query], normalize_embeddings=True).tolist()
        collection = self.client.get_collection(name=self.COLLECTION_NAME)
        result = collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
            where={"source": source},
        )
        docs = result["documents"]
        metas = result["metadatas"]
        if not docs or not metas:  # chromadb 无命中时返回 None（不是空列表），提前返回空
            return []
        docs = docs[0]   # 第 0 个 query 的 top-k 原文
        metas = metas[0]  # 第 0 个 query 的 top-k 标签
        return [
            {
                "text": doc,
                "page": meta["page"],
                "bbox": (meta["x0"], meta["y0"], meta["x1"], meta["y1"]),
            }
            for doc, meta in zip(docs, metas)
        ]
