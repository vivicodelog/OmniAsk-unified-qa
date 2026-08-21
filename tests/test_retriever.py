"""混合检索的纯算法测试：BM25 打分 + RRF 融合（不依赖模型/chroma，秒跑）。"""
from backend.retrieval.bm25 import BM25, rrf_fusion


# ① BM25：命中 query 词的文档分数更高，无关文档分数为 0
def test_bm25_scores_favor_matching_doc():
    docs = [
        ["最大", "市场", "华南", "区"],
        ["季度", "销售", "趋势"],
        ["产品", "线", "明细"],
    ]
    bm = BM25(docs)
    scores = bm.scores(["最大", "市场"])
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


# ② BM25：query 词全不命中时，所有分数为 0（不崩、不虚高）
def test_bm25_no_match_returns_zero():
    bm = BM25([["a", "b"], ["c", "d"]])
    assert bm.scores(["x", "y"]) == [0.0, 0.0]


# ③ RRF：同时出现在两路、且 rank 靠前的块排最前
def test_rrf_fusion_prefers_common_top():
    fused = rrf_fusion([[0, 1], [0, 2]])
    assert fused[0] == 0


# ④ RRF：top_k 截断
def test_rrf_fusion_top_k():
    fused = rrf_fusion([[0, 1, 2], [1, 2, 0]], top_k=2)
    assert len(fused) == 2


# ⑤ RRF：两个列表无交集时也能融合（按各自 rank）
def test_rrf_fusion_disjoint():
    fused = rrf_fusion([[0, 1], [2, 3]])
    assert set(fused) == {0, 1, 2, 3}
    assert len(fused) == 4
