from tortoise import models, fields


class User(models.Model):
    id = fields.IntField(pk=True, generated=True)
    name = fields.CharField(max_length=50)
    email = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=50)
    authenticator_mfa_enabled = fields.BooleanField(default=False)
    key = fields.CharField(max_length=16, null=True)
    email_mfa_enabled = fields.BooleanField(default=False)
    code = fields.CharField(max_length=6, null=True)
