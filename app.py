import os
import json

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from dotenv import load_dotenv
from sqlalchemy.engine import URL

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from authlib.integrations.flask_client import OAuth
from google import genai

from database.db import db

from models.user import User
from models.interview import Interview


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)


# =========================================================
# SECRET KEY
# =========================================================

app.secret_key = os.getenv(
    "SECRET_KEY",
    "dev-secret-key"
)


# =========================================================
# GEMINI CONFIGURATION
# =========================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

# Your Gemini model
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


if not GEMINI_API_KEY:

    print(
        "WARNING: GEMINI_API_KEY is not configured."
    )


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = None

if GEMINI_API_KEY:

    try:

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print(
            "Gemini client initialized successfully."
        )

        print(
            "Gemini model:",
            GEMINI_MODEL
        )

    except Exception as e:

        print(
            "Gemini client initialization failed:",
            e
        )

        gemini_client = None


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

database_url = URL.create(

    drivername="mysql+pymysql",

    username=os.getenv(
        "DB_USER"
    ),

    password=os.getenv(
        "DB_PASSWORD"
    ),

    host=os.getenv(
        "DB_HOST"
    ),

    port=int(
        os.getenv(
            "DB_PORT",
            "3306"
        )
    ),

    database=os.getenv(
        "DB_NAME"
    )
)


app.config[
    "SQLALCHEMY_DATABASE_URI"
] = database_url


app.config[
    "SQLALCHEMY_TRACK_MODIFICATIONS"
] = False


db.init_app(app)


# =========================================================
# GOOGLE OAUTH CONFIGURATION
# =========================================================

oauth = OAuth(app)


google = oauth.register(

    name="google",

    client_id=os.getenv(
        "GOOGLE_CLIENT_ID"
    ),

    client_secret=os.getenv(
        "GOOGLE_CLIENT_SECRET"
    ),

    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),

    client_kwargs={
        "scope": "openid email profile"
    }
)


# =========================================================
# GEMINI ERROR HANDLER
# =========================================================

def get_gemini_error_message(error):

    error_text = str(error)

    print(
        "\n========================================"
    )

    print(
        "GEMINI API ERROR"
    )

    print(
        error_text
    )

    print(
        "========================================\n"
    )


    # -----------------------------------------------------
    # QUOTA / RATE LIMIT
    # -----------------------------------------------------

    if (
        "429" in error_text
        or "RESOURCE_EXHAUSTED" in error_text
        or "QuotaFailure" in error_text
        or "quota" in error_text.lower()
    ):

        return (
            "Gemini API quota has been exceeded."
        )


    # -----------------------------------------------------
    # API KEY / AUTHENTICATION
    # -----------------------------------------------------

    if (
        "401" in error_text
        or "403" in error_text
        or "API key" in error_text
        or "PERMISSION_DENIED" in error_text
    ):

        return (
            "Gemini API authentication failed."
        )


    # -----------------------------------------------------
    # MODEL ERROR
    # -----------------------------------------------------

    if (
        "model" in error_text.lower()
        and (
            "not found" in error_text.lower()
            or "NOT_FOUND" in error_text
        )
    ):

        return (
            "The configured Gemini model is unavailable."
        )


    # -----------------------------------------------------
    # GENERAL ERROR
    # -----------------------------------------------------

    return (
        "Unable to connect to Gemini AI."
    )


# =========================================================
# FALLBACK INTERVIEW QUESTIONS
# =========================================================

