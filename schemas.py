from marshmallow import Schema, fields, validate

from tokens import TOKEN_TYPES


class TeacherTokenRowSchema(Schema):
    student_id = fields.Int(required=True, validate=validate.Range(min=1), error_messages={
        'required': 'ID студента обязателен',
        'invalid': 'ID студента должен быть числом',
        'validator_failed': 'ID студента должен быть положительным числом'
    })
    tokens = fields.List(fields.Str(), load_default=list, validate=validate.Length(max=len(TOKEN_TYPES)), error_messages={
        'validator_failed': f'Можно выбрать не более {len(TOKEN_TYPES)} типов жетонов'
    })


class SubmitTeacherTokensSchema(Schema):
    group_id = fields.Int(required=True, validate=validate.Range(min=1), error_messages={
        'required': 'ID группы обязателен',
        'validator_failed': 'ID группы должен быть положительным числом'
    })
    grades = fields.List(fields.Nested(TeacherTokenRowSchema), required=True, validate=validate.Length(min=1), error_messages={
        'required': 'Список записей обязателен',
        'validator_failed': 'Должна быть хотя бы одна строка'
    })


class AdminGradeRowSchema(Schema):
    student_id = fields.Int(required=True, validate=validate.Range(min=1), error_messages={
        'required': 'ID студента обязателен',
        'invalid': 'ID студента должен быть числом',
        'validator_failed': 'ID студента должен быть положительным числом'
    })
    grade = fields.Int(required=True, validate=validate.Range(min=1, max=5), error_messages={
        'required': 'Оценка (звёзды) обязательна',
        'invalid': 'Оценка должна быть числом',
        'validator_failed': 'Оценка должна быть от 1 до 5'
    })
    comment = fields.Str(allow_none=True, validate=validate.Length(max=1000), load_default='')


class AdminSubmitGradesSchema(Schema):
    subject_id = fields.Int(required=True, validate=validate.Range(min=1), error_messages={
        'required': 'ID предмета обязателен',
        'invalid': 'ID предмета должен быть числом',
        'validator_failed': 'ID предмета должен быть положительным числом'
    })
    grades = fields.List(fields.Nested(AdminGradeRowSchema), required=True, validate=validate.Length(min=1), error_messages={
        'required': 'Список оценок обязателен',
        'validator_failed': 'Должна быть хотя бы одна оценка'
    })

class InvitationSchema(Schema):
    student_id = fields.Int(required=True, validate=validate.Range(min=1), error_messages={
        'required': 'ID студента обязателен',
        'invalid': 'ID студента должен быть числом',
        'validator_failed': 'ID студента должен быть положительным числом'
    })
    position = fields.Str(required=True, validate=validate.Length(min=1, max=200), error_messages={
        'required': 'Должность обязательна',
        'validator_failed': 'Должность должна быть от 1 до 200 символов'
    })
    message = fields.Str(allow_none=True, validate=validate.Length(max=2000), load_default='', error_messages={
        'validator_failed': 'Сообщение слишком длинное (максимум 2000 символов)'
    })

