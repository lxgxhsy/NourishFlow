import json
import uuid

import litellm
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.models.tables import Conversation, Message
from app.services.chat import assemble_messages, extract_cited_chunk_ids
from app.services.search import search_chunks

router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str


@router.post("/api/chat")
def chat(req: ChatRequest):

    def sse_stream():
        with Session(engine) as session:
            # 1. 拿到 / 新建 conversation
            if req.conversation_id is None:
                conv = Conversation()
                session.add(conv)
                session.commit()
                session.refresh(conv)
            else:
                conv = session.get(Conversation, req.conversation_id)
                if conv is None:
                    yield f"event: error\ndata: {json.dumps({'error': 'conversation not found'})}\n\n"
                    return

            # event: start
            yield f"event: start\ndata: {json.dumps({'conversation_id': str(conv.id)})}\n\n"

            # 2. 加载最近 10 条 messages → 上下文
            stmt = (
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(col(Message.created_at).desc())
                .limit(10)
            )
            recent = list(reversed(session.exec(stmt).all()))
            history = [{"role": m.role, "content": m.content} for m in recent]

            # 3. Meilisearch 全文检索 → top-5
            chunks = search_chunks(req.message, limit=5)

            # 4. 组装 prompt
            messages = assemble_messages(req.message, chunks, history)

            # 5. 先写 user message（LLM 挂了也不丢）
            session.add(Message(
                conversation_id=conv.id,
                role="user",
                content=req.message,
            ))
            session.commit()

            # 6. LiteLLM 流式调用
            response = litellm.completion(
                model=settings.llm_model,
                messages=messages,
                stream=True,
                api_key=settings.deepseek_api_key,
            )

            # 6. SSE 推送 + 缓存完整回复
            full_text_parts: list[str] = []
            for chunk in response:
                delta = ""
                if hasattr(chunk, "choices") and chunk.choices:
                    choice = chunk.choices[0]
                    if hasattr(choice, "delta") and hasattr(choice.delta, "content"):
                        delta = choice.delta.content or ""
                if delta:
                    full_text_parts.append(delta)
                    yield f"event: message\ndata: {json.dumps({'delta': delta})}\n\n"

            full_text = "".join(full_text_parts)

            # 7. 解析引用,过滤不在本次检索范围内的 UUID,写入 assistant message
            valid_chunk_ids = {c["id"] for c in chunks}
            raw_cited = extract_cited_chunk_ids(full_text)
            cited_ids = [cid for cid in raw_cited if cid in valid_chunk_ids]

            session.add(Message(
                conversation_id=conv.id,
                role="assistant",
                content=full_text,
                cited_chunk_ids=cited_ids,
                llm_model=settings.llm_model,
            ))
            session.commit()

            yield f"event: done\ndata: {json.dumps({'cited_chunk_ids': cited_ids, 'model': settings.llm_model})}\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
