"""
MessageRole -
enum Restricts role values to exactly user, assistant, 
or system. Using an enum instead of 
plain string means if you typo "assitant" somewhere, 
Pydantic throws an error immediately rather than silently passing garbage to model.

Message -
The atomic unit of conversation. Every message has a 
role and content. This maps directly to what the Groq 

API expects — so you can pass a list[Message] straight into 
the API call without reformatting.

ChatRequest
What Streamlit sends to FastAPI when the user hits send:

message — the new user input
session_id — ties the conversation to a user session 
so multiple browser tabs don't bleed into each other

history — the full prior conversation, because Groq 
(like all LLMs) is stateless. Every call must include 
the full history or it forgets everything.

ChatResponse
What FastAPI sends back:
reply — the LLM's response text
tools_used — which tools the LangChain agent called
 (e.g. ["get_stock_price", "search_news"]).
 Useful to show in the Streamlit UI so the
   user knows what data was fetched.

"""


from pydantic import BaseModel
from enum import Enum

class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class Message(BaseModel):
    role: MessageRole
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: list[Message] = []

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tools_used: list[str] = []