def get_fallback_questions(role):

    role_lower = role.lower()


    # -----------------------------------------------------
    # PYTHON
    # -----------------------------------------------------

    if "python" in role_lower:

        return [

            "What is the difference between a list and a tuple in Python?",

            "Explain the concept of functions in Python with an example.",

            "What is exception handling in Python?",

            "What is the difference between a class and an object in Python?",

            "How would you optimize a Python program that is running slowly?"

        ]


    # -----------------------------------------------------
    # JAVA
    # -----------------------------------------------------

    if "java" in role_lower:

        return [

            "What are the main features of Java?",

            "What is the difference between JDK, JRE, and JVM?",

            "Explain the four main principles of Object-Oriented Programming.",

            "What is the difference between method overloading and method overriding?",

            "How does exception handling work in Java?"

        ]


    # -----------------------------------------------------
    # WEB DEVELOPMENT
    # -----------------------------------------------------

    if (
        "web" in role_lower
        or "frontend" in role_lower
        or "front-end" in role_lower
        or "full stack" in role_lower
        or "fullstack" in role_lower
    ):

        return [

            "What is HTML and why is it used in web development?",

            "What is the difference between class and id in CSS?",

            "Explain the CSS box model.",

            "What is the purpose of JavaScript in a web application?",

            "How does a frontend application communicate with a backend server?"

        ]


    # -----------------------------------------------------
    # REACT
    # -----------------------------------------------------

    if "react" in role_lower:

        return [

            "What is React and why is it used?",

            "What is a component in React?",

            "What is the difference between props and state?",

            "What are React Hooks? Explain the useState Hook.",

            "How would you improve the performance of a React application?"

        ]


    # -----------------------------------------------------
    # DATABASE / SQL / DBMS
    # -----------------------------------------------------

    if (
        "database" in role_lower
        or "sql" in role_lower
        or "dbms" in role_lower
    ):

        return [

            "What is a database and why is it used?",

            "What is the difference between primary key and foreign key?",

            "Explain the difference between DELETE, DROP, and TRUNCATE.",

            "What is normalization in DBMS?",

            "What is the difference between INNER JOIN and LEFT JOIN?"

        ]


    # -----------------------------------------------------
    # GENERAL SOFTWARE ROLE
    # -----------------------------------------------------

    return [

        f"What interests you about working as a {role}?",

        "Explain one technical project that you have worked on.",

        "What is the difference between a frontend and a backend application?",

        "How do you debug an error in a software application?",

        "Describe a technical problem you faced and how you solved it."

    ]


# =========================================================
# FALLBACK INTERVIEW EVALUATION
# =========================================================

