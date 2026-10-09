import pytest

from src.generator import evidence_generator
from src.generator.evidence_generator import generate_answer
from src.generator.llm_provider import LLMGenerationResult
from src.generator.template_generator import (
    _select_query_excerpt,
    _shorten_text,
)


def test_excerpt_keeps_relevant_tail_and_adjacent_context():
    prefix = "这段材料介绍资料整理与平台维护。" * 30
    context = "组织动员帮助队伍克服困难。"
    conclusion = "材料强调：“团结协作精神源于共同实践。”"
    text = prefix + context + conclusion

    excerpt = _select_query_excerpt("团结协作精神源于什么？", text)

    assert context in excerpt
    assert conclusion in excerpt
    assert excerpt in text
    assert len(excerpt) <= 320


def test_excerpt_preserves_short_text_and_unmatched_fallback():
    short = "教育需要结合具体材料。"
    assert _select_query_excerpt("教育", short) == short
    long = "资料整理需要检查编号。" * 40
    assert _select_query_excerpt("量子纠错", long) == _shorten_text(long)


def test_excerpt_preserves_consecutive_sentence_marks():
    text = "背景说明。" * 90 + "真的吗？！长征精神体现坚定信念。"
    excerpt = _select_query_excerpt("长征精神坚定信念", text)
    assert "真的吗？！" in excerpt
    assert excerpt in text


def test_excerpt_keeps_an_oversized_relevant_sentence_complete():
    sentence = "团结协作精神体现为" + "共同实践" * 90 + "。"
    text = "背景资料与平台维护。" * 40 + sentence
    assert _select_query_excerpt("团结协作精神", text) == sentence


def _hit(
    *,
    hit_id: str = "chunk_test_001",
    title: str = "测试证据",
    text: str = "思想政治教育需要依据具体历史材料展开。",
    hybrid_score: float = 0.9,
) -> dict:
    return {
        "id": hit_id,
        "source": "中国共产党思想政治教育史",
        "title": title,
        "text": text,
        "citation": {
            "doc": "中国共产党思想政治教育史",
            "section": "测试章节",
            "page": 1,
        },
        "hybrid_score": hybrid_score,
    }


def test_template_generator_mode_is_default(monkeypatch):
    monkeypatch.delenv("DACHUANG_GENERATOR_MODE", raising=False)

    result = generate_answer("思想政治教育为什么重要？", [_hit()])

    assert result["generator_mode"] == "template"
    assert result["generator_provider"] == "template"
    assert result["provider_status"] == "template_evidence_summary"
    assert result["used_fallback"] is True
    assert result["answer"]
    assert result["citations_used"]
    assert "prompt_preview" not in result


def test_llm_mode_keeps_contract_and_builds_prompt(monkeypatch):
    monkeypatch.setenv("DACHUANG_GENERATOR_MODE", "llm")

    result = generate_answer("思想政治教育为什么重要？", [_hit()])

    assert result["generator_mode"] == "llm"
    assert result["generator_provider"] == "stub"
    assert result["provider_status"] == "stub_no_external_call"
    assert result["answer"]
    assert result["citations_used"]
    assert "只能依据给定证据回答" in result["prompt_preview"]
    assert "先概括核心结论" in result["prompt_preview"]
    assert "不要逐条复制证据标题" in result["prompt_preview"]
    assert "使用 [1]、[2]" in result["prompt_preview"]
    assert "来源：" in result["prompt_preview"]
    assert "思想政治教育需要依据具体历史材料展开" in result["prompt_preview"]


def test_llm_mode_uses_successful_provider_answer(monkeypatch):
    answer = (
        "思想政治教育之所以重要，是因为它能够围绕党的中心任务统一思想、凝聚共识，"
        "并将理论教育转化为组织动员和群众实践。[1] 从历史发展看，这一工作贯穿革命、"
        "建设和改革过程，为干部教育、组织建设和群众工作提供持续的思想保障。[1]\n\n"
        "来源：[1]《中国共产党思想政治教育史》，测试章节，PDF 页码 1。"
    )

    class SuccessfulProvider:
        name = "zhipu"

        def generate(self, prompt: str) -> LLMGenerationResult:
            return LLMGenerationResult(
                text=answer,
                provider_name=self.name,
                status="success",
            )

    monkeypatch.setenv("DACHUANG_GENERATOR_MODE", "llm")
    monkeypatch.setattr(
        evidence_generator,
        "get_llm_provider",
        lambda provider_name: SuccessfulProvider(),
    )

    result = generate_answer("思想政治教育为什么重要？", [_hit()])

    assert result["answer"].startswith("仅依据当前检索到的证据，")
    assert answer in result["answer"]
    assert result["generator_provider"] == "zhipu"
    assert result["provider_status"] == "success"
    assert result["used_fallback"] is False
    assert result["citations_used"]


