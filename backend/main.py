from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
import os
import httpx


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

MODEL_URL = os.getenv(
    "MEENAMITRA_MODEL_URL",
    "http://127.0.0.1:8000"
).rstrip("/")


if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY "
        "must be set in backend/.env"
    )


# ============================================================
# SUPABASE CLIENT
# ============================================================

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="MeenaMitra API",
    description="Backend API for the MeenaMitra aquaculture AI advisor",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://meenamitra.vercel.app",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    question: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "MeenaMitra API is running",
        "status": "online"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "MeenaMitra Backend",
        "model_url": MODEL_URL
    }


# ============================================================
# SIGNUP
# ============================================================

@app.post("/signup")
def signup(request: SignupRequest):

    try:

        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })

        user = response.user
        session = response.session

        return {
            "message": "Signup successful",

            "user_id": (
                user.id
                if user
                else None
            ),

            "email": (
                user.email
                if user
                else request.email
            ),

            "access_token": (
                session.access_token
                if session
                else None
            ),

            "refresh_token": (
                session.refresh_token
                if session
                else None
            ),

            "email_confirmation_required": (
                session is None
            )
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(request: LoginRequest):

    try:

        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if not response.session:

            raise HTTPException(
                status_code=401,
                detail="Login failed"
            )

        return {

            "message": "Login successful",

            "user_id": response.user.id,

            "email": response.user.email,

            "access_token": (
                response.session.access_token
            ),

            "refresh_token": (
                response.session.refresh_token
            )
        }

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


# ============================================================
# GET CURRENT USER
# ============================================================

def get_current_user(access_token: str):

    if not access_token:

        raise HTTPException(
            status_code=401,
            detail="Missing access token"
        )

    try:

        response = supabase.auth.get_user(
            access_token
        )

        if not response.user:

            raise HTTPException(
                status_code=401,
                detail="Invalid access token"
            )

        return response.user

    except HTTPException:

        raise

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token"
        )


# ============================================================
# CHAT
# ============================================================

@app.post("/chat")
def chat(
    request: ChatRequest,
    authorization: str = Header(default=None)
):

    # --------------------------------------------------------
    # CHECK AUTHORIZATION
    # --------------------------------------------------------

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )


    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Authorization must use Bearer token"
        )


    access_token = authorization.replace(
        "Bearer ",
        "",
        1
    ).strip()


    # --------------------------------------------------------
    # VALIDATE USER
    # --------------------------------------------------------

    user = get_current_user(
        access_token
    )


    # --------------------------------------------------------
    # VALIDATE QUESTION
    # --------------------------------------------------------

    question = request.question.strip()


    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )


    # ========================================================
    # SEND QUESTION TO MEENAMITRA MODEL ON AWS
    # ========================================================

    try:

        payload = {

            "model": "meenamitra",

            "messages": [

                {
                    "role": "user",
                    "content": question
                }

            ],

            "temperature": 0.7,

            "max_tokens": 300
        }


        with httpx.Client(
            timeout=httpx.Timeout(
                connect=10.0,
                read=180.0,
                write=30.0,
                pool=30.0
            )
        ) as client:

            response = client.post(
                f"{MODEL_URL}/v1/chat/completions",
                json=payload
            )


        # ----------------------------------------------------
        # CHECK AWS RESPONSE
        # ----------------------------------------------------

        response.raise_for_status()

        result = response.json()


        # ----------------------------------------------------
        # EXTRACT MODEL ANSWER
        # ----------------------------------------------------

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
            TypeError,
            AttributeError
        ):

            raise HTTPException(
                status_code=502,
                detail="Invalid response received from MeenaMitra model"
            )


        if not answer:

            raise HTTPException(
                status_code=502,
                detail="MeenaMitra model returned an empty response"
            )


    # --------------------------------------------------------
    # AWS CONNECTION ERROR
    # --------------------------------------------------------

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
                "MeenaMitra model took too long to respond. "
                "Please try again."
            )
        )


    except httpx.HTTPStatusError as e:

        raise HTTPException(
            status_code=502,
            detail=(
                "MeenaMitra model server returned an error: "
                f"{e.response.status_code}"
            )
        )


    # ========================================================
    # SAVE CHAT HISTORY TO SUPABASE
    # ========================================================

    try:

        supabase.table(
            "chat_history"
        ).insert({

            "user_id": user.id,

            "question": question,

            "answer": answer

        }).execute()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not save chat history: {str(e)}"
            )
        )


    # ========================================================
    # RETURN FINAL RESPONSE
    # ========================================================

    return {

        "user_id": user.id,

        "question": question,

        "answer": answer
    }


# ============================================================
# CHAT HISTORY
# ============================================================

@app.get("/history")
def history(
    authorization: str = Header(default=None)
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )


    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Authorization must use Bearer token"
        )


    access_token = authorization.replace(
        "Bearer ",
        "",
        1
    ).strip()


    user = get_current_user(
        access_token
    )


    try:

        response = (
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

            "user_id": user.id,

            "conversations": response.data

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load chat history: {str(e)}"
            )
        )