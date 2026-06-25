import json
from typing import Any

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool

from langgraph.runtime import Runtime
from pydantic import BaseModel

from app.core.logger import log_async_execution_time
from app.database.crud.post import PostService
from app.database.db.session import get_async_db

from app.services.post_generation.lang_chain_agent.llm_factory import get_lot_chooser_llm
from app.services.post_generation.lang_chain_agent.schemas import get_agent_result_parser, AgentResult
from app.services.post_generation.lang_chain_agent.state_context import AgentsState, AgentsRuntimeContext
from app.services.post_generation.lang_chain_agent.tools import get_instructions, get_page_of_lots
from app.services.post_generation.lang_chain_agent.utils import GeneratePostUtils
from app.services.post_generation.user_facing_errors import lot_chooser_failed_message

lot_chooser_tools: list[BaseTool] = [get_page_of_lots]


def _lot_chooser_user_error(state: AgentsState, min_lots: int, **kwargs: Any) -> str:
    filters = state["filters"]
    return lot_chooser_failed_message(
        make=filters.make,
        model=filters.model,
        min_lots=min_lots,
        **kwargs,
    )


def _build_lot_chooser_base_messages(
    system_instructions: str,
    history: list[BaseMessage],
    filters_json: str,
    min_lots: int,
    max_lots: int,
) -> list[BaseMessage]:
    return [
        SystemMessage(content=system_instructions),
        *history,
        HumanMessage(
            content=(
                f"Pick the best qualifying lots using these filters: {filters_json}\n"
                f"Return up to {max_lots} unique lots when that many qualify (minimum target: {min_lots}).\n"
                f"If you have reviewed fewer than {min_lots} qualifying lots so far, call get_page_of_lots "
                f"for the next page before answering.\n"
                f"Each lot_id must appear exactly once. Never use lot_id 0, placeholders, or duplicate ids.\n"
                f"If fewer than {min_lots} lots qualify across all available pages, return every qualifying lot "
                f"with is_error=false (do not pad the list).\n"
                f"Use is_error only when zero lots qualify or tools fail."
            )
        ),
    ]


async def _finalize_lot_chooser_result(
    parsed: AgentResult,
    state: AgentsState,
    runtime: Runtime[AgentsRuntimeContext],
) -> dict[str, Any]:
    ai_msg = AIMessage(content=parsed.model_dump_json())
    chose_lot_ids = [lot.lot_id for lot in parsed.lots]
    all_cumulated_lot_ids = chose_lot_ids + state.get("cumulated_chose_lot_ids", [])

    async with get_async_db() as db:
        post_service = PostService(db)
        posts = await post_service.left_only_this_lot_ids(
            request_filter_id=runtime.context["request_id"], lot_ids=all_cumulated_lot_ids
        )

    if not posts:
        raise ValueError("No matching posts in the database.")

    return {
        "messages": [ai_msg],
        "lot_chooser_result": parsed,
        "chose_lot_ids": chose_lot_ids,
        "cumulated_chose_lot_ids": all_cumulated_lot_ids,
        "cumulated_lots": parsed.lots + state.get("cumulated_lots", []),
    }


