import os
import uuid

import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client


# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY"
)

MODEL_URL = os.getenv(
    "MEENAMITRA_MODEL_URL"
)

MODEL_API_KEY = os.getenv(
    "MEENAMITRA_MODEL_API_KEY"
)


# ==========================================================
# VALIDATE ENVIRONMENT VARIABLES
# ==========================================================

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL is missing"
    )


if not SUPABASE_PUBLISHABLE_KEY:
    raise RuntimeError(
        "SUPABASE_PUBLISHABLE_KEY is missing"
    )


if not MODEL_URL:
    raise RuntimeError(
        "MEENAMITRA_MODEL_URL is missing"
    )


if not MODEL_API_KEY:
    raise RuntimeError(
        "MEENAMITRA_MODEL_API_KEY is missing"
    )


# ==========================================================
# SUPABASE CLIENT
# ==========================================================

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
)


# ==========================================================
# FASTAPI APP
# ==========================================================

app = FastAPI(
    title="MeenaMitra API",
    description="AI-powered aquaculture advisor",
    version="1.0.0"
)


# ==========================================================
# CORS
# ==========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],

    allow_origin_regex=r"https://.*\.vercel\.app",

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ==========================================================
# REQUEST MODELS
# ==========================================================

class AuthRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChatRequest(BaseModel):
    question: str
    access_token: str
    conversation_id: str | None = None


# ==========================================================
# TELUGU LANGUAGE DETECTION
# ==========================================================

def contains_telugu(text: str) -> bool:
    """
    Detect Telugu Unicode characters.

    Telugu Unicode range:
    U+0C00 - U+0C7F
    """

    return any(
        "\u0c00" <= char <= "\u0c7f"
        for char in text
    )


def get_language_instruction(
    question: str
) -> str:

    if contains_telugu(question):

        return (
            "LANGUAGE REQUIREMENT:\n"
            "The user wrote the question in Telugu.\n"
            "You MUST answer entirely in natural Telugu script.\n"
            "Do NOT answer in English.\n"
            "Do NOT translate the question into English.\n"
            "Do NOT mix English sentences with Telugu.\n"
            "Technical abbreviations such as pH, DO and ppm may remain "
            "in their standard form when necessary.\n"
            "The main explanation must be in Telugu."
        )

    return (
        "LANGUAGE REQUIREMENT:\n"
        "The user wrote the question in English.\n"
        "Answer in clear, simple English."
    )


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "message": "MeenaMitra API is running",
        "model": "Qwen2.5-1.5B fine-tuned for aquaculture"
    }


# ==========================================================
# HEALTH
# ==========================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


@app.head("/health")
def health_head():

    return None


# ==========================================================
# SIGNUP
# ==========================================================

@app.post("/signup")
def signup(data: AuthRequest):

    try:

        result = supabase.auth.sign_up(
            {
                "email": data.email,
                "password": data.password
            }
        )

        session = result.session
        user = result.user

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Signup failed"
            )

        response = {
            "message": "Signup successful",
            "email": user.email
        }

        if session:

            response["access_token"] = (
                session.access_token
            )

            response["refresh_token"] = (
                session.refresh_token
            )

        return response

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==========================================================
# LOGIN
# ==========================================================

