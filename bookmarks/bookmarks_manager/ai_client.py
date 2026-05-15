"""Cliente AsyncAnthropic com retry, timeout e tracking de uso.

Mesmo padrão usado em ``autocomplete/autocomplete_simulation.py``: a chave
da API é lida de ``ANTHROPIC_API_KEY`` no ambiente e nunca persistida em
disco. Importação do pacote ``anthropic`` é lazy — só falha quando o
usuário tenta usar funcionalidade que depende dele.
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
from dataclasses import dataclass

CALL_TIMEOUT_S = 60
BACKOFF_CAP_S = 15
MAX_RETRIES = 5

PRICING = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
}


def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.stderr.write(
            "ERRO: variável de ambiente ANTHROPIC_API_KEY não encontrada.\n"
            "Configure antes de rodar:\n\n"
            "    export ANTHROPIC_API_KEY=sk-ant-...\n\n"
        )
        sys.exit(1)
    return key


def get_client():
    """Importa anthropic sob demanda e retorna um AsyncAnthropic."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        sys.stderr.write(
            "ERRO: pacote `anthropic` não instalado.\n"
            "Rode: pip install anthropic>=0.40.0\n"
        )
        sys.exit(1)
    return AsyncAnthropic(api_key=get_api_key())


@dataclass
class UsageTracker:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, response) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0

    def cost_usd(self, model: str) -> float | None:
        prices = PRICING.get(model)
        if not prices:
            return None
        return (
            self.input_tokens / 1_000_000 * prices["input"]
            + self.output_tokens / 1_000_000 * prices["output"]
        )

    def format_summary(self, model: str) -> str:
        cost = self.cost_usd(model)
        cost_str = f"US$ {cost:.4f}" if cost is not None else "n/d"
        return (
            f"tokens: {self.input_tokens:,} input + "
            f"{self.output_tokens:,} output  |  custo: {cost_str}"
        )


def _backoff(attempt: int) -> float:
    return min(2 ** attempt, BACKOFF_CAP_S) + random.uniform(0, 1)


async def call_tool_use(
    client,
    *,
    model: str,
    system: str,
    user_content: str,
    tool_name: str,
    tool_schema: dict,
    max_tokens: int,
    temperature: float = 0.2,
    usage: UsageTracker | None = None,
):
    """Chama messages.create forçando o modelo a usar a tool indicada.

    Retorna o dict de ``tool_use.input``. Faz retry com backoff em rate
    limit / erro de servidor / timeout. Em caso de falha definitiva,
    levanta ``RuntimeError`` com contexto.
    """
    try:
        from anthropic import APIStatusError, RateLimitError
    except ImportError:
        raise RuntimeError("pacote `anthropic` não instalado")

    tool = {
        "name": tool_name,
        "description": f"Estrutura de saída obrigatória para {tool_name}.",
        "input_schema": tool_schema,
    }

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    tools=[tool],
                    tool_choice={"type": "tool", "name": tool_name},
                    messages=[{"role": "user", "content": user_content}],
                ),
                timeout=CALL_TIMEOUT_S,
            )
            if usage is not None:
                usage.add(response)
            for block in response.content:
                if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                    return block.input
            raise RuntimeError(
                f"resposta sem tool_use válido (stop_reason={response.stop_reason})"
            )
        except asyncio.TimeoutError:
            last_error = TimeoutError(f"call exceeded {CALL_TIMEOUT_S}s")
        except RateLimitError as e:
            last_error = e
        except APIStatusError as e:
            last_error = e
            status = getattr(e, "status_code", None)
            if not status or (status != 429 and status < 500):
                break
        except Exception as e:
            last_error = e

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(_backoff(attempt))

    raise RuntimeError(f"chamada falhou após {MAX_RETRIES} tentativas: {last_error}")
