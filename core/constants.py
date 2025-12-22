"""Multilingual Constants for Trinity System.

This file centralizes all keywords used for:
1. Task classification (DEV vs GENERAL)
2. Verification verdict markers (Success, Failure, Negations)
3. Vision-based failure detection
4. Termination and system messages
"""

# -----------------------------------------------------------------------------
# TASK CLASSIFICATION (Atlas _classify_task)
# -----------------------------------------------------------------------------
DEV_KEYWORDS = [
    "код", "code", "python", "javascript", "typescript", "script", "function",
    "рефакторинг", "refactor", "тест", "test", "git", "commit", "branch",
    "архітектура", "architecture", "api", "database", "db", "sql",
    "windsurf", "editor", "ide", "файл", "file", "write", "create"
]

GENERAL_KEYWORDS = [
    "фільм", "movie", "video", "youtube", "netflix", "браузер", "browser",
    "музика", "music", "spotify", "apple music", "відкрий", "open",
    "переглянь", "watch", "слухай", "listen", "грай", "play",
    "скачай", "download", "завантаж", "upload", "фото", "photo",
    "картинка", "image", "розташування", "location", "карта", "map",
    "погода", "weather", "новини", "news", "соціальна мережа", "social",
    "email", "mail", "повідомлення", "message", "чат", "chat"
]

MEDIA_KEYWORDS = [
    "фільм", "movie", "video", "youtube", "netflix", "дивитись", 
    "watch", "серіал", "serial", "film", "музика", "music", "play"
]

# -----------------------------------------------------------------------------
# VERIFICATION MARKERS (Grisha verdict)
# -----------------------------------------------------------------------------
SUCCESS_MARKERS = [
    "verified", "success", "confirmed", "passed", "step_completed", "completed", "done",
    "успішно", "виконано", "готово", "підтверджено",
    "виконана", "виконаний", "готова", "готовий", "підтверджена", "підтверджений"
]

FAILURE_MARKERS = [
    "[failed]", "failed", "failure", "critical error", "fatal error",
    "verification failed", "unable to verify", "not achieved", "goal not met",
    "помилка", "невдача", "не вдалося", "не виконано", "не готова", "не готовий",
    "не вдалося", "не вдалось", "неможливо"
]

TERMINATION_MARKERS = [
    "[verified]", "[achievement_confirmed]", "[task_done]", "[success]",
    "[підтверджено]", "[виконано]"
]

UNCERTAIN_MARKERS = [
    "uncertain", "uncertain", "not sure", "insufficient data",
    "непевно", "невідомо", "недостатньо даних"
]

# -----------------------------------------------------------------------------
# NEGATION DETECTION (Regex patterns)
# -----------------------------------------------------------------------------
# Patterns that indicate the PREVIOUS keyword is negated
# Example: "not successful", "не виконано"
NEGATION_PATTERNS = {
    "en": r"\b(?:not|no|cannot|can't|unable)\b",
    "uk": r"\b(?:не|ні|немає|неможливо|не вдалося|не вдалось)\b",
}

# -----------------------------------------------------------------------------
# VISION FAILURE INDICATORS (multilingual)
# -----------------------------------------------------------------------------
VISION_FAILURE_KEYWORDS = [
    "no video playing", "no video in fullscreen", "nothing playing",
    "page is empty", "about:blank", "not found", "404", "error loading",
    "the task was not completed", "goal not achieved", "not playing",
    "not in fullscreen", "no active video", "no evidence of", "does not show",
    "не відтворюється", "відео не грає", "сторінка порожня", 
    "помилка завантаження", "завдання не виконано", "ціль не досягнута",
    # CAPTCHA detection keywords
    "captcha", "sorry/index", "unusual traffic", "blocked", "recaptcha",
    "hcaptcha", "links: []", "empty links", "no search results", "verify you are human"
]

# -----------------------------------------------------------------------------
# SYSTEM MESSAGES (Multilingual templates)
# -----------------------------------------------------------------------------
MESSAGES = {
    "en": {
        "step_limit_reached": "Step limit reached ({limit}).",
        "replan_limit_reached": "Replan limit reached ({limit}).",
        "task_achieved": "All plan steps completed successfully. Task achieved.",
        "plan_empty": "The plan is empty.",
        "clueless_pause": "Doctor Vibe: Detected an unknown stop. Please clarify the task.",
        "native_failed_switching_gui": "[VOICE] Native mode failed. Switching to GUI mode.",
        "uncertainty_limit": "[SYSTEM] Uncertainty limit reached. Marking as FAILED."
    },
    "uk": {
        "step_limit_reached": "Ліміт кроків вичерпано ({limit}).",
        "replan_limit_reached": "Ліміт перепланувань вичерпано ({limit}).",
        "task_achieved": "Усі кроки плану успішно виконано. Ціль досягнута.",
        "plan_empty": "План порожній.",
        "clueless_pause": "Doctor Vibe: Виявлено невідому зупинку системи. Будь ласка, уточніть завдання.",
        "native_failed_switching_gui": "[VOICE] Native режим не спрацював. Перемикаюся на GUI режим.",
        "uncertainty_limit": "[SYSTEM] Ліміт невизначеності досягнуто. Помічаю як FAILED."
    }
}
# -----------------------------------------------------------------------------
# INTERNAL CONSTANTS (Literal replacements)
# -----------------------------------------------------------------------------
UNKNOWN_STEP = "Unknown step"
STEP_COMPLETED_MARKER = "[STEP_COMPLETED]"
VOICE_MARKER = "[VOICE]"
DEFAULT_MODEL_FALLBACK = "gpt-4.1"
