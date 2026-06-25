from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, ValidationError

from app.core.logger import log_async_execution_time
from app.services.post_generation.lang_chain_agent.llm_factory import get_choose_final_lots_llm
from app.services.post_generation.lang_chain_agent.schemas import (
    coerce_structured_model,
    get_final_lots_response_schema,
)
from app.services.post_generation.lang_chain_agent.state_context import AgentsState, AgentsRuntimeContext
from app.services.post_generation.lang_chain_agent.tools import get_instructions
from app.services.post_generation.lang_chain_agent.utils import GeneratePostUtils


def _build_choose_final_lots_messages(
    final_agent_messages: list,
    descriptions_for_lots: str,
    final_lots_amount: int,
    min_lots_amount: int,
) -> list:
    return [
        SystemMessage(content=get_instructions("choose_final_lots.md")),
        *final_agent_messages,
        HumanMessage(
            content=(
                "Choose the best lots based on the following descriptions:\n"
                f"{descriptions_for_lots}\n\n"
                f"Return between {min_lots_amount} and {final_lots_amount} lots, ordered from best to worst.\n"
                "Each lot_id must appear exactly once.\n"
                "Do not request more inventory; send the best available lots from the list below."
            )
        ),
    ]


async def _invoke_final_lots_llm(
    messages: list,
    response_schema: type[BaseModel],
    *,
    min_lots_amount: int,
    max_attempts: int = 3,
) -> BaseModel:
    llm = get_choose_final_lots_llm()
    structured_llm = llm.with_structured_output(response_schema)
    feedback: list[HumanMessage] = []

    for attempt in range(max_attempts):
        try:
            response = await structured_llm.ainvoke(messages + feedback)
            return coerce_structured_model(response, response_schema)
        except ValidationError as exc:
            if attempt + 1 >= max_attempts:
                raise ValueError(
                    f"Final lot selection returned an invalid list. "
                    f"Need between {min_lots_amount} and the available pool size. "
                    f"Details: {exc.errors()[0]['msg'] if exc.errors() else exc}"
                ) from exc
            feedback.append(
                HumanMessage(
                    content=(
                        f"Your previous answer failed validation: {exc}. "
                        f"Return between {min_lots_amount} unique lot_ids from the provided list."
                    )
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            if attempt + 1 >= max_attempts:
                raise ValueError(
                    "Final lot selection returned an unexpected response format. "
                    "Please try generating again."
                ) from exc
            feedback.append(
                HumanMessage(
                    content=(
                        "Your previous answer was malformed. "
                        f"Return a JSON object with a lot_ids array containing "
                        f"between {min_lots_amount} unique integer ids from the list above."
                    )
                )
            )

    raise ValueError("Final lot selection failed after several attempts.")


@log_async_execution_time("Choose final lots")
async def choose_final_lots_node(state: AgentsState, runtime: Runtime[AgentsRuntimeContext]) -> AgentsState:
    await GeneratePostUtils.edit_message_for_user(
        message_id=runtime.context["editable_message_id"],
        text="🔄 Final choosing phase...\n"
        "▶️ Approximately 2-4 min left",
        user_uuid=runtime.context["user_uuid"],
    )
    image_descriptions = state["cumulated_images_description"]
    lot_chooser_result = state["cumulated_lots"]
    final_agent_messages = state.get("final_agent_messages", [])

    descriptions_for_lots_raw = []
    for img_desc in image_descriptions:
        for lot in lot_chooser_result:
            if lot.lot_id == img_desc.lot_id:
                descriptions_for_lots_raw.append(
                    f"# Lot ID: {lot.lot_id}\n"
                    f"Image Description: {img_desc.descriptions.description}\n"
                    f"Image Good Aspects: {img_desc.descriptions.good_aspect}\n"
                    f"Image Bad Aspects: {img_desc.descriptions.bad_aspect}\n"
                    f"Lot Description: {lot.description}\n"
                )
                break

    if not descriptions_for_lots_raw:
        return {
            "is_error": True,
            "error_message": (
                "No lots with photos were available for final review. "
                "Please try generating again or adjust your search filters."
            ),
        }

    max_target = runtime.context["result_lots_count"]
    min_target = runtime.context["min_lots_count"]
    available_count = len(descriptions_for_lots_raw)

    if available_count < min_target:
        lots_needed = min_target - available_count
        await GeneratePostUtils.edit_message_for_user(
            message_id=runtime.context["editable_message_id"],
            text=(
                f"🔄 Need at least {min_target} lots ({available_count} ready).\n"
                "▶️ Fetching more inventory..."
            ),
            user_uuid=runtime.context["user_uuid"],
        )
        return {
            "is_need_more_lots": True,
            "lots_needed": lots_needed,
        }

    descriptions_for_lots = "\n\n".join(descriptions_for_lots_raw)
    final_lots_amount = min(available_count, max_target)
    min_lots_amount = min(min_target, final_lots_amount)

    messages = _build_choose_final_lots_messages(
        final_agent_messages,
        descriptions_for_lots,
        final_lots_amount,
        min_lots_amount,
    )

    response_schema = get_final_lots_response_schema(min_lots_amount, final_lots_amount)
    try:
        response = await _invoke_final_lots_llm(
            messages,
            response_schema,
            min_lots_amount=min_lots_amount,
        )
    except ValueError as exc:
        return {"is_error": True, "error_message": str(exc)}

    ai_msg = AIMessage(content=response.model_dump_json())

    return {
        "is_need_more_lots": False,
        "lots_needed": 0,
        "final_lot_ids": response.lot_ids,
        "final_agent_messages": [ai_msg] + messages,
        "messages": [RemoveMessage(id="__remove_all__")],
    }


def final_router(state: AgentsState) -> str | None:
    is_need_more_lots = state.get("is_need_more_lots")
    is_error = state.get("is_error", False)
    if is_error:
        return "send_error_to_user"

    if is_need_more_lots:
        return "more_lots_needed"
    return "send_posts_to_user"