def test_llm_mode_rejects_incomplete_provider_answer(monkeypatch):
    class IncompleteProvider:
        name = "zhipu"

        def generate(self, prompt: str) -> LLMGenerationResult:
            return LLMGenerationResult(
                text="根据证据可以看出，这一问题主要包括：一是",
                provider_name=self.name,
                status="success",
            )

    monkeypatch.setenv("DACHUANG_GENERATOR_MODE", "llm")
    monkeypatch.setattr(
        evidence_generator,
        "get_llm_provider",
        lambda provider_name: IncompleteProvider(),
    )

    result = generate_answer("思想政治教育为什么重要？", [_hit()])

    assert result["provider_status"] == "invalid_response"
    assert result["used_fallback"] is True
    assert "仅为检索证据摘要" in result["answer"]
    assert result["quality_issues"]


def test_llm_mode_falls_back_when_provider_fails(monkeypatch):
    class FailedProvider:
        name = "zhipu"

        def generate(self, prompt: str) -> LLMGenerationResult:
            return LLMGenerationResult(
                text="",
                provider_name=self.name,
                status="provider_error",
            )

    monkeypatch.setenv("DACHUANG_GENERATOR_MODE", "llm")
    monkeypatch.setattr(
        evidence_generator,
        "get_llm_provider",
        lambda provider_name: FailedProvider(),
    )

    result = generate_answer("思想政治教育为什么重要？", [_hit()])

    assert result["answer"]
    assert result["provider_status"] == "provider_error"
    assert result["used_fallback"] is True
    assert result["citations_used"]
    assert "仅为检索证据摘要" in result["answer"]


def test_llm_mode_skips_paid_call_without_evidence(monkeypatch):
    class UnexpectedProvider:
        name = "zhipu"

        def generate(self, prompt: str) -> LLMGenerationResult:
            raise AssertionError("无证据时不应调用外部模型")

    monkeypatch.setenv("DACHUANG_GENERATOR_MODE", "llm")
    monkeypatch.setattr(
        evidence_generator,
        "get_llm_provider",
        lambda provider_name: UnexpectedProvider(),
    )

    result = generate_answer("一个知识库中没有证据的问题", [])

    assert result["generator_mode"] == "llm"
    assert result["provider_status"] == "skipped_no_evidence"
    assert result["used_fallback"] is True
    assert result["citations_used"] == []


def test_unknown_generator_mode_falls_back_to_template(monkeypatch):
    monkeypatch.setenv("DACHUANG_GENERATOR_MODE", "unknown")

    result = generate_answer("思想政治教育为什么重要？", [_hit()])

    assert result["generator_mode"] == "template"
    assert result["answer"]


def test_template_answer_is_compact_and_citation_grounded(monkeypatch):
    monkeypatch.delenv("DACHUANG_GENERATOR_MODE", raising=False)

    result = generate_answer(
        "思想政治教育为什么重要？",
        [
            _hit(title="核心证据"),
            _hit(
                hit_id="chunk_test_002",
                title="补充证据",
                text="补充证据用于说明思想政治教育还需要结合组织动员和群众工作展开。",
                hybrid_score=0.8,
            ),
            _hit(
                hit_id="chunk_test_003",
                title="无关补充证据",
                text="这是一条不应进入模板回答的低分候选。",
                hybrid_score=0.1,
            ),
        ],
    )

    assert "生成服务当前不可用" in result["answer"]
    assert "仅为检索证据摘要" in result["answer"]
    assert "引用依据" in result["answer"]
    assert "来源：" in result["answer"]
    assert "PDF 页码" in result["answer"]
    assert "仅依据当前检索到的证据" in result["answer"]
    assert "核心证据" in result["answer"]
    assert "补充证据" in result["answer"]
    assert "无关补充证据" not in result["answer"]
    assert len(result["citations_used"]) == 2
    assert len(result["answer"]) < 1200


