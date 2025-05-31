from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, Form
from typing import Annotated
from fastapi.middleware.cors import CORSMiddleware
from app.db import create_db_and_tables, User
from app.schemas import UserCreate, UserRead, UserUpdate
from app.users import auth_backend, current_user, fastapi_users

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2_fragments.fastapi import Jinja2Blocks
import jinja_partials # type: ignore
import httpx
from datastar_py.fastapi import DatastarStreamingResponse
from datastar_py.sse import ServerSentEventGenerator as SSE

import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Not needed if you setup a migration system like Alembic
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Allow all origins (for development only)
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] for all origins (not recommended in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Blocks(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
jinja_partials.register_starlette_extensions(templates)


rendered_html_str:str = ""

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.jinja2",
        {"request": request}
    )



@app.post("/logout")
async def logout(request: Request):
    url = "http://localhost:8000/auth/jwt/logout"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data:dict = {}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
    print("Status Code:", response.status_code)
    print("Response:", response.json())
    if response.status_code == 201:
        return templates.TemplateResponse(
                "snippets.jinja2",
                {"request": request},
                status_code=201,
                block_name="signupsuccess"
        )
    return "Unknown return Code!!"

def is_fragment(request: Request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"

@app.get("/login_form", response_class=HTMLResponse)
async def login(request: Request):
    if is_fragment(request):
        return templates.TemplateResponse("login.jinja2", {"request": request}, block_name="content")
    return templates.TemplateResponse("login.jinja2", {"request": request})

@app.post("/login_validate")
async def login_validate(request: Request, email: Annotated[str, Form()], password: Annotated[str, Form()]):
    print('username:' + email)
    print('password:' + password)

    BASE_URL:str = "http://localhost:8000"
    LOGIN_URL = f"{BASE_URL}/auth/jwt/login"
    print('LOGIN_URL:' + LOGIN_URL)

    login_data = {
    "grant_type": "password",
    "username": email,
    "password": password,
    "scope": "",
    "client_id": "",
    "client_secret": ""
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            LOGIN_URL,
            data=login_data,
            headers={
                "accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

    if response.status_code == 200 or response.status_code == 204:
        print(str(response.cookies.get('auth')))
        cookie_value = response.cookies.get('auth', '')
        templ = templates.get_template("snippets.jinja2")
        rendered_html_str = "".join(templ.blocks["loginsuccess"](templ.new_context({"request": request})))
        async def _():
            yield SSE.merge_fragments(fragments=rendered_html_str, use_view_transition=True)
            time.sleep(4)
            yield SSE.redirect("/authenticated-route")

        streaming_response = DatastarStreamingResponse(_())
        streaming_response.headers['Set-Cookie'] = f"auth={cookie_value}; HttpOnly; Secure; Path=/"
        return streaming_response

    elif response.status_code == 400:
        templ = templates.get_template("snippets.jinja2")
        rendered_html_str = "".join(templ.blocks["signupfailed"](templ.new_context({"request": request, "id":"loginerrordiv", "signuperrormessage": 'Invalid credentials', "errortitle": 'Login failed'})))
        async def _():
            yield SSE.merge_fragments(fragments=rendered_html_str)
        return DatastarStreamingResponse(_())
    else:
        templ = templates.get_template("snippets.jinja2")
        rendered_html_str = "".join(templ.blocks["signupfailed"](templ.new_context({"request": request, "id":"loginerrordiv", "signuperrormessage": f"Login failed with status code: {response.status_code}", "errortitle": 'Login failed'})))
        async def _():
            yield SSE.merge_fragments(fragments=rendered_html_str)
        return DatastarStreamingResponse(_())


@app.get("/signup_form")
def signup_form(request: Request):
    if request.headers.get('datastar-request') == 'true':
        templ = templates.get_template("signup.jinja2")
        rendered_html_str = "".join(templ.blocks["content"](templ.new_context({"request": request})))
        async def _():
            yield SSE.merge_fragments(fragments=rendered_html_str, use_view_transition=True)
        return DatastarStreamingResponse(_())
    else:
        return templates.TemplateResponse(
            "signup.jinja2",
            {"request": request}
        )

@app.post("/signup_validate")
async def signup_validate(request: Request, email: Annotated[str, Form()], password: Annotated[str, Form()], passwordrepeat: Annotated[str, Form()]):
    print('email:' + email)
    print('password:' + password)
    print('passwordrepeat:' + passwordrepeat)

    if not password == passwordrepeat:
        templ = templates.get_template("snippets.jinja2")
        rendered_html_str = "".join(templ.blocks["signupfailed"](templ.new_context({"request": request, "id":"signuperrordiv", "signuperrormessage": 'Password Repeat missmatch', "errortitle": 'Sign Up failed'})))
        async def _():
            yield SSE.merge_fragments(fragments=rendered_html_str)
        return DatastarStreamingResponse(_())

    url = "http://localhost:8000/auth/register"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "password": password,
        "is_active": True,
        "is_superuser": False,
        "is_verified": False
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
    print("Status Code:", response.status_code)
    print("Response:", response.json())
    if response.status_code == 201:
        templ = templates.get_template("snippets.jinja2")
        rendered_html_str = "".join(templ.blocks["signupsuccess"](templ.new_context({"request": request})))
        async def _():
            yield SSE.merge_fragments(fragments=rendered_html_str, use_view_transition=True)
        return DatastarStreamingResponse(_())
    elif response.status_code == 400:
        code_value = response.json()["detail"]
        if code_value == 'REGISTER_USER_ALREADY_EXISTS':
            templ = templates.get_template("snippets.jinja2")
            rendered_html_str = "".join(templ.blocks["signupfailed"](templ.new_context({"request": request, "id":"signuperrordiv", "signuperrormessage": 'Email address already in use', "errortitle": 'Sign Up failed'})))
            async def _():
                yield SSE.merge_fragments(fragments=rendered_html_str)
            return DatastarStreamingResponse(_())
        elif code_value == 'REGISTER_INVALID_PASSWORD':
            templ = templates.get_template("snippets.jinja2")
            rendered_html_str = "".join(templ.blocks["signupfailed"](templ.new_context({"request": request, "id":"signuperrordiv", "signuperrormessage": 'Invalid Password', "errortitle": 'Sign Up failed'})))
            async def _():
                yield SSE.merge_fragments(fragments=rendered_html_str)
            return DatastarStreamingResponse(_())
    elif response.status_code == 422:
        templ = templates.get_template("snippets.jinja2")
        rendered_html_str = "".join(templ.blocks["signupfailed"](templ.new_context({"request": request, "id":"signuperrordiv", "signuperrormessage": 'Validation Error', "errortitle": 'Sign Up failed'})))
        async def _():
            yield SSE.merge_fragments(fragments=rendered_html_str)
        return DatastarStreamingResponse(_())
    print("Unknown return Code!!")
    return "Unknown return Code!!"


@app.get("/forgotpassword_form")
async def forgotpassword_form(request: Request):
    if request.headers.get('datastar-request') == 'true':
        return templates.TemplateResponse(
            "forgotpassword.jinja2",
            {"request": request},
            block_name="content"
        )
    else:
        return templates.TemplateResponse(
            "forgotpassword.jinja2",
            {"request": request}
    )

@app.get("/muster_form")
async def muster_form(request: Request):
    if request.headers.get('datastar-request') == 'true':
        return templates.TemplateResponse(
            "muster.jinja2",
            {"request": request},
            block_name="content"
        )
    else:
        return templates.TemplateResponse(
            "muster.jinja2",
            {"request": request}
    )

# USERS
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# /{subpage}
@app.get("/authenticated-route")
async def authenticated_route(request: Request, user: User = Depends(current_user)):
    if user is None:
        return templates.TemplateResponse(
            "unauthanticated.jinja2",
            {"request": request, "user": user}
        )
    else:
        return templates.TemplateResponse(
            "calc01.jinja2",
            {"request": request, "user": user}
        )