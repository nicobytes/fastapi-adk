import uuid

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.subagents.customer.tools.search_context import search_context

GENERATE_PROMPT = """Eres un asistente de Xperiencia. Responde SOLO con la información del contexto.
Si el contexto no alcanza para responder, di que no tienes esa información en la base de conocimiento.
No inventes precios, horarios ni detalles que no estén en el contexto.
Responde en español, de forma breve y concreta."""

APP_NAME = "xperiencia_eval"
USER_ID = "eval_user"
SESSION_ID = "session1234"

root_agent = Agent(
    model="gemini-3.5-flash-lite",
    name="root_agent",
    description="Asistente de Xperiencia",
    instruction=GENERATE_PROMPT,
    tools=[search_context],
)

# Inicializar SessionService y Runner
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


async def call_agent(query: str, session_id: str | None = None):
    # Usar un session_id único por defecto para que cada query sea independiente
    active_session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

    # Asegurar que la sesión existe antes de ejecutar
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=active_session_id
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=active_session_id
        )

    content = types.Content(role="user", parts=[types.Part(text=query)])
    events = runner.run_async(
        user_id=USER_ID, session_id=active_session_id, new_message=content
    )

    final_answer = ""
    retrieved_contexts = []

    async for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_response:
                    tool_data = part.function_response.response
                    if isinstance(tool_data, dict):
                        if "artifact" in tool_data and isinstance(
                            tool_data["artifact"], list
                        ):
                            for chunk in tool_data["artifact"]:
                                if isinstance(chunk, dict) and "content" in chunk:
                                    retrieved_contexts.append(chunk["content"])
                                else:
                                    retrieved_contexts.append(str(chunk))
                        elif "content" in tool_data:
                            retrieved_contexts.append(str(tool_data["content"]))
                        else:
                            retrieved_contexts.append(str(tool_data))
                    else:
                        retrieved_contexts.append(str(tool_data))

        if event.is_final_response() and event.content and event.content.parts:
            text_parts = [
                part.text.strip() for part in event.content.parts if part.text
            ]
            if text_parts:
                final_answer = "\n".join(text_parts)

    return final_answer, retrieved_contexts
