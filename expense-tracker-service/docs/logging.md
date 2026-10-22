# Logging

* Setup: `app/logging_config.py`. Format: `time LEVEL request_id=<id> logger | message`.
* A `ContextVar` holds the request ID; a logging `Filter` stamps it on every record, so even deep repository code logs the ID without receiving it as a parameter.
* `LOG_LEVEL` = DEBUG | INFO | WARNING | ERROR. INFO shows request start/finish and business events (`expense_created`); DEBUG adds component/action traces; 4xx completions log at WARNING; unexpected exceptions log at ERROR with stack trace (`logger.exception`).
* `SQL_ECHO=true` turns on SQLAlchemy statement logging independently.
* Never logged: request bodies, field values from validation errors, secrets.
* Trace: take `X-Request-ID` from the response header and `grep` it in the server output.
* uvicorn's own access log is disabled to avoid duplicates.
