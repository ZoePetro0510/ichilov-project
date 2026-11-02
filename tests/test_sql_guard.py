import pytest

from app.agent.sql_guard import UnsafeSQL, validate_select


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT count(*) FROM documents",
        "select title from documents where category = 'תרופות' order by published_date limit 3;",
        "SELECT d.title FROM public.documents d",
        "SELECT category, count(*) FROM documents GROUP BY category",
        "SELECT created_at FROM documents  -- trailing comment",
    ],
)
def test_valid_queries_pass(sql):
    assert validate_select(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM documents",
        "DROP TABLE documents",
        "UPDATE documents SET title = 'x'",
        "INSERT INTO documents(title) VALUES ('x')",
        "SELECT 1; DROP TABLE documents",
        "SELECT * FROM chunks",
        "SELECT * FROM documents JOIN chunks ON chunks.document_id = documents.id",
        "SELECT * FROM pg_shadow",
        "SELECT * FROM information_schema.tables",
        "SELECT 1",
        "",
        "   ;  ",
        "SELECT * INTO newtable FROM documents",
        "COPY documents TO '/tmp/x'",
    ],
)
def test_unsafe_queries_rejected(sql):
    with pytest.raises(UnsafeSQL):
        validate_select(sql)