@app.post("/login")
def login(data: AuthRequest):

    try:

        result = supabase.auth.sign_in_with_password(
            {
                "email": data.email,
                "password": data.password
            }
        )

        if not result.session:
            raise HTTPException(
                status_code=401,
                detail="Login failed"
            )

        return {
            "message": "Login successful",

            "access_token":
                result.session.access_token,

            "refresh_token":
                result.session.refresh_token,

            "email":
                result.user.email
                if result.user
                else data.email
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


# ==========================================================
# REFRESH ACCESS TOKEN
# ==========================================================

@app.post("/refresh")
def refresh_token(
    data: RefreshRequest
):

    try:

        result = supabase.auth.refresh_session(
            data.refresh_token
        )

        if not result.session:

            raise HTTPException(
                status_code=401,
                detail="Could not refresh session"
            )

        return {
            "message": "Token refreshed",

            "access_token":
                result.session.access_token,

            "refresh_token":
                result.session.refresh_token,

            "email":
                result.user.email
                if result.user
                else None
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


# ==========================================================
# CHAT
# ==========================================================

@app.post("/chat")
async def chat(data: ChatRequest):

    question = data.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )


    # ======================================================
    # 1. VERIFY USER
    # ======================================================

    try:

        user_result = supabase.auth.get_user(
            data.access_token
        )

        if not user_result or not user_result.user:

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        user_id = user_result.user.id

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


    # ======================================================
    # 2. GET OR CREATE CONVERSATION ID
    # ======================================================

    if data.conversation_id:

        conversation_id = data.conversation_id

        # --------------------------------------------------
        # Verify that the conversation belongs to this user
        # --------------------------------------------------

        try:

            existing = (
                supabase
                .table("chat_history")
                .select("id")
                .eq(
                    "conversation_id",
                    conversation_id
                )
                .eq(
                    "user_id",
                    user_id
                )
                .limit(1)
                .execute()
            )

            if not existing.data:

                raise HTTPException(
                    status_code=403,
                    detail="Conversation does not belong to this user"
                )

        except HTTPException:
            raise

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Could not verify conversation: "
                    f"{str(e)}"
                )
            )

    else:

        # --------------------------------------------------
        # FIRST MESSAGE OF NEW CONVERSATION
        # --------------------------------------------------

        conversation_id = str(
            uuid.uuid4()
        )


    # ======================================================
    # 3. LOAD PREVIOUS MESSAGES
    # ======================================================

    try:

        previous_result = (
            supabase
            .table("chat_history")
            .select(
                "question, answer, created_at"
            )
            .eq(
                "conversation_id",
                conversation_id
            )
            .eq(
                "user_id",
                user_id
            )
            .order(
                "created_at",
                desc=False
            )
            .limit(8)
            .execute()
        )

        previous_messages = (
            previous_result.data or []
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not load conversation history: "
                f"{str(e)}"
            )
        )


    # ======================================================
    # 4. LANGUAGE
    # ======================================================

    language_instruction = (
        get_language_instruction(
            question
        )
    )


    # ======================================================
    # 5. SYSTEM PROMPT
    # ======================================================

    system_prompt = (

        "You are MeenaMitra, a specialized AI advisor "
        "for small-scale pond-based fish farming and "
        "aquaculture.\n\n"

        "Your purpose is to provide practical, safe and "
        "understandable advice to fish farmers.\n\n"

        "IMPORTANT RULES:\n"

        "1. Answer the farmer's actual question.\n"

        "2. Stay focused on pond fish farming and "
        "aquaculture.\n"

        "3. Do not discuss aquariums unless explicitly "
        "asked.\n"

        "4. Give simple and practical advice.\n"

        "5. Do not invent exact values when important "
        "information is missing.\n"

        "6. Consider fish species, fish size, biomass, "
        "pond size, temperature, dissolved oxygen, pH, "
        "ammonia, feeding and pond conditions when "
        "relevant.\n"

        "7. If important information is missing, explain "
        "what information the farmer should provide.\n"

        "8. Never generate programming code unless "
        "explicitly requested.\n"

        "9. Never generate unrelated languages.\n"

        "10. Keep answers concise but useful.\n\n"

        + language_instruction
    )


    # ======================================================
    # 6. BUILD MODEL MESSAGES
    # ======================================================

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]


    # ------------------------------------------------------
    # Previous conversation context
    # ------------------------------------------------------

    for item in previous_messages:

        messages.append(
            {
                "role": "user",
                "content": item["question"]
            }
        )

        messages.append(
            {
                "role": "assistant",
                "content": item["answer"]
            }
        )


    # ------------------------------------------------------
    # Current question
    # ------------------------------------------------------

    messages.append(
        {
            "role": "user",
            "content": question
        }
    )


    # ======================================================
    # 7. MODEL REQUEST
    # ======================================================

    payload = {

        "model": "meenamitra",

        "messages": messages,

        "temperature": 0.25,

        "top_p": 0.9,

        "repeat_penalty": 1.1,

        "max_tokens": 250
    }


    try:

        timeout = httpx.Timeout(

            connect=10.0,

            read=180.0,

            write=30.0,

            pool=30.0
        )


        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.post(

                f"{MODEL_URL.rstrip('/')}"
                "/v1/chat/completions",

                headers={
                    "Authorization":
                        f"Bearer {MODEL_API_KEY}"
                },

                json=payload
            )


            if response.status_code != 200:

                raise HTTPException(

                    status_code=502,

                    detail=(
                        "Model server error: "
                        f"{response.text}"
                    )
                )


            result = response.json()


            try:

                answer = (
                    result["choices"][0]
                    ["message"]
                    ["content"]
                    .strip()
                )

            except (
                KeyError,
                IndexError,
                TypeError
            ):

                raise HTTPException(

                    status_code=502,

                    detail=(
                        "Unexpected response "
                        "from model server"
                    )
                )


    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=(
                "Model request failed: "
                f"{str(e)}"
            )
        )


    # ======================================================
    # 8. SAVE TO SUPABASE
    # ======================================================

    try:

        save_result = (

            supabase

            .table("chat_history")

            .insert(
                {
                    "user_id":
                        user_id,

                    "conversation_id":
                        conversation_id,

                    "question":
                        question,

                    "answer":
                        answer
                }
            )

            .execute()
        )


        if not save_result.data:

            raise Exception(
                "Supabase did not return saved record"
            )


    except Exception as e:

        print(
            "HISTORY SAVE ERROR:",
            str(e)
        )

        # IMPORTANT:
        # Do not silently return success if the
        # database save failed.

        raise HTTPException(

            status_code=500,

            detail=(
                "AI answered successfully, but "
                "the conversation could not be saved: "
                f"{str(e)}"
            )
        )


    # ======================================================
    # 9. RETURN RESPONSE
    # ======================================================

    return {

        "conversation_id":
            conversation_id,

        "question":
            question,

        "answer":
            answer
    }


