let currentQuiz = null; // Stores quiz data with student answers

async function generateQuiz() {
    const fileInput = document.getElementById('imageUpload');
    const resultDiv = document.getElementById('result');
    
    if (!fileInput.files[0]) {
        showError("Please select an image first!");
        return;
    }

    showLoading("⏳ Processing your quiz...");

    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        const response = await fetch('http://localhost:5000/generate-quiz', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server responded with status ${response.status}`);
        }

        currentQuiz = await response.json();
        displayQuiz(currentQuiz);
    } catch (error) {
        showError(`Failed to generate quiz: ${error.message}`);
        console.error("Quiz generation error:", error);
    }
}

function displayQuiz(quiz) {
    const resultDiv = document.getElementById('result');
    
    let html = `
        <h2>${quiz.topic}</h2>
        <div class="quiz-container">
    `;
    
    quiz.questions.forEach((q, i) => {
        q.student_answer = null; // Initialize answer slot
        
        html += `
        <div class="question-card" id="q${i}">
            <h3>Q${i+1}: ${q.question}</h3>
            <div class="options-grid">`;
        
        q.options.forEach((opt, optIndex) => {
            const optionLetter = String.fromCharCode(97 + optIndex);
            html += `
            <div class="option">
                <input type="radio" 
                       name="q${i}" 
                       id="q${i}_opt${optIndex}"
                       value="${optionLetter}"
                       onchange="storeAnswer(${i}, '${optionLetter}')">
                <label for="q${i}_opt${optIndex}">${opt}</label>
            </div>`;
        });
        
        html += `</div></div>`;
    });

    html += `
        </div>
        <button class="submit-btn" onclick="submitQuiz()">Submit Answers</button>
    `;
    
    resultDiv.innerHTML = html;
}

function storeAnswer(questionIndex, selectedOption) {
    if (!currentQuiz || !currentQuiz.questions[questionIndex]) return;
    
    currentQuiz.questions[questionIndex].student_answer = selectedOption;
    
    // Visual feedback
    const questionCard = document.getElementById(`q${questionIndex}`);
    if (questionCard) {
        questionCard.classList.add('answered');
    }
}

async function submitQuiz() {
    // Validate all answers
    const unansweredQuestions = currentQuiz.questions.filter(q => q.student_answer === null);
    if (unansweredQuestions.length > 0) {
        showError(`Please answer all questions! (${unansweredQuestions.length} remaining)`);
        
        // Highlight unanswered questions
        unansweredQuestions.forEach((_, i) => {
            const questionCard = document.getElementById(`q${i}`);
            if (questionCard) questionCard.classList.add('unanswered');
        });
        
        return;
    }

    showLoading("⏳ Evaluating your answers...");

    try {
        const response = await fetch('http://localhost:5000/evaluate-quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentQuiz)
        });

        if (!response.ok) {
            throw new Error(`Evaluation failed with status ${response.status}`);
        }

        const results = await response.json();
        displayEvaluationResults(results);
        
    } catch (error) {
        showError(`Evaluation failed: ${error.message}`);
        console.error("Evaluation error:", error);
    }
}

function displayEvaluationResults(results) {
    const resultDiv = document.getElementById('result');
    
    let html = `
        <h2>${currentQuiz.topic}</h2>
        <div class="results-container">
    `;
    
    results.evaluations.forEach((eval, i) => {
        const question = currentQuiz.questions[i];
        const isCorrect = eval.passed;
        
        html += `
        <div class="result-card ${isCorrect ? 'correct' : 'incorrect'}">
            <div class="question-header">
                <h3>Q${i+1}: ${question.question}</h3>
                <span class="score-badge">${eval.score}/5</span>
            </div>
            
            <div class="answer-comparison">
                <div class="student-answer">
                    <label>Your answer:</label>
                    <p>${question.student_answer.toUpperCase()}. ${question.options.find(opt => 
                        opt.startsWith(question.student_answer + ".")) || ''}</p>
                </div>
                
                <div class="correct-answer">
                    <label>Correct answer:</label>
                    <p>${question.right_option.toUpperCase()}. ${question.options.find(opt => 
                        opt.startsWith(question.right_option + ".")) || ''}</p>
                </div>
            </div>
            
            <div class="feedback">
                <p>${eval.feedback}</p>
            </div>
        </div>`;
    });

    // Add summary
    const percentage = Math.round((results.overall_score / 5) * 100);
    html += `
        <div class="summary-card">
            <h3>Quiz Summary</h3>
            <div class="score-meter">
                <div class="meter-fill" style="width: ${percentage}%"></div>
                <span>${percentage}%</span>
            </div>
            <p>${getResultMessage(percentage)}</p>
            <button onclick="window.location.reload()">Try Another Quiz</button>
        </div>
        </div>`;
    
    resultDiv.innerHTML = html;
}

// Helper functions
function showLoading(message) {
    document.getElementById('result').innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>`;
}

function showError(message) {
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = `
        <div class="error-state">
            <p>❌ ${message}</p>
        </div>`;
}

function getResultMessage(percentage) {
    if (percentage >= 80) return "🎉 Excellent work! You've mastered this material.";
    if (percentage >= 60) return "👍 Good job! You understand most concepts.";
    if (percentage >= 40) return "🤔 You're getting there! Review these topics.";
    return "📚 Keep practicing! Review the material and try again.";
}