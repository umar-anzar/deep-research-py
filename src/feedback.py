from typing import Annotated
from pydantic import BaseModel, Field


from .prompt import system_prompt
from .providers import get_model, generate_object


async def generate_feedback(query: str, num_questions: int = 3):

  class QuestionList(BaseModel):
    questions: Annotated[list[str], Field(description=f"Follow up questions to clarify the research direction, max of {num_questions}")]
  
  prompt=(
    f"Given the following query from the user, ask some follow up questions to clarify the research direction." 
    f"Return a maximum of {num_questions} questions, but feel free to return less if the original query is clear: <query>{query}</query>"
  )
  user_feedback = await generate_object(
    model=get_model(),
    system=system_prompt(),
    prompt=prompt,
    schema=QuestionList
  )

  return user_feedback.questions[0: num_questions]