def generate_fallback_evaluation(
    role,
    answers
):

    results = []


    # -----------------------------------------------------
    # EVALUATE EACH ANSWER
    # -----------------------------------------------------

    for i, item in enumerate(
        answers,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue


        question = str(
            item.get(
                "question",
                ""
            )
        ).strip()


        answer = str(
            item.get(
                "answer",
                ""
            )
        ).strip()


        answer_lower = answer.lower()

        answer_length = len(
            answer.split()
        )


        # -------------------------------------------------
        # I DON'T KNOW
        # -------------------------------------------------

        if answer_lower in [

            "i don't know",
            "i dont know",
            "don't know",
            "dont know",
            "no idea",
            "i have no idea"

        ]:

            technical = 0
            relevance = 0
            clarity = 2
            completeness = 0
            overall = 0

            feedback = (
                "The candidate honestly stated that they do not "
                "know the answer. The response does not demonstrate "
                "technical understanding of the question."
            )


        # -------------------------------------------------
        # EMPTY ANSWER
        # -------------------------------------------------

        elif not answer:

            technical = 0
            relevance = 0
            clarity = 0
            completeness = 0
            overall = 0

            feedback = (
                "No answer was provided. Try to answer the "
                "question with a clear explanation."
            )


        # -------------------------------------------------
        # VERY SHORT ANSWER
        # -------------------------------------------------

        elif answer_length < 5:

            technical = 3
            relevance = 3
            clarity = 4
            completeness = 2
            overall = 3

            feedback = (
                "The answer is too short. Provide more technical "
                "details and explain your reasoning."
            )


        # -------------------------------------------------
        # SHORT ANSWER
        # -------------------------------------------------

        elif answer_length < 15:

            technical = 5
            relevance = 5
            clarity = 5
            completeness = 4
            overall = 5

            feedback = (
                "The answer is relevant but could be improved "
                "with more explanation and a practical example."
            )


        # -------------------------------------------------
        # GOOD ANSWER
        # -------------------------------------------------

        elif answer_length < 35:

            technical = 7
            relevance = 7
            clarity = 7
            completeness = 6
            overall = 7

            feedback = (
                "Good answer. You provided a reasonable explanation. "
                "Adding a specific technical example would make it stronger."
            )


        # -------------------------------------------------
        # DETAILED ANSWER
        # -------------------------------------------------

        else:

            technical = 8
            relevance = 8
            clarity = 8
            completeness = 8
            overall = 8

            feedback = (
                "Good detailed answer. Your explanation is reasonably "
                "complete. Try to keep the response structured and concise."
            )


        results.append({

            "question_number": i,

            "technical": technical,

            "relevance": relevance,

            "clarity": clarity,

            "completeness": completeness,

            "overall": overall,

            "feedback": feedback

        })


    # -----------------------------------------------------
    # NO VALID RESULTS
    # -----------------------------------------------------

    if not results:

        return {

            "results": [],

            "final_score": 0,

            "percentage": 0,

            "strengths": [
                "Interview was submitted."
            ],

            "weaknesses": [
                "No valid answers were provided."
            ],

            "improvement_suggestions": [
                "Provide complete answers to all interview questions."
            ]

        }


    # -----------------------------------------------------
    # FINAL SCORE
    # -----------------------------------------------------

    total_score = sum(
        result["overall"]
        for result in results
    )


    final_score = round(
        total_score / len(results),
        1
    )


    percentage = round(
        final_score * 10,
        1
    )


    # -----------------------------------------------------
    # STRENGTHS
    # -----------------------------------------------------

    strengths = [

        "You attempted the interview questions.",

        "Your answers can be improved further with more technical examples."

    ]


    # -----------------------------------------------------
    # WEAKNESSES
    # -----------------------------------------------------

    weaknesses = [

        "Some answers may require more technical depth.",

        "Answers should include practical examples where possible."

    ]


    # -----------------------------------------------------
    # IMPROVEMENT SUGGESTIONS
    # -----------------------------------------------------

    improvement_suggestions = [

        "Explain technical concepts step by step.",

        "Use practical examples from your projects.",

        "Keep your answers clear, structured, and relevant."

    ]


    return {

        "results": results,

        "final_score": final_score,

        "percentage": percentage,

        "strengths": strengths,

        "weaknesses": weaknesses,

        "improvement_suggestions":
            improvement_suggestions

    }


# =========================================================
# SAVE INTERVIEW HISTORY
# =========================================================

def save_interview_history(
    role,
    evaluation
):

    user_id = session.get(
        "user_id"
    )


    # -----------------------------------------------------
    # USER NOT LOGGED IN
    # -----------------------------------------------------

    if not user_id:

        print(
            "INFO: Interview result was not saved "
            "because the user is not logged in."
        )

        return False


    try:

        final_score = float(
            evaluation.get(
                "final_score",
                0
            )
        )


        percentage = float(
            evaluation.get(
                "percentage",
                final_score * 10
            )
        )


        strengths = evaluation.get(
            "strengths",
            []
        )


        weaknesses = evaluation.get(
            "weaknesses",
            []
        )


        improvement_suggestions = evaluation.get(
            "improvement_suggestions",
            []
        )


        # -------------------------------------------------
        # CONVERT LISTS TO JSON
        # -------------------------------------------------

        strengths_json = json.dumps(
            strengths,
            ensure_ascii=False
        )


        weaknesses_json = json.dumps(
            weaknesses,
            ensure_ascii=False
        )


        suggestions_json = json.dumps(
            improvement_suggestions,
            ensure_ascii=False
        )


        # -------------------------------------------------
        # CREATE RECORD
        # -------------------------------------------------

        interview_record = Interview(

            user_id=user_id,

            role=role,

            final_score=final_score,

            percentage=percentage,

            strengths=strengths_json,

            weaknesses=weaknesses_json,

            improvement_suggestions=suggestions_json

        )


        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

        db.session.add(
            interview_record
        )

        db.session.commit()


        print(
            "SUCCESS: Interview history saved to database."
        )


        return True


    except Exception as e:

        db.session.rollback()


        print(
            "\n========================================"
        )

        print(
            "INTERVIEW HISTORY SAVE ERROR:"
        )

        print(
            e
        )

        print(
            "========================================\n"
        )


        return False


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# INTERVIEW PAGE
# =========================================================

@app.route("/interview")
def interview():

    return render_template(
        "interview.html"
    )


# =========================================================
# GENERATE INTERVIEW QUESTIONS
# =========================================================

@app.route(
    "/generate-question",
    methods=["POST"]
)
def generate_question():

    data = request.get_json(
        silent=True
    ) or {}


    role = data.get(
        "role"
    )


    # -----------------------------------------------------
    # VALIDATE ROLE
    # -----------------------------------------------------

    if not role:

        return {

            "success": False,

            "error": "Please select a job role."

        }


    role = str(
        role
    ).strip()


    if not role:

        return {

            "success": False,

            "error": "Please select a valid job role."

        }


    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are an expert technical interviewer.

Create exactly 5 interview questions for a student
applying for the role of {role}.

Requirements:

1. Questions must be dynamically generated.
2. Do NOT use a fixed question list.
3. Start with basic questions.
4. Gradually increase the difficulty.
5. Cover different technical topics.
6. Questions should be suitable for a student.
7. Questions should test practical understanding.
8. Do not provide answers.
9. Do not repeat questions.
10. Return exactly 5 questions.

Return ONLY valid JSON in this format:

{{
    "questions": [
        "Question 1",
        "Question 2",
        "Question 3",
        "Question 4",
        "Question 5"
    ]
}}
"""


    # -----------------------------------------------------
    # TRY GEMINI
    # -----------------------------------------------------

    try:

        if gemini_client is None:

            raise RuntimeError(
                "Gemini client is not configured."
            )


        response = gemini_client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config={
                "response_mime_type": "application/json"
            }

        )


        if not response or not response.text:

            raise ValueError(
                "Gemini returned an empty response."
            )


        result = json.loads(
            response.text
        )


        questions = result.get(
            "questions",
            []
        )


        if not isinstance(
            questions,
            list
        ):

            raise ValueError(
                "Invalid question format returned by Gemini."
            )


        questions = [

            str(question).strip()

            for question in questions

            if str(question).strip()

        ]


        if len(questions) != 5:

            raise ValueError(
                "Gemini did not generate exactly 5 questions."
            )


        print(
            "SUCCESS: Questions generated using Gemini AI."
        )


        return {

            "success": True,

            "questions": questions

        }


    except Exception as e:

        error_message = get_gemini_error_message(
            e
        )


        print(
            "\nGemini question generation failed."
        )

        print(
            "Reason:",
            error_message
        )

        print(
            "Activating automatic fallback questions..."
        )


        fallback_questions = get_fallback_questions(
            role
        )


        return {

            "success": True,

            "questions": fallback_questions,

            "fallback": True,

            "message":
                "Gemini is temporarily unavailable. "
                "Fallback interview questions are being used."

        }


# =========================================================
# EVALUATE INTERVIEW
# =========================================================

@app.route(
    "/evaluate-interview",
    methods=["POST"]
)
def evaluate_interview():

    data = request.get_json(
        silent=True
    ) or {}


    role = data.get(
        "role"
    )


    answers = data.get(
        "answers",
        []
    )


    # -----------------------------------------------------
    # VALIDATE ROLE
    # -----------------------------------------------------

    if not role:

        return {

            "success": False,

            "error": "Role is required."

        }


    role = str(
        role
    ).strip()


    # -----------------------------------------------------
    # VALIDATE ANSWERS
    # -----------------------------------------------------

    if not answers:

        return {

            "success": False,

            "error": "Interview answers are required."

        }


    if not isinstance(
        answers,
        list
    ):

        return {

            "success": False,

            "error": "Invalid answers format."

        }


    # -----------------------------------------------------
    # CREATE INTERVIEW TEXT
    # -----------------------------------------------------

    interview_text = ""


    for i, item in enumerate(
        answers,
        start=1
    ):

        if not isinstance(
            item,
            dict
        ):

            continue


        question = str(
            item.get(
                "question",
                ""
            )
        ).strip()


        answer = str(
            item.get(
                "answer",
                ""
            )
        ).strip()


        interview_text += f"""

Question {i}:
{question}

Candidate Answer {i}:
{answer}

"""


    if not interview_text.strip():

        return {

            "success": False,

            "error":
                "No valid interview answers were provided."

        }


    # =====================================================
    # AI EVALUATION PROMPT
    # =====================================================

    prompt = f"""
You are an expert technical interviewer.

Evaluate the complete interview of a candidate
applying for the role of {role}.

The candidate answered the following questions:

{interview_text}

Evaluate EACH answer carefully.

For every question provide:

1. Technical Knowledge score out of 10
2. Relevance score out of 10
3. Clarity score out of 10
4. Completeness score out of 10
5. Overall score out of 10
6. Short constructive feedback

Then provide an overall interview analysis:

- final_score out of 10
- percentage out of 100
- strengths
- weaknesses
- improvement suggestions

Important:

- Evaluate the actual candidate answer.
- Do not give a high score just because an answer exists.
- If the candidate says "I don't know", evaluate it honestly.
- Keep feedback constructive.
- Scores must be numbers.
- Scores must be between 0 and 10.
- Percentage must be between 0 and 100.
- Do not invent candidate information.
- Return exactly one result for each question.

Return ONLY valid JSON in this structure:

{{
    "results": [
        {{
            "question_number": 1,
            "technical": 0,
            "relevance": 0,
            "clarity": 0,
            "completeness": 0,
            "overall": 0,
            "feedback": "feedback"
        }}
    ],

    "final_score": 0,

    "percentage": 0,

    "strengths": [
        "strength 1",
        "strength 2"
    ],

    "weaknesses": [
        "weakness 1",
        "weakness 2"
    ],

    "improvement_suggestions": [
        "suggestion 1",
        "suggestion 2"
    ]
}}
"""


    # =====================================================
    # TRY GEMINI EVALUATION
    # =====================================================

    try:

        if gemini_client is None:

            raise RuntimeError(
                "Gemini client is not configured."
            )


        response = gemini_client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config={
                "response_mime_type": "application/json"
            }

        )


        if not response or not response.text:

            raise ValueError(
                "Gemini returned an empty evaluation."
            )


        result = json.loads(
            response.text
        )


        if not isinstance(
            result,
            dict
        ):

            raise ValueError(
                "Invalid evaluation format returned by Gemini."
            )


        if "results" not in result:

            raise ValueError(
                "Evaluation results are missing."
            )


        if not isinstance(
            result["results"],
            list
        ):

            raise ValueError(
                "Invalid evaluation results format."
            )


        # -------------------------------------------------
        # SAVE HISTORY
        # -------------------------------------------------

        history_saved = save_interview_history(
            role,
            result
        )


        print(
            "SUCCESS: Interview evaluated using Gemini AI."
        )


        return {

            "success": True,

            "evaluation": result,

            "history_saved": history_saved

        }


    except Exception as e:

        error_message = get_gemini_error_message(
            e
        )


        print(
            "\nGemini evaluation failed."
        )

        print(
            "Reason:",
            error_message
        )

        print(
            "Activating automatic fallback evaluation..."
        )


        # -------------------------------------------------
        # FALLBACK
        # -------------------------------------------------

        fallback_evaluation = generate_fallback_evaluation(

            role,

            answers

        )


        # -------------------------------------------------
        # SAVE FALLBACK
        # -------------------------------------------------

        history_saved = save_interview_history(

            role,

            fallback_evaluation

        )


        return {

            "success": True,

            "evaluation": fallback_evaluation,

            "fallback": True,

            "history_saved": history_saved,

            "message":
                "Gemini is temporarily unavailable. "
                "A fallback evaluation has been generated."

        }


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return redirect(
            url_for("login")
        )


    interviews = Interview.query.filter_by(

        user_id=user_id

    ).order_by(

        Interview.created_at.desc()

    ).all()


    history_data = []


    for interview_record in interviews:

        # ---------------------------------------------
        # STRENGTHS
        # ---------------------------------------------

        try:

            strengths = json.loads(
                interview_record.strengths
            ) if interview_record.strengths else []

        except Exception:

            strengths = []


        # ---------------------------------------------
        # WEAKNESSES
        # ---------------------------------------------

        try:

            weaknesses = json.loads(
                interview_record.weaknesses
            ) if interview_record.weaknesses else []

        except Exception:

            weaknesses = []


        # ---------------------------------------------
        # SUGGESTIONS
        # ---------------------------------------------

        try:

            improvement_suggestions = json.loads(
                interview_record.improvement_suggestions
            ) if interview_record.improvement_suggestions else []

        except Exception:

            improvement_suggestions = []


        history_data.append({

            "id":
                interview_record.id,

            "role":
                interview_record.role,

            "final_score":
                interview_record.final_score,

            "percentage":
                interview_record.percentage,

            "strengths":
                strengths,

            "weaknesses":
                weaknesses,

            "improvement_suggestions":
                improvement_suggestions,

            "created_at":
                interview_record.created_at

        })


    return render_template(

        "history.html",

        interviews=history_data

    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return redirect(
            url_for("login")
        )


    interviews = Interview.query.filter_by(

        user_id=user_id

    ).order_by(

        Interview.created_at.desc()

    ).all()


    # -----------------------------------------------------
    # STATISTICS
    # -----------------------------------------------------

    total_interviews = len(
        interviews
    )


    if total_interviews > 0:

        scores = [

            float(
                interview.final_score or 0
            )

            for interview in interviews

        ]


        percentages = [

            float(
                interview.percentage or 0
            )

            for interview in interviews

        ]


        average_score = round(

            sum(scores) / total_interviews,

            1

        )


        best_score = round(

            max(scores),

            1

        )


        average_percentage = round(

            sum(percentages) / total_interviews,

            1

        )


    else:

        average_score = 0

        best_score = 0

        average_percentage = 0


    # -----------------------------------------------------
    # RECENT INTERVIEWS
    # -----------------------------------------------------

    recent_interviews = interviews[:5]


    # -----------------------------------------------------
    # CHART DATA
    # -----------------------------------------------------

    chart_labels = []

    chart_scores = []


    for interview in reversed(
        interviews[:10]
    ):

        if interview.created_at:

            chart_labels.append(

                interview.created_at.strftime(
                    "%d %b"
                )

            )

        else:

            chart_labels.append(
                "Interview"
            )


        chart_scores.append(

            float(
                interview.final_score or 0
            )

        )


    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------

    return render_template(

        "dashboard.html",

        total_interviews=total_interviews,

        average_score=average_score,

        best_score=best_score,

        average_percentage=average_percentage,

        recent_interviews=recent_interviews,

        chart_labels=json.dumps(
            chart_labels
        ),

        chart_scores=json.dumps(
            chart_scores
        )

    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    user_id = session.get(
        "user_id"
    )


    # -----------------------------------------------------
    # LOGIN CHECK
    # -----------------------------------------------------

    if not user_id:

        return redirect(
            url_for("login")
        )


    # -----------------------------------------------------
    # GET USER
    # -----------------------------------------------------

    user = User.query.get(
        user_id
    )


    if not user:

        session.clear()

        return redirect(
            url_for("login")
        )


    # -----------------------------------------------------
    # RENDER PROFILE
    # -----------------------------------------------------

    return render_template(

        "profile.html",

        user=user

    )


# =========================================================
# EDIT PROFILE
# =========================================================

@app.route(
    "/edit-profile",
    methods=["GET", "POST"]
)
def edit_profile():

    user_id = session.get(
        "user_id"
    )


    # -----------------------------------------------------
    # LOGIN CHECK
    # -----------------------------------------------------

    if not user_id:

        return redirect(
            url_for("login")
        )


    # -----------------------------------------------------
    # GET USER
    # -----------------------------------------------------

    user = User.query.get(
        user_id
    )


    if not user:

        session.clear()

        return redirect(
            url_for("login")
        )


    # =====================================================
    # UPDATE PROFILE
    # =====================================================

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()


        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        # -------------------------------------------------
        # VALIDATE
        # -------------------------------------------------

        if not name or not email:

            return render_template(

                "edit_profile.html",

                user=user,

                error="Name and email are required."

            )


        # -------------------------------------------------
        # CHECK DUPLICATE EMAIL
        # -------------------------------------------------

        existing_user = User.query.filter(

            User.email == email,

            User.id != user.id

        ).first()


        if existing_user:

            return render_template(

                "edit_profile.html",

                user=user,

                error="This email is already registered."

            )


        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------

        user.name = name

        user.email = email


        try:

            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print(
                "PROFILE UPDATE ERROR:",
                e
            )

            return render_template(

                "edit_profile.html",

                user=user,

                error="Unable to update profile."

            )


        # -------------------------------------------------
        # UPDATE SESSION
        # -------------------------------------------------

        session["user_name"] = user.name

        session["user_email"] = user.email


        # -------------------------------------------------
        # REDIRECT PROFILE
        # -------------------------------------------------

        return redirect(
            url_for("profile")
        )


    # =====================================================
    # GET EDIT PAGE
    # =====================================================

    return render_template(

        "edit_profile.html",

        user=user

    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()


        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        password = request.form.get(
            "password",
            ""
        )


        # -------------------------------------------------
        # VALIDATE
        # -------------------------------------------------

        if not name or not email or not password:

            return render_template(

                "register.html",

                error="Please fill all fields."

            )


        # -------------------------------------------------
        # CHECK EXISTING USER
        # -------------------------------------------------

        existing_user = User.query.filter_by(

            email=email

        ).first()


        if existing_user:

            return render_template(

                "register.html",

                error="Email already registered."

            )


        # -------------------------------------------------
        # HASH PASSWORD
        # -------------------------------------------------

        hashed_password = generate_password_hash(

            password

        )


        # -------------------------------------------------
        # CREATE USER
        # -------------------------------------------------

        user = User(

            name=name,

            email=email,

            password=hashed_password

        )


        db.session.add(
            user
        )


        db.session.commit()


        # -------------------------------------------------
        # LOGIN PAGE
        # -------------------------------------------------

        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        password = request.form.get(
            "password",
            ""
        )


        # -------------------------------------------------
        # FIND USER
        # -------------------------------------------------

        user = User.query.filter_by(

            email=email

        ).first()


        # -------------------------------------------------
        # USER NOT FOUND
        # -------------------------------------------------

        if not user:

            return render_template(

                "login.html",

                error="Email or password is incorrect."

            )


        # -------------------------------------------------
        # GOOGLE ACCOUNT
        # -------------------------------------------------

        if not user.password:

            return render_template(

                "login.html",

                error=
                    "Please use Google Login for this account."

            )


        # -------------------------------------------------
        # CHECK PASSWORD
        # -------------------------------------------------

        if not check_password_hash(

            user.password,

            password

        ):

            return render_template(

                "login.html",

                error="Email or password is incorrect."

            )


        # -------------------------------------------------
        # SESSION
        # -------------------------------------------------

        session["user_id"] = user.id

        session["user_name"] = user.name

        session["user_email"] = user.email


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return redirect(
            url_for("home")
        )


    return render_template(
        "login.html"
    )


# =========================================================
# GOOGLE LOGIN
# =========================================================

@app.route("/auth/google")
def google_login():

    redirect_uri = url_for(

        "google_callback",

        _external=True

    )


    return google.authorize_redirect(

        redirect_uri

    )


# =========================================================
# GOOGLE CALLBACK
# =========================================================

@app.route(
    "/auth/google/callback"
)
def google_callback():

    try:

        # -------------------------------------------------
        # ACCESS TOKEN
        # -------------------------------------------------

        token = google.authorize_access_token()


        # -------------------------------------------------
        # USER INFORMATION
        # -------------------------------------------------

        user_info = token.get(
            "userinfo"
        )


        if not user_info:

            return (
                "Google login failed."
            )


        name = user_info.get(
            "name",
            "Google User"
        )


        email = user_info.get(
            "email"
        )


        if not email:

            return (
                "Google account email not available."
            )


        email = email.strip().lower()


        # -------------------------------------------------
        # FIND USER
        # -------------------------------------------------

        user = User.query.filter_by(

            email=email

        ).first()


        # -------------------------------------------------
        # CREATE USER
        # -------------------------------------------------

        if not user:

            user = User(

                name=name,

                email=email,

                password=None

            )


            db.session.add(
                user
            )

            db.session.commit()


        # -------------------------------------------------
        # SESSION
        # -------------------------------------------------

        session["user_id"] = user.id

        session["user_name"] = user.name

        session["user_email"] = user.email


        # -------------------------------------------------
        # HOME
        # -------------------------------------------------

        return redirect(
            url_for("home")
        )


    except Exception as e:

        print(
            "\n========================================"
        )

        print(
            "GOOGLE OAUTH ERROR:"
        )

        print(
            e
        )

        print(
            "========================================\n"
        )


        return (

            "Google login failed. "

            "Check terminal for error."

        )


# =========================================================
# FACEBOOK LOGIN
# =========================================================

@app.route("/auth/facebook")
def facebook_login():

    return redirect(
        url_for("login")
    )


# =========================================================
# GITHUB LOGIN
# =========================================================

@app.route("/auth/github")
def github_login():

    return redirect(
        url_for("login")
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()


    print(
        "\n========================================"
    )

    print(
        "AI INTERVIEW EVALUATOR"
    )

    print(
        "========================================"
    )

    print(
        "Gemini Model:",
        GEMINI_MODEL
    )

    print(
        "Server: http://127.0.0.1:5000"
    )

    print(
        "========================================\n"
    )


    app.run(
        debug=True
    )