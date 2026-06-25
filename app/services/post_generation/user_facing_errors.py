"""Map internal generation errors to messages suitable for Telegram users."""


def _vehicle_label(*, make: str | None = None, model: str | None = None) -> str:
    parts = [make or ""]
    if model:
        parts.append(model)
    label = " ".join(p for p in parts if p).strip()
    return label or "your search"


def lot_chooser_failed_message(
    *,
    make: str | None = None,
    model: str | None = None,
    min_lots: int,
    validation_errors: list[str] | None = None,
    agent_reason: str | None = None,
) -> str:
    """Explain lot-selection failures in plain language."""
    vehicle = _vehicle_label(make=make, model=model)

    if agent_reason:
        reason = agent_reason.strip().rstrip(".")
        return (
            f"We could not find suitable auction lots for {vehicle}. "
            f"{reason}. "
            f"Try broadening your filters (year range, mileage, or auction site) and search again."
        )

    errors_text = " ".join(validation_errors or []).lower()

    if "duplicate" in errors_text or "lot_id=0" in errors_text or "no valid lots" in errors_text:
        return (
            f"Lot selection for {vehicle} did not complete: the system could not build a valid list "
            f"of unique cars after several tries. Please wait a minute and try again, "
            f"or use slightly broader filters."
        )

    if "min_length" in errors_text or "minitems" in errors_text or "too_short" in errors_text:
        return (
            f"Not enough matching lots for {vehicle}. "
            f"We look for at least {min_lots} cars that pass quality filters, but fewer were available. "
            f"Try a wider year or mileage range, another model, or both Copart and IAAI if possible."
        )

    if "no matching posts" in errors_text:
        return (
            f"Selected lots for {vehicle} could not be loaded from our database. "
            f"Please try generating again."
        )

    return (
        f"Lot selection for {vehicle} failed after several attempts. "
        f"We need at least {min_lots} qualifying cars. "
        f"Try adjusting your search filters and run the request again."
    )


def generation_exception_message(message: str) -> str:
    """Turn a raw exception string into text suitable for users."""
    text = (message or "").strip()
    if not text:
        return "An unexpected error occurred. Please try again later."

    lowered = text.lower()
    if "schema validation failed" in lowered:
        return (
            "Lot selection did not finish after several attempts. "
            "Please try again in a few minutes or use broader search filters."
        )
    if "only" in lowered and "lots could be selected" in lowered:
        return text
    if "timeout" in lowered or "timed out" in lowered:
        return "The request took too long and was stopped. Please try again."
    if "openai" in lowered or "api key" in lowered:
        return "The AI service is temporarily unavailable. Please try again later."

    return text


def format_telegram_error(error_message: str, request_id: int | None) -> str:
    """Format an error notification for Telegram."""
    body = generation_exception_message(error_message)
    lines = ["❌ We could not finish generating your posts.", "", body]
    if request_id is not None:
        lines.extend(["", f"Reference: request #{request_id}"])
    return "\n".join(lines)
