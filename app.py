import pymssql
from dotenv import load_dotenv
import os
from groq import Groq
from flask import Flask, render_template, request, redirect, url_for

########################################################################
# LOAD ENV VARIABLES
########################################################################

load_dotenv()

########################################################################
# DATABASE DETAILS
########################################################################

server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
user_name = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

########################################################################
# GROQ API
########################################################################

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

########################################################################
# FLASK APP
########################################################################

app = Flask(__name__)

########################################################################
# CHAT HISTORY
########################################################################

chat_history = []

########################################################################
# HOME ROUTE
########################################################################

@app.route("/", methods=["GET", "POST"])

def home():

    global chat_history

    if request.method == "POST":

        ################################################################
        # RESET BUTTON
        ################################################################

        if "reset" in request.form:

            chat_history.clear()

            return redirect(url_for("home"))

        ################################################################
        # GET USER QUESTION
        ################################################################

        user_question = request.form.get("query")

        if not user_question or user_question.strip() == "":

            return render_template(
                "index.html",
                chat_history=chat_history
            )

        ################################################################
        # AI PROMPT
        ################################################################

        prompt = f"""

        You are a SQL query generator.

        Convert the user's English question into ONLY a SQL Server SELECT query.

        STRICT RULES:

        1. Return ONLY raw SQL query
        2. Do NOT explain anything
        3. Do NOT write notes
        4. Do NOT use markdown
        5. Only SELECT queries allowed
        6. SQL Server syntax only
        7. NEVER generate DELETE, UPDATE, DROP, INSERT, ALTER, TRUNCATE
        8. If using AVG, SUM, COUNT, include GROUP BY properly

        TABLE NAME:
        Daily_Packing_Data

        COLUMNS:

        Serial_Number
        Record_Number
        Machine_No
        Date_of_Packing
        Time_of_Packing
        Location
        Machine
        SKU
        Weight_of_Bag
        OPT_Name
        Time_Stamp

        USER QUESTION:
        {user_question}

        """

        try:

            ############################################################
            # ASK AI
            ############################################################

            response = client.chat.completions.create(

                model="llama-3.1-8b-instant",

                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

            )

            ############################################################
            # GET AI SQL
            ############################################################

            ai_query = response.choices[0].message.content.strip()

            ai_query = ai_query.replace("```sql", "")
            ai_query = ai_query.replace("```", "")
            ai_query = ai_query.strip()

            print("\nAI GENERATED SQL:")
            print(ai_query)

            ############################################################
            # SAFETY CHECK
            ############################################################

            if not ai_query.lower().startswith("select"):

                return "Only SELECT queries are allowed."

            ############################################################
            # CONNECT DATABASE
            ############################################################

            now_connect = pymssql.connect(

                server=server,
                user=user_name,
                password=password,
                database=database

            )

            cursor = now_connect.cursor()

            ############################################################
            # EXECUTE QUERY
            ############################################################

            cursor.execute(ai_query)

            ############################################################
            # FETCH DATA
            ############################################################

            result = cursor.fetchall()

            columns = [column[0] for column in cursor.description]

            ############################################################
            # CLOSE CONNECTION
            ############################################################

            now_connect.close()

            ############################################################
            # SAVE CHAT HISTORY
            ############################################################

            chat_history.append({

                "question": user_question,

                "sql": ai_query,

                "result": result,

                "columns": columns

            })

            ############################################################
            # RENDER HTML
            ############################################################

            return render_template(

                "index.html",

                chat_history=chat_history

            )

        except Exception as e:

            return f"Error : {e}"

    ####################################################################
    # FIRST PAGE LOAD
    ####################################################################

    return render_template(

        "index.html",

        chat_history=chat_history

    )

########################################################################
# RUN APP
########################################################################

if __name__ == "__main__":

    app.run(debug=True)