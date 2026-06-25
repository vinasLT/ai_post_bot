from pydantic import BaseModel, Field, ConfigDict, conlist, model_validator


class LotObject(BaseModel):
    lot_id: int = Field(..., description="Lot ID from the auction API")
    description: str = Field(
        ...,
        description="Brief summary of what is good and bad about the lot",
    )


class ImageProcessingSchema(BaseModel):
    description: str = Field(..., description="Describe this vehicle")
    bad_aspect: str = Field(..., description="What aspect of the vehicle is bad?")
    good_aspect: str = Field(..., description="What aspect of the vehicle is good?")


class ImageProcessingResult(BaseModel):
    lot_id: int = Field(..., description="Lot ID")
    descriptions: ImageProcessingSchema


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lots: list[LotObject] | None = Field(
        None,
        description="Lots that you choose (ONLY UNIQUE VALUES)",
    )
    is_error: bool = False
    error_message: str | None = None

    @model_validator(mode="after")
    def normalize_lots(self):
        if self.is_error or not self.lots:
            return self

        seen: set[int] = set()
        unique_lots: list[LotObject] = []
        for lot in self.lots:
            if lot.lot_id <= 0 or lot.lot_id in seen:
                continue
            seen.add(lot.lot_id)
            unique_lots.append(lot)

        self.lots = unique_lots
        return self


def get_agent_result_parser(lots_min: int, lots_max: int) -> type[AgentResult]:
    """Lot chooser structured output. Use lots_min=1 to avoid forcing duplicate padding."""

    class LimitedAgentResult(AgentResult):
        lots: list[LotObject] = Field(
            ...,
            min_length=lots_min,
            max_length=lots_max,
            description="Lots that you choose (ONLY UNIQUE VALUES)",
        )

    return LimitedAgentResult


def get_final_lots_response_schema(min_lots: int, max_lots: int) -> type[BaseModel]:
    """Final lot selection structured output with min_lots <= count <= max_lots."""

    class FinalLotsResponse(BaseModel):
        model_config = ConfigDict(extra="forbid")

        lot_ids: list[int] = Field(
            ...,
            min_length=min_lots,
            max_length=max_lots,
            description="Unique lot ids, ordered best to worst",
        )
        is_need_more_lots: bool = Field(
            False,
            description="Always false; do not request more inventory at this step",
        )
        lots_needed: int = Field(
            0,
            description="Always 0 at this step",
        )

        @model_validator(mode="after")
        def normalize_lot_ids(self):
            seen: set[int] = set()
            unique_ids: list[int] = []
            for lot_id in self.lot_ids:
                if lot_id <= 0 or lot_id in seen:
                    continue
                seen.add(lot_id)
                unique_ids.append(lot_id)
            self.lot_ids = unique_ids
            if len(self.lot_ids) < min_lots:
                raise ValueError(
                    f"lot_ids must contain at least {min_lots} unique values after deduplication"
                )
            return self

    return FinalLotsResponse