# ==========================================================
# HISTORY
# ==========================================================

@app.get("/history")
def history(
    authorization: str | None = Header(default=None)
):

    # ======================================================
    # 1. GET ACCESS TOKEN FROM AUTHORIZATION HEADER
    # ======================================================

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is missing"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header"
        )

    access_token = authorization[
        len("Bearer "):
    ].strip()

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Access token is missing"
        )


    # ======================================================
    # 2. VERIFY USER
    # ======================================================

    try:

        user_result = supabase.auth.get_user(
            access_token
        )

        if (
            not user_result
            or not user_result.user
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        user_id = user_result.user.id

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


    # ======================================================
    # 3. LOAD USER'S CHAT HISTORY
    # ======================================================

    try:

        result = (
            supabase
            .table("chat_history")
            .select(
                "id, conversation_id, question, answer, created_at"
            )
            .eq(
                "user_id",
                user_id
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        rows = result.data or []

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load chat history: "
                f"{str(e)}"
            )
        )


    # ======================================================
    # 4. GROUP MESSAGES BY CONVERSATION
    # ======================================================

    conversations = {}


    for row in rows:

        conversation_id = row[
            "conversation_id"
        ]


        if conversation_id not in conversations:

            conversations[
                conversation_id
            ] = {

                "conversation_id":
                    conversation_id,

                "title":
                    row["question"],

                "created_at":
                    row["created_at"],

                "messages":
                    []
            }


        conversations[
            conversation_id
        ]["messages"].append(

            {
                "id":
                    row["id"],

                "question":
                    row["question"],

                "answer":
                    row["answer"],

                "created_at":
                    row["created_at"]
            }
        )


    # ======================================================
    # 5. RETURN GROUPED HISTORY
    # ======================================================

    return {
        "history":
            list(
                conversations.values()
            )
    }