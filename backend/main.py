import os
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client


# ==========================================================
# ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
MODEL_URL = os.getenv("MEENAMITRA_MODEL_URL")


if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is missing")


if not SUPABASE_PUBLISHABLE_KEY:
    raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is missing")


if not MODEL_URL:
    raise RuntimeError("MEENAMITRA_MODEL_URL is missing")


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
)


# ==========================================================
# FASTAPI
# ==========================================================

app = FastAPI(
    title="MeenaMitra API",
    description="AI fish-farming advisor API",
    version="1.0.0"
)


# ==========================================================
# CORS
# ==========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# REQUEST MODELS
# ==========================================================

class AuthRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    question: str


class RefreshRequest(BaseModel):
    refresh_token: str


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


# ==========================================================
# SIGNUP
# ==========================================================

@app.post("/signup")
def signup(data: AuthRequest):

    try:

        result = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password
        })


        if not result.user:

            raise HTTPException(
                status_code=400,
                detail="Signup failed"
            )


        response = {
            "message": "Signup successful",
            "user_id": result.user.id
        }


        # If Supabase immediately provides a session
        if result.session:

            response["access_token"] = (
                result.session.access_token
            )

            response["refresh_token"] = (
                result.session.refresh_token
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

        result = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })


        if not result.session:

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )


        return {

            "access_token":
                result.session.access_token,

            "refresh_token":
                result.session.refresh_token,

            "user_id":
                result.user.id,

            "email":
                result.user.email
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
def refresh_token(data: RefreshRequest):

    try:

        result = supabase.auth.refresh_session(
            data.refresh_token
        )


        if not result.session:

            raise HTTPException(
                status_code=401,
                detail="Refresh token is invalid or expired"
            )


        return {

            "access_token":
                result.session.access_token,

            "refresh_token":
                result.session.refresh_token,

            "user_id":
                result.user.id,

            "email":
                result.user.email
        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "TOKEN REFRESH ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=401,
            detail="Refresh token is invalid or expired"
        )


# ==========================================================
# GET CURRENT USER
# ==========================================================

def get_current_user(
    authorization: str
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )


    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header"
        )


    token = authorization.replace(
        "Bearer ",
        "",
        1
    )


    try:

        user_response = (
            supabase.auth.get_user(token)
        )


        if not user_response.user:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )


        return user_response.user


    except HTTPException:

        raise


    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


# ==========================================================
# CHAT
# ==========================================================

@app.post("/chat")
async def chat(
    data: ChatRequest,
    authorization: str = Header(default="")
):

    user = get_current_user(
        authorization
    )


    question = data.question.strip()


    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )


    # ======================================================
    # MEENAMITRA SYSTEM PROMPT
    # ======================================================

    system_prompt = """
You are MeenaMitra, an AI advisor specialized in
small-scale pond-based fish farming and aquaculture.

Answer specifically for fish farmers and pond aquaculture.

Do not discuss aquariums unless the user explicitly asks
about aquariums.

Give practical, simple and useful advice.

Consider fish species, fish size, fish biomass, water
temperature, dissolved oxygen, pH, ammonia, feed quantity,
feeding frequency, pond conditions and fish health when
relevant.

If important information is missing, say what information
is needed instead of inventing exact values.

Keep answers clear and concise.

You can answer in English or Telugu depending on the
language used by the farmer.
"""


    payload = {

        "model": "meenamitra",

        "messages": [

            {
                "role": "system",
                "content": system_prompt
            },

            {
                "role": "user",
                "content": question
            }

        ],

        "temperature": 0.7,

        "max_tokens": 300
    }


    # ======================================================
    # CALL AWS MODEL
    # ======================================================

    try:

        async with httpx.AsyncClient(

            timeout=httpx.Timeout(
                connect=10.0,
                read=180.0,
                write=30.0,
                pool=30.0
            )

        ) as client:

            response = await client.post(

                f"{MODEL_URL.rstrip('/')}"
                "/v1/chat/completions",

                json=payload

            )


            response.raise_for_status()


            result = response.json()


            answer = (
                result["choices"][0]["message"]["content"]
                .strip()
            )


    except httpx.ConnectError:

        raise HTTPException(

            status_code=503,

            detail=(
                "MeenaMitra model server is unreachable. "
                "Please make sure the AWS model server is running."
            )
        )


    except httpx.TimeoutException:

        raise HTTPException(

            status_code=504,

            detail=(
                "MeenaMitra model took too long to respond."
            )
        )


    except Exception as e:

        print(
            "MODEL ERROR:",
            repr(e)
        )


        raise HTTPException(

            status_code=500,

            detail=(
                "MeenaMitra model failed "
                "to generate a response."
            )
        )


    # ======================================================
    # SAVE CHAT HISTORY
    # ======================================================

    try:

        supabase.table(
            "chat_history"
        ).insert({

            "user_id": user.id,

            "question": question,

            "answer": answer

        }).execute()


    except Exception as e:

        print(
            "HISTORY SAVE ERROR:",
            repr(e)
        )


    # ======================================================
    # RETURN
    # ======================================================

    return {

        "question": question,

        "answer": answer

    }


# ==========================================================
# CHAT HISTORY
# ==========================================================

@app.get("/history")
def history(
    authorization: str = Header(default="")
):

    user = get_current_user(
        authorization
    )


    try:

        result = (

            supabase
            .table("chat_history")
            .select(
                "id, question, answer, created_at"
            )
            .eq(
                "user_id",
                user.id
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()

        )


        return {

            "history":
                result.data or []

        }


    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)

        )