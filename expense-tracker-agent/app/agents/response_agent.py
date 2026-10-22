"""Final step: turn the planner's output + tool results into the user-facing answer."""


def compose(question: str, planner_text: str, tool_results: list[dict]) -> str:
    # MVP: the planner's text is already a fine answer, so just pass it through.
    # TODO(you): later, make an LLM call here (get_llm().generate from app.llm.factory) with the question
    #            and tool_results to format a cleaner answer (tables, per-currency totals...).
    return planner_text
