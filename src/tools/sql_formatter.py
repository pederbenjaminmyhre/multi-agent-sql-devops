import sqlparse
from langchain_core.tools import tool


@tool
def format_sql(sql: str) -> str:
    """Format a T-SQL string with consistent style: uppercase keywords, 4-space indent, trailing semicolons."""
    formatted = sqlparse.format(
        sql,
        keyword_case="upper",
        identifier_case=None,
        reindent=True,
        indent_width=4,
        strip_comments=False,
        comma_first=False,
    )
    # Ensure trailing semicolon on each statement
    statements = sqlparse.split(formatted)
    cleaned = []
    for stmt in statements:
        stmt = stmt.strip()
        if stmt and not stmt.endswith(";"):
            stmt += ";"
        if stmt:
            cleaned.append(stmt)
    return "\n\n".join(cleaned)


SQL_FORMAT_TOOLS = [format_sql]
