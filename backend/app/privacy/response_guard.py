from app.models import AliasItem


def verify_response(
    response: str,
    aliases: list[AliasItem],
) -> dict:

    missing_tokens = []

    for alias in aliases:

        # If the AI response contains the original
        # private value, that is potentially a leak.

        if alias.original in response:

            missing_tokens.append(
                {
                    "type": alias.type,
                    "original": alias.original,
                    "alias": alias.alias,
                }
            )

    return {
        "safe": len(missing_tokens) == 0,
        "potential_leaks": missing_tokens,
    }