@log_async_execution_time('Choosing lots')
async def lot_chooser_agent_node(state: AgentsState, runtime: Runtime[AgentsRuntimeContext]) -> dict[str, Any]:
    min_lots_required = state["min_lots_lot_chooser"]
    max_lots = state["max_lots_lot_chooser"]

    is_need_more_lots = state.get("is_need_more_lots")
    if is_need_more_lots:
        min_lots = state.get("lots_needed", 5) + 2
        max_lots = state.get("lots_needed", 5) + 5
        await GeneratePostUtils.edit_message_for_user(
            message_id=runtime.context["editable_message_id"],
            text="🔄 Choosing more lots for you...\n"
                 f"⏳ This phase usually takes {round(0.18 * ((min_lots + max_lots) / 2), 2)} min\n"
                 "▶️ Approximately 5-7 min left",
            user_uuid=runtime.context["user_uuid"],
        )
    else:
        min_lots = min_lots_required
        await GeneratePostUtils.edit_message_for_user(
            message_id=runtime.context["editable_message_id"],
            text="🔄 Choosing the best lots for you...\n"
                 f"⏳ This phase usually takes {round(0.18 * ((min_lots + max_lots) / 2), 2)} min\n"
                 "▶️ Approximately 8-10 min left",
            user_uuid=runtime.context["user_uuid"],
        )

    # Schema min is 1 so the model never pads with duplicate lot_ids; min_lots_required is enforced via prompts and the fetch loop.
    response_schema: type[BaseModel] = get_agent_result_parser(1, max_lots)
    llm = get_lot_chooser_llm()
    structured_llm = llm.with_structured_output(response_schema)
    system_instructions = get_instructions("main_agent.md")

    filters_json = json.dumps(state["filters"].model_dump(mode="json"), ensure_ascii=False)
    base_messages = _build_lot_chooser_base_messages(
        system_instructions=system_instructions,
        history=state.get("messages", []),
        filters_json=filters_json,
        min_lots=min_lots,
        max_lots=max_lots,
    )

    correction_guard = SystemMessage(content="If you receive validation feedback, you must correct your answer to satisfy the response schema exactly and return only the fixed object.")
    feedback_messages: list[HumanMessage] = []
    validation_errors: list[str] = []
    attempts = 3
    messages: list[BaseMessage] = list(base_messages)

    for _ in range(attempts):
        ai = await llm.bind_tools(lot_chooser_tools).ainvoke(messages)

        if getattr(ai, "tool_calls", None):
            return {"messages": [ai]}

        try:
            parsed = await structured_llm.ainvoke(messages + [ai, correction_guard] + feedback_messages)
        except Exception as e:
            validation_errors.append(str(e))
            feedback_messages.append(
                HumanMessage(content=f"Your response failed validation: {e}. Fix schema violations and try again.")
            )
            messages = list(base_messages) + [ai, correction_guard] + feedback_messages
            continue

        if not parsed.lots and not parsed.is_error:
            validation_errors.append("No valid lots in response (empty list, duplicate lot_ids, or lot_id=0).")
            feedback_messages.append(
                HumanMessage(
                    content=(
                        "Your response contained no valid lots (empty list, duplicate lot_ids, or lot_id=0). "
                        f"Return every qualifying lot you found (up to {max_lots}) with unique positive lot_ids."
                    )
                )
            )
            messages = list(base_messages) + [ai, correction_guard] + feedback_messages
            continue

        if parsed.is_error and not parsed.lots:
            feedback_messages.append(
                HumanMessage(
                    content=(
                        "Do not stop with is_error when some lots qualify. "
                        f"Return every qualifying lot you found (up to {max_lots}) with is_error=false. "
                        f"Previous error: {parsed.error_message}"
                    )
                )
            )
            messages = list(base_messages) + [ai, correction_guard] + feedback_messages
            continue

        try:
            return await _finalize_lot_chooser_result(parsed, state, runtime)
        except ValueError:
            validation_errors.append("No matching posts in the database for the returned lot_ids.")
            error_message = HumanMessage(
                content="No matching posts in the database. Use tools to fetch lots, then return only lot_ids that exist."
            )
            feedback_messages.append(error_message)
            messages = list(base_messages) + [ai, correction_guard] + feedback_messages
            continue
        except Exception as e:
            return {
                "is_error": True,
                "error_message": _lot_chooser_user_error(
                    state,
                    min_lots_required,
                    validation_errors=[str(e)],
                ),
            }

    fallback_nudge = HumanMessage(
        content="You could not satisfy the schema yet. Call the available tools now to fetch or refine lots, then return a corrected object strictly matching the schema."
    )

    try:
        ai_final = await llm.bind_tools(lot_chooser_tools).ainvoke(list(base_messages) + [correction_guard] + feedback_messages + [fallback_nudge])
    except Exception as e:
        validation_errors.append(str(e))
        return {
            "is_error": True,
            "error_message": _lot_chooser_user_error(
                state,
                min_lots_required,
                validation_errors=validation_errors,
            ),
        }

    if getattr(ai_final, "tool_calls", None):
        return {"messages": [ai_final]}

    try:
        parsed_final = await structured_llm.ainvoke(list(base_messages) + [correction_guard] + feedback_messages + [fallback_nudge])
        if parsed_final.is_error and not parsed_final.lots:
            return {
                "is_error": True,
                "error_message": _lot_chooser_user_error(
                    state,
                    min_lots_required,
                    agent_reason=parsed_final.error_message,
                ),
                "messages": [AIMessage(content=parsed_final.model_dump_json())],
                "lot_chooser_result": parsed_final,
            }
        return await _finalize_lot_chooser_result(parsed_final, state, runtime)
    except Exception as e:
        validation_errors.append(str(e))

    return {
        "is_error": True,
        "error_message": _lot_chooser_user_error(
            state,
            min_lots_required,
            validation_errors=validation_errors,
        ),
    }



def tools_router(state: AgentsState) -> str | None:
    messages = state.get("messages", [])
    is_error = state.get("is_error", False)
    if not messages:
        return "process_image"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools_node"
    elif is_error:
        return 'send_error_to_user'
    return "process_image"
