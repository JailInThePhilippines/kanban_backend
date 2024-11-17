from marshmallow import Schema, fields, validate

class UserSchema(Schema):
    _id = fields.Str(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=3, max=30))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=64))
    age = fields.Int(required=True, validate=validate.Range(min=18))
    created_at = fields.DateTime(dump_only=True)

class TaskSchema(Schema):
    _id = fields.Str(dump_only=True)
    title = fields.String(required=True)
    description = fields.String(required=True)
    due_date = fields.Date(required=True)
    status = fields.String(required=True)
    created_at = fields.DateTime()