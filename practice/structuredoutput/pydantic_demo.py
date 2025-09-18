from pydantic import BaseModel, Field, EmailStr
from typing import Optional 

class Student(BaseModel):
    name: str # for default value just write ='nitish'
    age: Optional[int] = None
    cgpa: float = Field(gt=0,lt=10, default=5, description='A decimal value representing the cgpa of the student')
    email: EmailStr

new_student = {'name':'nitish','cgpa':'9.8', 'email':'abc@abc.com'}

student = Student(**new_student)

print(dict(student))
print(type(student))
student_json =student.model_dump_json()
