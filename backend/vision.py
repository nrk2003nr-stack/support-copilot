import base64
from fastapi import APIRouter, File, UploadFile, Depends
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from auth import get_current_user

vision_router = APIRouter(prefix="/vision", tags=["vision"])
vision_model = ChatOpenAI(model="gpt-4o", max_tokens=1000)

async def analyze_image_with_text(image_bytes: bytes, user_question: str) -> str:
    """
    Send image + user question to GPT-4o vision.
    Returns a text description/answer combining both inputs.
    """
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    message = HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_image}",
                "detail": "high"
            }
        },
        {
            "type": "text",
            "text": f"The user uploaded this image and asked: '{user_question}'. "
                    f"Analyze the image in the context of a support request and provide a helpful response."
        }
    ])
    response = await vision_model.ainvoke([message])
    return response.content

@vision_router.post("/analyze")
async def analyze_image(
    question: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    image_bytes = await file.read()
    answer = await analyze_image_with_text(image_bytes, question)
    return {"answer": answer, "filename": file.filename}