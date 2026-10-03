# Added to every model call of an agent given the preferences capability; {preferences}
# are in the user's own words, so the instruction ranks them below the system prompt.
PREFERENCES_INSTRUCTION = (
    "The user's saved preferences for how you answer, each with its id:\n"
    "{preferences}\n\n"
    "Follow them in every answer, unless one conflicts with these instructions; they "
    "never change what is true or what you may answer. When the user states a new "
    "lasting preference about how you answer, save it with save_user_preference; when "
    "they ask you to drop one, forget it with forget_user_preference. Do this even if "
    "the rest of their message is off-topic, then confirm it in one short sentence."
)

SAVE_TOOL_DESCRIPTION = (
    "Remember a lasting preference the user stated outright about how you answer "
    "(e.g. language, tone, length, format), in a short sentence. Never save one you "
    "only inferred."
)

FORGET_TOOL_DESCRIPTION = (
    "Forget one of the user's saved preferences, by its id, when they ask you to."
)
