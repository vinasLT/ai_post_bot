from langgraph.runtime import Runtime

from app.core.logger import log_async_execution_time
from app.database.crud.post import PostService
from app.database.crud.request_filter import RequestFiltersService
from app.database.db.session import get_async_db
from app.database.enums import RequestStage
from app.services.post_generation.lang_chain_agent.state_context import AgentsState, AgentsRuntimeContext
from app.services.post_generation.lang_chain_agent.utils import GeneratePostUtils

@log_async_execution_time('Sending lots to user')
async def send_lots_to_user_node(state: AgentsState, runtime: Runtime[AgentsRuntimeContext]):
    final_lot_ids = state.get("final_lot_ids", [])
    min_lots = runtime.context["min_lots_count"]
    if len(final_lot_ids) < min_lots:
        raise ValueError(
            f"Only {len(final_lot_ids)} lots could be selected; at least {min_lots} are required."
        )

    request_id = runtime.context["request_id"]
    user_uuid = runtime.context["user_uuid"]
    async with get_async_db() as db:
        post_service = PostService(db)
        _, missing = await post_service.validate_lot_ids_for_request(request_id, final_lot_ids)
        if missing:
            saved = sorted(await post_service.get_lot_ids_for_request(request_id))
            raise ValueError(
                f"Final lot selection includes lot_ids not saved for this request: {sorted(missing)}. "
                f"Saved lot_ids: {saved}"
            )
        posts = await post_service.left_only_this_lot_ids(request_filter_id=request_id, lot_ids=final_lot_ids)

        posts = await GeneratePostUtils.update_average_price_for_posts(posts)

    await GeneratePostUtils.edit_message_for_user(
        message_id=runtime.context['editable_message_id'],
        text="Sending your lots...",
        user_uuid=user_uuid
    )
    await GeneratePostUtils.send_response_to_user(posts, request_id, user_uuid)

    async with get_async_db() as db:
        requests_service = RequestFiltersService(db)
        await requests_service.set_request_stage(request_id, RequestStage.COMPLETED)