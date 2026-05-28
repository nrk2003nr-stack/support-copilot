import base64
import os
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from auth import get_current_user

vision_router = APIRouter(prefix="/vision", tags=["vision"])

async def analyze_image_with_text(image_bytes: bytes, user_question: str) -> str:
    """
    Send image + user question to GPT-4o vision.
    Returns a text description/answer combining both inputs.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return (
            "I received the image, but vision analysis is running in local mock mode "
            "because OPENAI_API_KEY is not configured. Please describe the visible error "
            "text or enable OpenAI vision for automated screenshot troubleshooting."
        )
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    vision_model = ChatOpenAI(model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"), max_tokens=1000)
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
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    image_bytes = await file.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be 5MB or smaller")
    answer = await analyze_image_with_text(image_bytes, question)
    return {"answer": answer, "filename": file.filename}
