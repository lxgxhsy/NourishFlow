#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
UVICORN_PID=""

cleanup() {
    if [ -n "$UVICORN_PID" ] && kill -0 "$UVICORN_PID" 2>/dev/null; then
        kill "$UVICORN_PID" 2>/dev/null
        wait "$UVICORN_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

fail() {
    echo "FAIL: $1"
    echo "--- stderr ---"
    echo "$2"
    exit 1
}

# 1. 起 PG + Meilisearch
echo "==> docker compose up -d"
cd "$ROOT"
docker compose up -d

# 等 PG ready (最多 30 秒)
echo "==> 等待 PG ready..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U nourish > /dev/null 2>&1; then
        echo "    PG ready (${i}s)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        fail "PG 30 秒内未就绪" "$(docker compose logs postgres)"
    fi
    sleep 1
done

# 等 Meili ready (最多 30 秒)
echo "==> 等待 Meili ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:7700/health > /dev/null 2>&1; then
        echo "    Meili ready (${i}s)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        fail "Meili 30 秒内未就绪" "$(docker compose logs meilisearch)"
    fi
    sleep 1
done

# 2. 启动 uvicorn 后台
echo "==> 启动 uvicorn (后台)"
cd "$BACKEND"
[ -f .env ] || cp .env.example .env
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!
sleep 5

# 检查 uvicorn 还活着
if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
    wait "$UVICORN_PID" 2>/dev/null || true
    fail "uvicorn 启动后退出" "$(cat /proc/$UVICORN_PID/fd/2 2>/dev/null || echo '进程已退出,无法获取 stderr')"
fi

# 3. psql 检查 4 张表
echo "==> psql \\dt 检查表"
TABLES=$(docker compose exec -T postgres psql -U nourish -d nourishflow -t -c "\dt" 2>&1)
for tbl in articles article_chunks conversations messages; do
    if echo "$TABLES" | grep -q "$tbl"; then
        echo "    $tbl ✅"
    else
        fail "PG 缺少表: $tbl" "$TABLES"
    fi
done

# 4. Meili 索引检查
echo "==> curl Meili indexes"
MEILI_MASTER_KEY="dev-master-key-for-local-use-only"
MEILI_RESP=$(curl -sf -H "Authorization: Bearer $MEILI_MASTER_KEY" http://localhost:7700/indexes 2>&1) || fail "Meili /indexes 请求失败" "$MEILI_RESP"
if echo "$MEILI_RESP" | grep -q "article_chunks"; then
    echo "    article_chunks 索引 ✅"
else
    fail "Meili 缺少 article_chunks 索引" "$MEILI_RESP"
fi

# 5. /api/health
echo "==> curl /api/health"
HEALTH=$(curl -sf http://localhost:8000/api/health 2>&1) || fail "/api/health 请求失败" "$HEALTH"
if echo "$HEALTH" | grep -q '"status"'; then
    echo "    /api/health ✅  → $HEALTH"
else
    fail "/api/health 响应异常" "$HEALTH"
fi

echo ""
echo "=== P1 全部通过 ==="
exit 0