def test_template_answer_filters_high_score_but_weak_query_overlap(monkeypatch):
    monkeypatch.delenv("DACHUANG_GENERATOR_MODE", raising=False)

    result = generate_answer(
        "张闻天起草的宣传鼓动工作提纲强调了什么？",
        [
            _hit(
                title="党的宣传鼓动工作提纲",
                text="张闻天起草的宣传鼓动工作提纲强调宣传鼓动工作的性质、任务、范围和群众教育方法。",
                hybrid_score=0.9,
            ),
            _hit(
                hit_id="chunk_test_002",
                title="弱相关高分证据",
                text="这条材料主要讨论课程资源建设与教学平台维护，并不回答当前问题。",
                hybrid_score=0.95,
            ),
        ],
    )

    assert "党的宣传鼓动工作提纲" in result["answer"]
    assert "弱相关高分证据" not in result["answer"]
    assert len(result["citations_used"]) == 1


def test_template_answer_prefers_complete_sentence_boundary(monkeypatch):
    monkeypatch.delenv("DACHUANG_GENERATOR_MODE", raising=False)
    long_text = (
        "第一句话用于说明核心结论，并且已经完整结束。"
        + "第二句话包含大量补充说明，" * 30
    )

    result = generate_answer("测试长文本截断。", [_hit(text=long_text)])

    assert "第一句话用于说明核心结论，并且已经完整结束。" in result["answer"]
    assert "第二句话包含大量补充说明，第二句话" not in result["answer"]


def test_template_answer_keeps_closing_quote_when_truncated(monkeypatch):
    monkeypatch.delenv("DACHUANG_GENERATOR_MODE", raising=False)
    quoted_text = (
        "材料指出：“这是一句带有完整中文引号的关键论述。”"
        + "后续补充说明较长，" * 80
    )

    result = generate_answer("测试中文引号截断。", [_hit(text=quoted_text)])

    assert "“这是一句带有完整中文引号的关键论述。”" in result["answer"]
    assert "后续补充说明较长，后续补充说明较长" not in result["answer"]

@pytest.mark.parametrize(
    ("body_refs", "source_refs", "accepted"),
    [
        ("[1]", "[1]", True),
        ("[2]", "[2]", True),
        ("[1][99]", "[1][99]", False),
        ("[0]", "[0]", False),
        ("[01]", "[01]", False),
        ("", "[1]", False),
        ("[1]", "[2]", False),
        ("[1]", "[1][2]", False),
    ],
)
def test_llm_citation_numbers_match_current_evidence(
    body_refs, source_refs, accepted
):
    answer = (
        "仅依据当前检索到的证据，解释历史问题需要核查材料，"
        "区分材料直接说明的内容与仍需进一步验证的推断。" * 4
        + body_refs
        + "\n\n来源：" + source_refs + "测试资料。"
    )
    issues = evidence_generator._validate_llm_answer(answer, 2)
    assert (not issues) is accepted


def test_llm_citations_used_contains_only_body_references(monkeypatch):
    answer = (
        "仅依据当前检索到的证据，思想政治教育需要结合具体材料展开，"
        "阅读者应核查原文并据此形成解释。" * 4
        + "[2]\n\n来源：[2]《中国共产党思想政治教育史》，"
        "测试章节，PDF 页码 1。"
    )

    class SuccessfulProvider:
        name = "stub"

        def generate(self, prompt: str) -> LLMGenerationResult:
            return LLMGenerationResult(
                text=answer, provider_name=self.name, status="success"
            )

    monkeypatch.setenv("DACHUANG_GENERATOR_MODE", "llm")
    monkeypatch.setattr(
        evidence_generator,
        "get_llm_provider",
        lambda provider_name: SuccessfulProvider(),
    )
    result = generate_answer(
        "思想政治教育",
        [_hit(), _hit(hit_id="chunk_test_002")],
    )
    assert result["used_fallback"] is False
    assert [item["id"] for item in result["citations_used"]] == [
        "chunk_test_002"
    ]
