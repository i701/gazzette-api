from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator


class Result(Model):
    id = fields.UUIDField(pk=True)
    search_key = fields.CharField(max_length=256, unique=True)
    content = fields.JSONField()


Result_Pydantic = pydantic_model_creator(Result, name="Result")
ResultIn_Pydantic = pydantic_model_creator(
    Result, name="ResultIn", exclude_readonly=True
)
