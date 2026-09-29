from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Result(Model):
    id = fields.UUIDField(primary_key=True)
    search_key = fields.CharField(max_length=256, unique=True)
    url = fields.CharField(max_length=512)
    content = fields.JSONField()
    # Bumped whenever /search serves this row. Rows nobody asks for stop being
    # refreshed and are eventually purged (see app/tasks.py).
    last_accessed_at = fields.DatetimeField(auto_now_add=True, db_index=True)


# last_accessed_at is internal bookkeeping; keep the API response shape unchanged.
Result_Pydantic = pydantic_model_creator(
    Result, name="Result", exclude=("last_accessed_at",)
)
ResultIn_Pydantic = pydantic_model_creator(
    Result, name="ResultIn", exclude_readonly=True, exclude=("last_accessed_at",)
)
