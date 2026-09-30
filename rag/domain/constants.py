# Chat
MAX_MESSAGE_LENGTH = 8192  # characters in one user message

# Conversation list paging
DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100

# Conversation titles
FALLBACK_TITLE_LENGTH = (
    60  # the title cut from the message when the LLM can't write one
)
MAX_TITLE_LENGTH = 80  # cap on an LLM-written title
# Only the start of the message is needed to title it; caps the title call's cost.
TITLE_MESSAGE_EXCERPT = 1000
# The client waits on this for the sidebar title; don't hold it on a slow LLM.
TITLE_TIMEOUT_SECONDS = 10

# Retrieval
SEARCH_TOP_K = 3  # passages the knowledge-base search returns
RRF_K = 5  # reciprocal-rank-fusion constant when merging vector and full-text results

# Agent
LLM_RETRY_ATTEMPTS = 3  # tries per LLM call before falling back
MAX_REVISIONS = 1  # times the groundedness guard sends an answer back per turn

# Knowledge-base uploads
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024  # size of an uploaded zip
MAX_ARCHIVE_MEMBERS = 1000  # markdown files in one archive
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # what the archive may expand to

# What GET /api/settings reports; static until the real values are exposed.
REPORTED_MODEL = "gpt-4o-mini"
REPORTED_TEMPERATURE = 0.2
