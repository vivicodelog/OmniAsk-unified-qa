"""TextRetriever 的 pytest 测试：模型只加载一次 + 临时库隔离，不污染真实 data/chroma_db。"""
import pytest

from backend.retrieval.text_retriever import TextRetriever
from backend.schemas import PdfTextBlock


@pytest.fixture(scope="module")
def retriever(tmp_path_factory) -> TextRetriever:
    """模块级：BGE 模型只加载一次；临时库写进 tmp_path，测完自动删。"""
    persist_dir = tmp_path_factory.mktemp("chroma_test")
    return TextRetriever(persist_dir=str(persist_dir))


@pytest.fixture(scope="module")
def seeded(retriever: TextRetriever) -> TextRetriever:
    """模块级：索引 3 条测试数据一次，三个测试共享，不依赖执行顺序。"""
    blocks = [
        PdfTextBlock(page=1, text="这是第一段测试文本", bbox=(0.0, 0.0, 100.0, 50.0)),
        PdfTextBlock(page=1, text="这是第二段测试文本", bbox=(0.0, 50.0, 100.0, 100.0)),
        PdfTextBlock(page=2, text="这是第二页的测试文本", bbox=(0.0, 0.0, 100.0, 50.0)),
    ]
    retriever.index(blocks, "测试文档")
    return retriever


def test_index_count(seeded: TextRetriever) -> None:
    """写入 3 条，collection 里 source=测试文档 的条数应为 3。"""
    collection = seeded.client.get_collection(TextRetriever.COLLECTION_NAME)
    result = collection.get(where={"source": "测试文档"})
    assert len(result["ids"]) == 3


def test_search_ranking(seeded: TextRetriever) -> None:
    """检索排序准：查「这是第一段」，第一名应是「这是第一段测试文本」，bbox 拼回 tuple 且值对。"""
    hits = seeded.search("这是第一段", "测试文档", top_k=3)
    assert len(hits) == 3
    assert hits[0]["text"] == "这是第一段测试文本"
    assert hits[0]["page"] == 1
    assert hits[0]["bbox"] == (0.0, 0.0, 100.0, 50.0)


def test_search_empty_source(seeded: TextRetriever) -> None:
    """source 不匹配时，search 返回 []（不是 None，不崩）。"""
    assert seeded.search("随便搜", "不存在的文件", top_k=3) == []
