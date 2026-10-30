document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // HTML ELEMENTS
    // =========================

    const roleSelect =
        document.getElementById("role");

    const startBtn =
        document.getElementById("startBtn");

    const setupSection =
        document.getElementById("setupSection");

    const interviewSection =
        document.getElementById("interviewSection");

    const questionText =
        document.getElementById("questionText");

    const answerInput =
        document.getElementById("answerInput");

    const nextBtn =
        document.getElementById("nextBtn");

    const progressText =
        document.getElementById("progressText");

    const progressBar =
        document.getElementById("progressBar");


    // =========================
    // AI EVALUATION ELEMENTS
    // =========================

    const evaluationBox =
        document.getElementById("evaluationBox");

    const technicalScore =
        document.getElementById("technicalScore");

    const relevanceScore =
        document.getElementById("relevanceScore");

    const clarityScore =
        document.getElementById("clarityScore");

    const completenessScore =
        document.getElementById("completenessScore");

    const overallScore =
        document.getElementById("overallScore");

    const feedbackText =
        document.getElementById("feedbackText");


    // =========================
    // INTERVIEW VARIABLES
    // =========================

    const totalQuestions = 5;

    let currentQuestion = 0;

    let selectedRole = "";

    let selectedQuestions = [];

    let interviewData = [];


    // =========================
    // START INTERVIEW
    // =========================

    startBtn.addEventListener(
        "click",
        async function () {

            selectedRole =
                roleSelect.value;

            if (!selectedRole) {

                alert(
                    "Please select a job role."
                );

                return;
            }


            // Reset interview
            currentQuestion = 0;

            selectedQuestions = [];

            interviewData = [];


            // Show interview section
            setupSection.style.display =
                "none";

            interviewSection.style.display =
                "block";


            // Reset UI
            answerInput.style.display =
                "block";

            nextBtn.style.display =
                "block";

            evaluationBox.style.display =
                "none";


            // Generate questions
            await generateQuestions();

        }
    );


    // =========================
    // GENERATE 5 AI QUESTIONS
    // =========================

    async function generateQuestions() {

        questionText.textContent =
            "🤖 AI is preparing your 5 interview questions...";

        progressText.textContent =
            "Preparing interview...";

        answerInput.disabled =
            true;

        nextBtn.disabled =
            true;

        nextBtn.textContent =
            "Generating Questions...";


        try {

            const response =
                await fetch(
                    "/generate-question",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            role: selectedRole
                        })
                    }
                );


            const data =
                await response.json();


            console.log(
                "Question API Response:",
                data
            );


            if (!data.success) {

                throw new Error(
                    data.error ||
                    "Question generation failed."
                );
            }


            // Check exactly 5 questions
            if (
                !data.questions ||
                data.questions.length !== 5
            ) {

                throw new Error(
                    "AI did not generate exactly 5 questions."
                );
            }


            // Save questions
            selectedQuestions =
                data.questions;


            console.log(
                "AI Generated Questions:",
                selectedQuestions
            );


            // Create answer data
            interviewData =
                selectedQuestions.map(
                    function (question) {

                        return {
                            question: question,
                            answer: ""
                        };

                    }
                );


            // Show first question
            showCurrentQuestion();


        } catch (error) {

            console.error(
                "Question Generation Error:",
                error
            );


            questionText.textContent =
                "Unable to generate AI questions.";

            progressText.textContent =
                "Please try again.";

            nextBtn.textContent =
                "Try Again";

            nextBtn.disabled =
                false;

            answerInput.disabled =
                true;


            alert(
                "Unable to generate AI questions.\n\n" +
                error.message
            );
        }

    }


    // =========================
    // SHOW CURRENT QUESTION
    // =========================

    function showCurrentQuestion() {

        const question =
            selectedQuestions[
                currentQuestion
            ];


        questionText.textContent =
            question;


        progressText.textContent =
            `Question ${currentQuestion + 1} of ${totalQuestions}`;


        const progress =
            (
                (currentQuestion + 1) /
                totalQuestions
            ) * 100;


        progressBar.style.width =
            progress + "%";


        answerInput.value =
            "";


        answerInput.disabled =
            false;

        nextBtn.disabled =
            false;


        if (
            currentQuestion ===
            totalQuestions - 1
        ) {

            nextBtn.textContent =
                "Submit Interview";

        } else {

            nextBtn.textContent =
                "Next Question";
        }


        evaluationBox.style.display =
            "none";


        answerInput.focus();

    }


    // =========================
    // NEXT / SUBMIT BUTTON
    // =========================

    nextBtn.addEventListener(
        "click",
        async function () {

            const answer =
                answerInput.value.trim();


            // Check answer
            if (!answer) {

                alert(
                    "Please enter your answer."
                );

                return;
            }


            // Save answer
            interviewData[
                currentQuestion
            ].answer = answer;


            console.log(
                `Answer ${currentQuestion + 1}:`,
                answer
            );


            // =========================
            // CHECK LAST QUESTION
            // =========================

            if (
                currentQuestion ===
                totalQuestions - 1
            ) {

                await evaluateInterview();

                return;
            }


            // Move to next question
            currentQuestion++;


            showCurrentQuestion();

        }
    );


    // =========================
    // EVALUATE COMPLETE INTERVIEW
    // =========================

    async function evaluateInterview() {

        // Disable controls
        nextBtn.disabled =
            true;

        answerInput.disabled =
            true;

        nextBtn.textContent =
            "🤖 AI Evaluating...";


        questionText.textContent =
            "🤖 AI is evaluating your complete interview...";


        progressText.textContent =
            "Analyzing all 5 answers...";


        progressBar.style.width =
            "100%";


        console.log(
            "Sending complete interview..."
        );

        console.log(
            "Role:",
            selectedRole
        );

        console.log(
            "Answers:",
            interviewData
        );


        try {

            const response =
                await fetch(
                    "/evaluate-interview",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            role:
                                selectedRole,

                            // IMPORTANT:
                            // app.py expects "answers"
                            answers:
                                interviewData

                        })
                    }
                );


            console.log(
                "Evaluation HTTP Status:",
                response.status
            );


            const data =
                await response.json();


            console.log(
                "Final Evaluation Response:",
                data
            );


            if (!data.success) {

                throw new Error(
                    data.error ||
                    "Interview evaluation failed."
                );
            }


            // Show final result
            showFinalEvaluation(
                data.evaluation
            );


            questionText.textContent =
                "🎉 Interview Evaluation Complete!";


            progressText.textContent =
                "Your complete interview has been evaluated.";


            answerInput.style.display =
                "none";

            nextBtn.style.display =
                "none";


        } catch (error) {

            console.error(
                "Interview Evaluation Error:",
                error
            );


            alert(
                "AI evaluation failed.\n\n" +
                error.message
            );


            nextBtn.disabled =
                false;

            answerInput.disabled =
                false;

            nextBtn.textContent =
                "Submit Interview";

        }

    }


    // =========================
    // SHOW FINAL EVALUATION
    // =========================

    function showFinalEvaluation(
        evaluation
    ) {

        console.log(
            "Final Evaluation:",
            evaluation
        );


        // Make sure results exist
        if (
            !evaluation ||
            !evaluation.results
        ) {

            console.error(
                "Invalid evaluation format:",
                evaluation
            );

            return;
        }


        // =========================
        // CALCULATE AVERAGES
        // =========================

        let technicalTotal = 0;

        let relevanceTotal = 0;

        let clarityTotal = 0;

        let completenessTotal = 0;

        let overallTotal = 0;


        evaluation.results.forEach(
            function (result) {

                technicalTotal +=
                    Number(
                        result.technical
                    ) || 0;

                relevanceTotal +=
                    Number(
                        result.relevance
                    ) || 0;

                clarityTotal +=
                    Number(
                        result.clarity
                    ) || 0;

                completenessTotal +=
                    Number(
                        result.completeness
                    ) || 0;

                overallTotal +=
                    Number(
                        result.overall
                    ) || 0;

            }
        );


        const count =
            evaluation.results.length;


        // =========================
        // DISPLAY SCORES
        // =========================

        technicalScore.textContent =
            (technicalTotal / count).toFixed(1);

        relevanceScore.textContent =
            (relevanceTotal / count).toFixed(1);

        clarityScore.textContent =
            (clarityTotal / count).toFixed(1);

        completenessScore.textContent =
            (completenessTotal / count).toFixed(1);

        overallScore.textContent =
            evaluation.final_score ??
            (overallTotal / count).toFixed(1);


        // =========================
        // FEEDBACK
        // =========================

        let feedback = "";


        evaluation.results.forEach(
            function (result) {

                feedback +=
                    "Question " +
                    result.question_number +
                    ": " +
                    result.feedback +
                    "\n\n";

            }
        );


        if (evaluation.strengths) {

            feedback +=
                "\nStrengths:\n";

            evaluation.strengths.forEach(
                function (strength) {

                    feedback +=
                        "• " +
                        strength +
                        "\n";

                }
            );
        }


        if (evaluation.weaknesses) {

            feedback +=
                "\nWeaknesses:\n";

            evaluation.weaknesses.forEach(
                function (weakness) {

                    feedback +=
                        "• " +
                        weakness +
                        "\n";

                }
            );
        }


        if (
            evaluation.improvement_suggestions
        ) {

            feedback +=
                "\nImprovement Suggestions:\n";

            evaluation.improvement_suggestions.forEach(
                function (suggestion) {

                    feedback +=
                        "• " +
                        suggestion +
                        "\n";

                }
            );
        }


        feedbackText.textContent =
            feedback;


        // Show evaluation box
        evaluationBox.style.display =
            "block";


        console.log(
            "Final Score:",
            evaluation.final_score
        );

        console.log(
            "Percentage:",
            evaluation.percentage
        );

    }

});