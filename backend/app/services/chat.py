import re

SYSTEM_PROMPT = """你是 NourishFlow 的营养陪伴 AI。

# 核心使命
帮用户预防肥胖和 2 型糖尿病,通过血糖管理和食物质量优化。

# 立场
- 长期肥胖/糖尿病的核心驱动是食物结构,不是热量
- 预防层面:血糖管理 > 热量计数
- 不数卡路里,只看添加糖、血糖负荷(GL)、加工等级(NOVA)

# 用户画像(MVP 写死)
代谢状态: at_risk
目标: 预防糖尿病和肥胖

# 检索到的相关知识
{retrieved_chunks}

# 回应原则
- 用户每个选择都尊重,不劝退
- 涉及血糖/胰岛素/添加糖的断言必须引用 [chunk_id:xxx]
- 不教训,不羞辱,不用"应该""必须"

# 兜底
- 如果用户描述疑似糖尿病典型症状(多饮多食多尿、体重骤降),建议就医
"""


def format_chunks_for_prompt(chunks: list[dict]) -> str:
    if not chunks:
        return "(本次未检索到相关知识)"
    lines = []
    for c in chunks:
        lines.append(
            f"[chunk_id:{c['id']}] (来源: {c['title']}, tier {c['tier']}) {c['content']}"
        )
    return "\n\n".join(lines)


def assemble_messages(
    user_message: str,
    retrieved_chunks: list[dict],
    history: list[dict] | None = None,
) -> list[dict]:
    """组装发给 LLM 的 messages 列表."""
    retrieved_text = format_chunks_for_prompt(retrieved_chunks)
    system = SYSTEM_PROMPT.format(retrieved_chunks=retrieved_text)

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def extract_cited_chunk_ids(text: str) -> list[str]:
    """从 LLM 输出中提取所有 [chunk_id:xxx]."""
    return re.findall(r"\[chunk_id:([0-9a-f-]{36})\]", text)
